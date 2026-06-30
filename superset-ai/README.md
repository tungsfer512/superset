# Superset AI Sidecar (`superset-ai`)

Dịch vụ AI **độc lập** cho Apache Superset: hỏi-đáp ngôn ngữ tự nhiên, Text-to-SQL,
đọc/giải thích SQL và nhận diện kiến trúc DB.

- **Tách biệt runtime:** chạy như tiến trình/container riêng (FastAPI + uvicorn).
  Lỗi của sidecar **không** làm hỏng Superset.
- **Đọc dữ liệu qua REST API Superset** (không nối thẳng DB), dùng **token
  pass-through** để giữ RBAC + RLS theo từng user.
- **Môi trường bám sát Superset:** Python 3.11 (base image
  `python:3.11.13-slim-bookworm`), tooling `ruff` + `mypy` + `pytest`, lib dùng
  chung pin trùng version Superset.

> Đây là khung Phase 0. Chi tiết kiến trúc & lộ trình: xem
> [`../AI_QA_INTEGRATION_PLAN.md`](../AI_QA_INTEGRATION_PLAN.md).

## Phát triển

```bash
cd superset-ai
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements/development.txt

# Chất lượng mã (cùng tooling với Superset)
ruff check .
ruff format --check .
mypy superset_ai
pytest

# Chạy local
cp .env.example .env          # điền ANTHROPIC_API_KEY khi cần
uvicorn superset_ai.main:app --host 0.0.0.0 --port 8800 --reload
curl -s http://localhost:8800/health | jq
```

## Docker

```bash
docker build -t superset-ai .
docker run --rm -p 8800:8800 \
  -e SUPERSET_AI_SUPERSET_BASE_URL=http://host.docker.internal:8088 \
  superset-ai
```

## Cấu trúc

```
superset_ai/
├── main.py            # FastAPI app factory + entrypoint
├── config.py          # Settings (env SUPERSET_AI_*)
├── api/               # routers (health; sẽ thêm ask, sql ở phase sau)
├── auth/              # token pass-through (phase 1)
├── superset_client/   # HTTP client tới REST API Superset (phase 1)
├── llm/               # provider LLM (phase 2)
├── tools/             # tool-use cho LLM (phase 1-2)
├── smart/             # SQL reader/generator, schema indexer, RAG (phase 3)
└── prompts/           # system prompt + few-shot
```
