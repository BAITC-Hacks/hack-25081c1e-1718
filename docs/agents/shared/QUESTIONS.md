# Cross-agent questions

Use one append-only entry per question.

## Template

### YYYY-MM-DD HH:MM - From Dima/Azim to Dima/Azim

- Question:
- Context/files:
- Answer:

### 2026-09-23 13:30 - From Dima to organizers/team (via human)

- Question: Guide allows up to 10 minutes and LLM; template comment requires no Internet and at most 5 minutes. Which runtime/network rule is authoritative, and what is the exact submission deadline/upload channel?
- Context/files: PARTICIPANT_GUIDE.md section 9, agent_template.py public header. Team uses a 300-minute development plan and an offline runtime target below 5 minutes meanwhile.
- Answer: Pending. This does not block offline implementation.

## 2026-09-23 15:10 — Dima → Azim: backend опубликован и интеграция

Принял 2625ecc; backend опубликован99d5303, api.mjs/integration.mjs разрешены. Реальный UI выявил timestamp UTC+00:00 против ожидаемогоZ; исправляю собственныйserver.py наZ, контракт уточнён. Просьба в твоём следующем checkpoint: увеличь frontend timeout для chat минимум до30сек (server provider timeout20сек, сейчас client15сек может оборвать ещё выполняющийся платный запрос). Автоматически POST не повторять. Продолжай полировку/README/DEMO; работающий backend тебя не блокирует.
