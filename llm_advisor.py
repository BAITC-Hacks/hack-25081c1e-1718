"""Optional, fail-safe OpenAI advisor for campaign candidate prioritisation."""

import json
import math
import os
import urllib.error
import urllib.request


class Advisor:
    """Ask a model to rank already-built candidate IDs without changing policy."""

    def __init__(self):
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini-2025-04-14")
        self.events = []
        self._calls = 0

    @staticmethod
    def _finite(value):
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if math.isfinite(number) else None

    @staticmethod
    def _text(value, limit=120):
        if value is None:
            return None
        return str(value)[:limit]

    def _candidate_payload(self, candidate):
        cid = candidate.get("candidate_id", candidate.get("id"))
        if cid is None:
            return None
        allowed = {
            "candidate_id", "target_tariff", "channel", "filter_arpu_segment",
            "filter_data_segment", "filter_call_segment", "filter_current_tariff",
        }
        payload = {"candidate_id": self._text(cid, 80)}
        for key in allowed - {"candidate_id"}:
            value = candidate.get(key)
            if value is not None:
                payload[key] = self._text(value, 80)
        filters = candidate.get("filters")
        if isinstance(filters, dict):
            filter_names = {
                "arpu_segment": "filter_arpu_segment",
                "data_segment": "filter_data_segment",
                "call_segment": "filter_call_segment",
                "current_tariff": "filter_current_tariff",
            }
            for source, target in filter_names.items():
                value = filters.get(source, filters.get(target))
                if value is not None:
                    payload[target] = self._text(value, 80)
        for key in (
            "n_customers", "audience_size", "estimated_net", "arpu_sum",
            "observed_lift_ratio", "prior_lift_ratio", "prior_n",
            "posterior_mean", "uncertainty", "score",
        ):
            number = self._finite(candidate.get(key))
            if number is not None:
                payload[key] = number
        rationale = self._text(candidate.get("rationale"), 180)
        if rationale:
            payload["rationale"] = rationale
        return payload if payload["candidate_id"] else None

    def _observation_payload(self, observation):
        result = {}
        for key in ("candidate_id", "target_tariff", "channel", "status"):
            value = observation.get(key)
            if value is not None:
                result[key] = self._text(value, 80)
        for key in ("n_customers", "estimated_net", "observed_lift_ratio"):
            number = self._finite(observation.get(key))
            if number is not None:
                result[key] = number
        return result

    def _record(self, phase, status, reason=None, usage=None, status_code=None):
        event = {"phase": self._text(phase, 40), "status": self._text(status, 40)}
        if reason:
            event["reason"] = self._text(reason, 120)
        if status_code is not None:
            code = self._finite(status_code)
            if code is not None:
                event["status_code"] = int(code)
        if self.model:
            event["model"] = self._text(self.model, 80)
        if isinstance(usage, dict):
            clean_usage = {}
            for key in ("input_tokens", "output_tokens", "total_tokens"):
                number = self._finite(usage.get(key))
                if number is not None:
                    clean_usage[key] = int(number)
            if clean_usage:
                event["usage"] = clean_usage
        self.events.append(event)

    @staticmethod
    def _schema(allowed_ids):
        return {
            "type": "object",
            "properties": {
                "candidate_ids": {
                    "type": "array",
                    "items": {"type": "string", "enum": allowed_ids},
                },
                "summary": {"type": "string"},
            },
            "required": ["candidate_ids", "summary"],
            "additionalProperties": False,
        }

    @staticmethod
    def _extract_text(response):
        if not isinstance(response, dict) or response.get("status") != "completed":
            return None
        output = response.get("output")
        if not isinstance(output, list):
            return None
        texts = []
        for item in output:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "message":
                content_items = item.get("content")
                if not isinstance(content_items, list):
                    return None
                for content in content_items:
                    if not isinstance(content, dict):
                        continue
                    if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                        texts.append(content["text"])
                    if content.get("type") == "refusal":
                        return None
        return "".join(texts) or None

    def recommend(self, candidates, observations, resources, phase):
        """Return model-selected existing candidate IDs, or an empty safe result."""
        empty = {"candidate_ids": [], "summary": ""}
        if os.environ.get("ARPU_OFFLINE") == "1":
            self._record(phase, "skipped", "offline_mode")
            return empty
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            self._record(phase, "skipped", "missing_api_key")
            return empty
        if self._calls >= 2:
            self._record(phase, "skipped", "call_limit")
            return empty
        if not isinstance(candidates, list) or not isinstance(observations, list):
            self._record(phase, "failed", "invalid_inputs")
            return empty

        clean_candidates = []
        for candidate in candidates[:24]:
            if isinstance(candidate, dict):
                item = self._candidate_payload(candidate)
                if item:
                    clean_candidates.append(item)
        allowed_ids = list(dict.fromkeys(item["candidate_id"] for item in clean_candidates))
        if not allowed_ids:
            self._record(phase, "failed", "no_candidates")
            return empty
        clean_observations = [
            self._observation_payload(item) for item in observations[:20]
            if isinstance(item, dict)
        ]
        safe_resources = {}
        if isinstance(resources, dict):
            for key in ("remaining_budget", "remaining_contacts", "pilots_left"):
                number = self._finite(resources.get(key))
                if number is not None:
                    safe_resources[key] = number
        request_data = {
            "phase": self._text(phase, 40),
            "candidates": clean_candidates,
            "observations": clean_observations,
            "resources": safe_resources,
        }
        instructions = (
            "Приоритизируй только переданные candidate_id для следующей фазы кампании. "
            "Верни не более 10 ID и краткое деловое резюме на русском языке. "
            "Не выдумывай наблюдения и не меняй фильтры, каналы или лимиты. "
            "На initial выбирай полезные гипотезы для разведки. На feedback при "
            "неоднозначном положительном результате рекомендуй повторный пилот; "
            "большой historical n сам по себе не доказывает причинный эффект. "
            "Не раскрывай chain-of-thought."
        )
        body = {
            "model": self.model,
            "store": False,
            "input": [
                {"role": "system", "content": [{"type": "input_text", "text": instructions}]},
                {"role": "user", "content": [{"type": "input_text", "text": json.dumps(request_data)}]},
            ],
            "max_output_tokens": 900,
            "text": {"format": {
                "type": "json_schema", "name": "campaign_advice", "strict": True,
                "schema": self._schema(allowed_ids),
            }},
        }
        request = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(body).encode("utf-8"),
            headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"},
            method="POST",
        )
        self._calls += 1
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                raw = response.read(128 * 1024)
                if len(raw) == 128 * 1024 and response.read(1):
                    self._record(phase, "failed", "invalid_response")
                    return empty
                payload = json.loads(raw.decode("utf-8"))
            text = self._extract_text(payload)
            if not text:
                self._record(phase, "failed", "invalid_response")
                return empty
            result = json.loads(text)
            if not isinstance(result, dict):
                self._record(phase, "failed", "invalid_response")
                return empty
            selected = result.get("candidate_ids")
            summary = result.get("summary")
            if (not isinstance(selected, list) or not selected or
                    not isinstance(summary, str) or not summary.strip() or
                    any(item not in allowed_ids for item in selected)):
                self._record(phase, "failed", "invalid_model_output")
                return empty
            selected = list(dict.fromkeys(selected))[:10]
            usage = payload.get("usage") if isinstance(payload, dict) else None
            self._record(phase, "completed", usage=usage)
            return {"candidate_ids": selected, "summary": summary[:500]}
        except urllib.error.HTTPError as error:
            self._record(phase, "failed", "http_error", status_code=error.code)
            return empty
        except (TimeoutError,):
            self._record(phase, "failed", "timeout")
            return empty
        except (urllib.error.URLError, OSError):
            self._record(phase, "failed", "request_error")
            return empty
        except (ValueError, TypeError, json.JSONDecodeError):
            self._record(phase, "failed", "invalid_response")
            return empty
