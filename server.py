"""Local ARPU Compass API. Only fixed analysis commands and report questions."""

import argparse
from collections import deque
import copy
from datetime import datetime, timezone
import getpass
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import secrets
import subprocess
import sys
import threading
import time
from urllib.parse import unquote, urlsplit
import warnings

from report_assistant import MODEL, answer_question
from report_localization import SUPPORTED_LANGUAGES

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
MAX_BODY = 16 * 1024
MAX_REPORT = 2 * 1024 * 1024
STATIC_FILES = {"/": "index.html", "/index.html": "index.html", "/app.mjs": "app.mjs",
                "/report.mjs": "report.mjs", "/api.mjs": "api.mjs",
                "/integration.mjs": "integration.mjs", "/styles.css": "styles.css", "/i18n.mjs": "i18n.mjs"}


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def reject_constant(value):
    raise ValueError("Non-finite JSON value")


def read_report(path):
    with path.open("rb") as stream:
        raw = stream.read(MAX_REPORT + 1)
    if len(raw) > MAX_REPORT:
        raise ValueError("Report too large")
    value = json.loads(raw.decode("utf-8"), parse_constant=reject_constant)
    if (not isinstance(value, dict) or value.get("schema_version") != "1.0"
            or not isinstance(value.get("validation"), dict) or value["validation"].get("valid") is not True
            or not isinstance(value.get("campaigns"), list) or not 1 <= len(value["campaigns"]) <= 10
            or not isinstance(value.get("pilots"), list) or not 1 <= len(value["pilots"]) <= 20
            or not isinstance(value.get("evaluation"), dict)):
        raise ValueError("Invalid report")
    return value, hashlib.sha256(raw).hexdigest()


class ApiError(Exception):
    def __init__(self, status, code, message):
        self.status, self.code, self.message = status, code, message


class AppState:
    def __init__(self, port):
        self.port = port
        self.token = secrets.token_urlsafe(32)
        self.lock = threading.RLock()
        self.chat_lock = threading.Lock()
        self.jobs = {}
        self.reports = {}
        self.current_job = None
        self.latest_report = None
        self.chat_times = deque()
        self.run_times = deque()
        self.child = None
        self.worker = None
        self.closing = False

    @staticmethod
    def openai_status():
        configured = bool(os.environ.get("OPENAI_API_KEY", "").strip())
        return {"configured": configured, "enabled": configured and os.environ.get("ARPU_OFFLINE") != "1",
                "model": os.environ.get("OPENAI_MODEL", MODEL)}

    def publish(self, report):
        with self.lock:
            report_id = secrets.token_hex(16)
            self.reports[report_id] = copy.deepcopy(report)
            self.latest_report = report_id
            while len(self.reports) > 10:
                del self.reports[next(iter(self.reports))]
            return report_id

    @staticmethod
    def throttle(timestamps, limit):
        now = time.monotonic()
        while timestamps and now - timestamps[0] >= 60:
            timestamps.popleft()
        if len(timestamps) >= limit:
            raise ApiError(429, "rate_limited", "Слишком частые запросы. Повторите через минуту.")
        timestamps.append(now)

    def start_run(self, mode, seed):
        if mode == "openai" and not self.openai_status()["enabled"]:
            raise ApiError(503, "openai_unavailable", "OpenAI не настроен на сервере. Доступен автономный режим.")
        with self.lock:
            if self.closing:
                raise ApiError(503, "server_stopping", "Сервер завершает работу.")
            if self.current_job and self.jobs[self.current_job]["state"] == "running":
                raise ApiError(409, "run_busy", "Анализ уже выполняется.")
            self.throttle(self.run_times, 6)
            run_id = secrets.token_hex(16)
            self.jobs[run_id] = {"run_id": run_id, "state": "running", "stage": "evaluating", "mode": mode,
                                 "seed": seed, "started_at": utc_now(), "finished_at": None,
                                 "report_id": None, "error": None}
            self.current_job = run_id
            while len(self.jobs) > 20:
                del self.jobs[next(iter(self.jobs))]
            self.worker = threading.Thread(target=self.run, args=(run_id,), daemon=True)
            self.worker.start()
            return {"run_id": run_id, "state": "running"}

    def run(self, run_id):
        with self.lock:
            job = dict(self.jobs[run_id])
        try:
            destination = ROOT / "output" / "runs" / (run_id + ".json")
            if destination.exists():
                raise ValueError("Output identity already exists")
            # The child gets only runtime variables and the selected API settings.
            environment = {key: os.environ[key] for key in (
                "SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "HOME", "USERPROFILE",
                "LANG", "LC_ALL", "SSL_CERT_FILE", "SSL_CERT_DIR") if key in os.environ}
            environment["PYTHONUTF8"] = "1"
            if job["mode"] == "offline":
                environment["ARPU_OFFLINE"] = "1"
            else:
                environment["OPENAI_API_KEY"] = os.environ["OPENAI_API_KEY"]
                environment["OPENAI_MODEL"] = os.environ.get("OPENAI_MODEL", MODEL)
            command = [sys.executable, "-X", "utf8", str(ROOT / "scripts" / "run_agent.py"),
                       "--mode", "report", "--seed", str(job["seed"]), "--run-id", run_id]
            if job["mode"] == "offline":
                command.append("--offline")
            started = datetime.now(timezone.utc)
            with self.lock:
                if self.closing:
                    raise ValueError("Server stopping")
                child = subprocess.Popen(command, cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.child = child
            try:
                returncode = child.wait(timeout=300)
            except subprocess.TimeoutExpired:
                self.stop_child(child)
                raise
            finally:
                with self.lock:
                    if self.child is child:
                        self.child = None
            if returncode:
                raise ValueError("Analysis failed")
            report, _ = read_report(destination)
            generated = datetime.fromisoformat(report.get("generated_at", ""))
            if (report.get("provenance", {}).get("run_id") != run_id or report.get("seed") != job["seed"]
                    or generated.tzinfo is None or generated < started):
                raise ValueError("Stale report")
            with self.lock:
                if self.closing:
                    raise ValueError("Server stopping")
                report_id = self.publish(report)
                self.jobs[run_id].update(state="completed", stage="ready", report_id=report_id,
                                          finished_at=utc_now())
        except Exception as error:
            timed_out = isinstance(error, subprocess.TimeoutExpired)
            with self.lock:
                self.jobs[run_id].update(state="failed", stage="failed", finished_at=utc_now(), error={
                    "code": "run_timeout" if timed_out else "run_failed",
                    "message": "Превышено время анализа." if timed_out else "Анализ не завершён. Предыдущий отчёт сохранён."})

    @staticmethod
    def stop_child(child):
        if child is not None and child.poll() is None:
            try:
                child.terminate()
                try:
                    child.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=3)
            except (OSError, subprocess.TimeoutExpired):
                # Teardown must still close the listener if the OS cannot reap a child.
                pass

    def close(self):
        with self.lock:
            self.closing = True
            child, worker = self.child, self.worker
        self.stop_child(child)
        if worker is not None:
            worker.join(timeout=7)

    def answer(self, report_id, message, language="ru"):
        with self.lock:
            if report_id not in self.reports:
                raise ApiError(404, "report_not_found", "Отчёт не найден. Загрузите отчёт сервера или запустите анализ.")
            report = copy.deepcopy(self.reports[report_id])
        if not self.chat_lock.acquire(blocking=False):
            raise ApiError(409, "chat_busy", "Предыдущий ответ ещё готовится.")
        try:
            with self.lock:
                self.throttle(self.chat_times, 12)
            response = answer_question(report, message, offline=not self.openai_status()["enabled"], language=language)
            return {"report_id": report_id, **response}
        finally:
            self.chat_lock.release()


class LocalServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, *args, **kwargs):
        self.request_slots = threading.BoundedSemaphore(16)
        super().__init__(*args, **kwargs)

    def process_request(self, request, client_address):
        if not self.request_slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self.request_slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.request_slots.release()


class Handler(BaseHTTPRequestHandler):
    server_version = "ARPUCompass"
    sys_version = ""

    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    @property
    def app(self):
        return self.server.app

    def log_message(self, format, *args):
        # URLs, request text, tokens and upstream messages never enter logs.
        pass

    def headers_for(self, status, content_type, length):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers()

    def send_json(self, status, value):
        raw = json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self.headers_for(status, "application/json; charset=utf-8", len(raw))
        self.wfile.write(raw)

    def validate_host(self):
        values = self.headers.get_all("Host", [])
        if len(values) != 1 or values[0] not in {f"127.0.0.1:{self.app.port}", f"localhost:{self.app.port}"}:
            raise ApiError(403, "invalid_host", "Недопустимый адрес сервера.")
        return values[0]

    def body(self):
        host = self.validate_host()
        origins = self.headers.get_all("Origin", [])
        tokens = self.headers.get_all("X-ARPU-Token", [])
        if (origins != ["http://" + host] or len(tokens) != 1
                or not secrets.compare_digest(tokens[0].encode("utf-8"), self.app.token.encode("ascii"))):
            raise ApiError(403, "invalid_origin_or_token", "Обновите страницу сервера перед повторной попыткой.")
        lengths = self.headers.get_all("Content-Length", [])
        if self.headers.get("Transfer-Encoding") or len(lengths) != 1 or not lengths[0].isdigit():
            raise ApiError(400, "invalid_body", "Неверный формат запроса.")
        size = int(lengths[0])
        if not 0 < size <= MAX_BODY:
            raise ApiError(400, "invalid_body_size", "Запрос пуст или превышает 16 КБ.")
        if self.headers.get_content_type() != "application/json":
            raise ApiError(400, "invalid_content_type", "Ожидается JSON.")
        try:
            raw = self.rfile.read(size)
            if len(raw) != size:
                raise ValueError("Incomplete body")
            value = json.loads(raw.decode("utf-8"), parse_constant=reject_constant)
            if not isinstance(value, dict):
                raise ValueError("Object required")
            return value
        except (ValueError, UnicodeError):
            raise ApiError(400, "invalid_json", "Не удалось прочитать JSON запроса.")

    def do_GET(self):
        self.dispatch(False)

    def do_POST(self):
        self.dispatch(True)

    def dispatch(self, post):
        try:
            self.validate_host()
            parsed = urlsplit(self.path)
            if parsed.scheme or parsed.netloc or parsed.query:
                raise ApiError(400, "invalid_url", "Недопустимый URL.")
            path = unquote(parsed.path)
            if post:
                value = self.body()
                if path == "/api/runs":
                    if (set(value) != {"mode", "seed"} or value["mode"] not in ("offline", "openai")
                            or type(value["seed"]) is not int or not 0 <= value["seed"] < 2 ** 32):
                        raise ApiError(400, "invalid_run", "Укажите режим offline/openai и корректный целый seed.")
                    return self.send_json(202, self.app.start_run(value["mode"], value["seed"]))
                if path == "/api/chat":
                    if (set(value) not in ({"report_id", "message"}, {"report_id", "message", "language"})
                            or not isinstance(value["report_id"], str)
                            or not isinstance(value["message"], str) or not 1 <= len(value["message"].strip()) <= 2000):
                        raise ApiError(400, "invalid_message", "Укажите отчёт и вопрос длиной до 2000 символов.")
                    language = value.get("language", "ru")
                    if language not in SUPPORTED_LANGUAGES:
                        raise ApiError(400, "invalid_language", "Поддерживаются языки ru и kk.")
                    return self.send_json(200, self.app.answer(value["report_id"], value["message"].strip(), language))
                raise ApiError(404, "not_found", "Действие не найдено.")
            if path == "/api/health":
                with self.app.lock:
                    job = self.app.jobs.get(self.app.current_job, {})
                    value = {"api_version": "1.0", "status": "ok", "csrf_token": self.app.token,
                             "openai": self.app.openai_status(),
                             "run": {"run_id": self.app.current_job, "state": job.get("state", "idle")},
                             "capabilities": {"run": True, "chat": True, "chat_languages": list(SUPPORTED_LANGUAGES)}}
                return self.send_json(200, value)
            if path == "/api/report":
                with self.app.lock:
                    report_id = self.app.latest_report
                    if not report_id:
                        raise ApiError(404, "no_report", "Готового отчёта пока нет. Запустите анализ.")
                    value = {"report_id": report_id, "report": copy.deepcopy(self.app.reports[report_id])}
                return self.send_json(200, value)
            if path.startswith("/api/runs/"):
                with self.app.lock:
                    job = self.app.jobs.get(path.removeprefix("/api/runs/"))
                    if not job:
                        raise ApiError(404, "run_not_found", "Запуск не найден.")
                    value = copy.deepcopy(job)
                return self.send_json(200, value)
            if path.startswith("/api/"):
                raise ApiError(404, "not_found", "Ресурс не найден.")
            name = STATIC_FILES.get(path)
            file = WEB / name if name else None
            if (file is None or not file.is_file() or not file.resolve().is_relative_to(WEB.resolve())
                    or file.stat().st_size > 2 * 1024 * 1024):
                raise ApiError(404, "not_found", "Файл не найден.")
            raw = file.read_bytes()
            content_type = "text/javascript" if file.suffix in {".mjs", ".js"} else mimetypes.guess_type(file.name)[0] or "application/octet-stream"
            self.headers_for(200, content_type, len(raw))
            self.wfile.write(raw)
        except ApiError as error:
            self.send_json(error.status, {"error": {"code": error.code, "message": error.message}})
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            self.close_connection = True
        except Exception:
            self.send_json(500, {"error": {"code": "internal_error", "message": "Не удалось выполнить запрос."}})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--ask-key", action="store_true")
    mode.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("port must be between 1024 and 65535")
    if args.ask_key:
        if not sys.stdin.isatty():
            parser.error("--ask-key requires an interactive terminal")
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            try:
                key = getpass.getpass("OpenAI API key (hidden, process only): ").strip()
            except getpass.GetPassWarning:
                parser.error("This terminal cannot hide the key")
        if not key:
            parser.error("Empty key")
        os.environ["OPENAI_API_KEY"] = key
        os.environ.pop("ARPU_OFFLINE", None)
        key = None
    elif args.offline:
        os.environ["ARPU_OFFLINE"] = "1"
    httpd = LocalServer(("127.0.0.1", args.port), Handler)
    httpd.app = AppState(args.port)
    print(f"ARPU Compass: http://127.0.0.1:{args.port}", flush=True)
    print("OpenAI configured:", httpd.app.openai_status()["configured"], flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            httpd.app.close()
        finally:
            httpd.server_close()


if __name__ == "__main__":
    main()
