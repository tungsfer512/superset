# Triển khai & vận hành `superset-ai`

Sidecar AI chạy **tiến trình riêng** cạnh Superset. Lỗi của nó **không** làm
hỏng Superset; Superset cũng không nạp thêm thư viện AI nào.

## 1. Biến môi trường (prefix `SUPERSET_AI_`)

| Biến | Mặc định | Ý nghĩa |
|------|----------|---------|
| `SUPERSET_BASE_URL` | `http://localhost:8088` | REST API Superset |
| `LLM_PROVIDER` | `anthropic` | `anthropic` \| `openai` \| `gemini` |
| `LLM_MODEL` | (theo provider) | Override model |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GEMINI_API_KEY` | — | Chỉ cần key của provider đang dùng |
| `SQL_ROW_LIMIT` | `1000` | Trần số dòng mỗi truy vấn |
| `RESPONSE_TOKEN_GUARD` | `25000` | Cắt kết quả tool đưa vào LLM |
| `RATE_LIMIT_PER_MIN` | `30` | Giới hạn req/phút mỗi user (0 = tắt) |
| `MAX_TOOL_ITERATIONS` | `6` | Trần vòng tool-use |
| `ENABLE_GROUNDING` | `true` | Bật schema indexer + glossary + RAG |
| `GROUNDING_TOP_K` | `5` | Số dataset đưa vào context |
| `SCHEMA_CACHE_TTL` | `300` | TTL cache schema (giây) |
| `GLOSSARY_PATH` | — | Đường dẫn JSON glossary vi↔db |
| `EXTRA_CORS_ORIGINS` | — | Origin trình duyệt thêm (phẩy ngăn cách) |
| `CONVERSATION_DB_PATH` | `data/conversations.db` | File SQLite lưu lịch sử chat (để trống = lưu tạm trong RAM) |
| `REDIS_URL` | — | Bật rate limit dùng Redis (đa worker) |

## 2. Chạy

Service `superset-ai` đã được gộp vào **`docker-compose.yml` của Superset** (cùng
network, trỏ `http://superset:8088`). Provider + API key đặt trong
`superset-ai/.env` (gitignored).

```bash
# Từ thư mục gốc repo — chạy cùng toàn bộ stack Superset:
docker compose up -d --build superset-ai
curl -s http://localhost:8800/health | jq
```

> `SUPERSET_AI_SUPERSET_BASE_URL` được compose override thành `http://superset:8088`
> nên không cần sửa trong `.env`.

## 3. Reverse proxy (khuyến nghị) — giữ RBAC/RLS

Đặt Superset và sidecar **chung domain**, route `/superset-ai/*` sang sidecar.
Khi đó cookie phiên Superset tự gửi kèm → sidecar gọi API **nhân danh user** →
RBAC + RLS được áp đúng. Frontend mặc định gọi `'/superset-ai'`.

Ví dụ Nginx:

```nginx
location /superset-ai/ {
    proxy_pass http://superset-ai:8800/;
    proxy_set_header Host $host;
    proxy_set_header Cookie $http_cookie;        # forward session
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_buffering off;                          # cho SSE /ask/stream
}
location / {
    proxy_pass http://superset:8088;
}
```

> TLS: kết thúc ở reverse proxy. Bật HTTPS cho mọi endpoint production.

## 4. Bảo mật

- **Chỉ đọc**: chỉ chạy SELECT, chặn DDL/DML (AST + denylist), ép `LIMIT`.
- **Token pass-through**: không lưu credential Superset; chạy theo quyền user.
- **Sanitize lỗi**: che connection string / key / IP trước khi trả về.
- **Rate limit** theo user; **response guard** chống payload khổng lồ.
- **Khóa LLM** đặt qua env/secret, **không** commit. Đừng để key thật trong
  `.env.example` (file template). Dùng `.env` (đã gitignore) cho key thật.

## 5. Vận hành

- `GET /health` cho liveness/readiness (đã có healthcheck trong compose).
- Access log: mỗi request ghi `method path -> status (ms)`, **không** kèm secret.
- Scale: nhiều worker → đặt `REDIS_URL` cho rate limit; lịch sử chat có thể
  chuyển sang `RedisConversationStore` (cùng interface) hoặc dùng volume SQLite.

### Lịch sử hội thoại (lưu bền, xem lại, chat tiếp)

- Mặc định lưu vào SQLite tại `CONVERSATION_DB_PATH`. Compose mount volume
  `superset_ai_data:/app/data` nên **lịch sử sống sót qua restart/rebuild**.
- Mỗi hội thoại được **gán theo người dùng** (theo cookie/Authorization) — user
  chỉ thấy lịch sử của chính mình.
- Endpoint: `GET /conversations` (danh sách), `GET /conversations/{id}` (nội
  dung để xem lại), và `POST /ask` với `conversation_id` để **chat tiếp** —
  các lượt trước được phát lại làm ngữ cảnh (context đa lượt).

## 6. Frontend

Panel "Ask AI" ở `superset-frontend/src/features/aiAssistant`. Xem README ở đó
để gắn `<AskAIButton />` vào navbar và cấu hình `window.supersetAiBaseUrl`.
