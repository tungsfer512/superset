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

## 2. Chạy

```bash
docker compose up -d --build
curl -s http://localhost:8800/health | jq
```

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
- Scale: nhiều worker → thay `InMemoryConversationStore` và `RateLimiter`
  bằng bản nền Redis (interface đã tách sẵn).

## 6. Frontend

Panel "Ask AI" ở `superset-frontend/src/features/aiAssistant`. Xem README ở đó
để gắn `<AskAIButton />` vào navbar và cấu hình `window.supersetAiBaseUrl`.
