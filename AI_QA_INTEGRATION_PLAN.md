# Kế hoạch tích hợp AI & Hỏi-Đáp — Sidecar tách riêng (`superset-ai/`)

> Plan kỹ thuật: xây `superset-ai` thành **service AI tách riêng** (sidecar) — **tiến trình/container riêng**, **đọc dữ liệu qua REST API của Superset**. Mục tiêu cốt lõi: **không làm Superset chậm hơn, không nặng hơn, và AI lỗi không kéo Superset lỗi theo.**
>
> Tham khảo:
> - Superset MCP Server: https://superset.apache.org/admin-docs/configuration/mcp-server
> - mcp-superset (community): https://github.com/bintocher/mcp-superset

---

## 1. Quyết định kiến trúc (đã chốt — Sidecar / REST API)

| Quyết định | Lựa chọn |
|---|---|
| Mô hình chạy | **Tiến trình/container RIÊNG** (FastAPI + uvicorn), tách hoàn toàn khỏi Superset |
| Truy cập Superset | **Qua REST API** (`/api/v1/...`) — KHÔNG import Superset, KHÔNG nối thẳng DB |
| Stack | **Python + FastAPI**, Python 3.11 (cùng base image Superset) |
| Xác thực & RLS | **Token/session pass-through** — gọi API nhân danh user đăng nhập → Superset tự áp RBAC + RLS |
| Vị trí code | Folder `superset-ai/` trong repo (ngang hàng `superset-frontend/`) — tiện quản lý, vẫn tách runtime |
| Thay đổi trong core | **0 dòng**; chỉ thêm frontend panel "Ask AI" |

**3 đảm bảo ứng với yêu cầu của bạn:**

1. **Không làm Superset NẶNG hơn** — process Superset không nạp thêm bất kỳ lib AI nào (`anthropic`, `sqlglot`, vector store…). Chúng chỉ ở process sidecar. RAM/thời gian khởi động Superset không đổi. Sidecar cũng **không cài Superset** (chỉ cần `httpx` + lib AI) nên nhẹ.
2. **Không làm Superset CHẬM hơn** — mọi việc nặng (LLM, embedding, parse SQL) chạy ở sidecar. Superset chỉ nhận **REST call có giới hạn** (rate-limit, timeout, chỉ SELECT) — như một user thao tác bình thường. Latency request hiện tại của Superset không bị ảnh hưởng.
3. **AI lỗi KHÔNG kéo Superset lỗi** — sidecar là tiến trình riêng; crash/treo chỉ chết sidecar. Frontend panel báo "AI offline", toàn bộ Superset chạy bình thường.

> Đánh đổi chấp nhận: có overhead HTTP mỗi tool call và bị giới hạn theo những gì REST API expose — đổi lại là cô lập + nhẹ + an toàn quyền. Đây đúng là ưu tiên bạn đặt ra.

---

## 2. Môi trường — bám sát Superset nhưng deps RIÊNG

| Hạng mục | Superset | `superset-ai/` |
|---|---|---|
| Python | Docker `3.11.13-slim-bookworm` | **cùng** base image 3.11 |
| Lint/format | `ruff` + `ruff-format` (target py310, style Black) | cùng config (đã set trong `pyproject.toml`) |
| Type check | `mypy` | cùng style strict |
| Quản lý deps | `requirements/*.in → *.txt` | cùng pattern |
| Lib dùng chung | `redis==4.6.0`, `requests==2.32.4`, `pyjwt==2.10.1`… | **pin trùng** version |
| Lib riêng | — | `fastapi`, `uvicorn`, `httpx`, `anthropic`, `sqlglot` (KHÔNG cài Superset) |
| License header | ASF | áp dụng |

> "Giống Superset" = cùng Python/tooling/base-image + pin trùng lib chung. **Không** gộp chung venv/`requirements` — sidecar có dependency set riêng để giữ nhẹ và tránh xung đột.

---

## 3. Sơ đồ tổng thể

```
┌──────────────────────────┐          ┌──────────────────────────────────────────┐
│  SUPERSET (NGUYÊN BẢN)    │          │  superset-ai/  (FastAPI — process riêng)    │
│                           │          │                                            │
│  Frontend (React/TS)      │  HTTPS   │  ┌────────────────────────────────────┐    │
│  ┌─────────────────────┐  │  + token │  │ API Gateway (FastAPI)               │    │
│  │ Ask AI Panel (THÊM) │──┼──user───→│  │  /ask /ask/stream /sql/* /health    │    │
│  └─────────────────────┘  │          │  └──────────────┬─────────────────────┘    │
│                           │          │  ┌──────────────▼─────────────────────┐    │
│  REST API v1 ◄────────────┼──gọi NHÂN│  │ LLM Orchestrator (Claude tool-use)  │    │
│   /dataset /database      │  DANH user│  └──────────────┬─────────────────────┘    │
│   /sqllab/execute /chart  │ (token   │  ┌──────────────▼─────────────────────┐    │
│   → chạy với quyền user   │  pass-   │  │ Tool layer (httpx → Superset API)   │    │
│     (áp RBAC + RLS)       │  through)│  └──────────────┬─────────────────────┘    │
│                           │          │  ┌──────────────▼─────────────────────┐    │
│  (KHÔNG nạp lib AI nào)   │          │  │ "Smart" modules (tune tự do):       │    │
│                           │          │  │  SQL reader/gen, schema indexer, RAG│    │
└──────────────────────────┘          │  └─────────────────────────────────────┘    │
        load Superset KHÔNG đổi         │  store + cache RIÊNG (không đụng DB Superset)│
                                       └──────────────────────────────────────────┘
```

**Biên giới an toàn:** sidecar không chạm DB phân tích trực tiếp. Mọi đọc metadata/chạy SQL đi qua REST API Superset **với token user** → tự kế thừa RBAC, RLS, audit log.

---

## 4. Cấu trúc folder `superset-ai/`

```
superset-6.0.1-vi/
├── superset/                  # core — KHÔNG đụng
├── superset-frontend/         # + thêm Ask AI panel (mục 6)
├── superset-ai/               # ⬅ sidecar (process riêng)
│   ├── pyproject.toml         # ruff/mypy bám Superset  ✅ đã tạo
│   ├── requirements/
│   │   ├── base.in / base.txt          # fastapi, uvicorn, httpx... + pin trùng lib chung
│   │   └── development.in / *.txt      # ruff, mypy, pytest
│   ├── Dockerfile             # FROM python:3.11.13-slim-bookworm  ✅ đã tạo
│   ├── .env.example           # ✅ đã tạo
│   ├── README.md              # ✅ đã tạo
│   ├── superset_ai/
│   │   ├── main.py            # FastAPI app factory  ✅ đã tạo
│   │   ├── config.py          # Settings env SUPERSET_AI_*  ✅ đã tạo
│   │   ├── api/
│   │   │   ├── health.py      # /health  ✅ đã tạo
│   │   │   ├── ask.py         # /ask, /ask/stream (SSE)
│   │   │   └── sql.py         # /sql/explain, /sql/fix, /sql/generate
│   │   ├── auth/
│   │   │   └── passthrough.py # nhận token user → đính vào call Superset
│   │   ├── superset_client/   # ↩ TÁI DÙNG từ mcp-superset
│   │   │   ├── client.py      # httpx, retry, RISON, CSRF, referer
│   │   │   └── endpoints.py   # wrap /dataset /database /sqllab /chart
│   │   ├── llm/
│   │   │   ├── base.py        # interface đổi provider
│   │   │   └── anthropic_client.py  # Claude tool-use + caching + streaming
│   │   ├── tools/             # registry + metadata/sql/viz tools (map vào client)
│   │   ├── smart/             # sql_reader, sql_generator, schema_indexer,
│   │   │                      #   semantic_layer, vector_store
│   │   ├── store/             # hội thoại + cache RIÊNG (SQLite/Postgres/Redis)
│   │   └── prompts/system.py
│   └── tests/                 # ✅ test_health.py đã tạo
└── docker-compose.yml         # + service superset-ai
```

> Skeleton Phase 0 (FastAPI) đã đúng mô hình sidecar — **không cần đổi**, chỉ bổ sung dần các thư mục còn lại theo phase.

---

## 5. Sidecar — thiết kế

### 5.1 Đọc Superset qua REST API
| Nhu cầu | Endpoint Superset | Ghi chú |
|---|---|---|
| Liệt kê dataset | `GET /api/v1/dataset/` | RISON pagination |
| Schema dataset (cột/kiểu) | `GET /api/v1/dataset/{id}` | nguồn grounding |
| DB/schema/bảng | `GET /api/v1/database/...` | dựng bản đồ kiến trúc |
| **Chạy SQL (chỉ SELECT)** | `POST /api/v1/sqllab/execute/` | **chạy với quyền user → áp RLS** |
| Ước tính chi phí | `POST /api/v1/sqllab/estimate/` | nếu engine hỗ trợ |
| Chart (list/tạo/sửa) | `GET/POST /api/v1/chart/` | sau flag write |

### 5.2 Token pass-through (giữ RLS)
1. User đăng nhập Superset (SSO sẵn có) → frontend có session/JWT.
2. Ask AI Panel gọi sidecar kèm token đó.
3. `auth/passthrough.py` đính token vào **mọi** request tới REST API Superset.
4. Superset thực thi dưới danh tính user → RBAC + RLS áp đúng từng người.
> CORS cho origin Superset; TLS production. Khuyến nghị reverse proxy chung domain để gọn CORS.

### 5.3 REST API của sidecar
| Method | Path | Mô tả |
|---|---|---|
| POST | `/ask` | Hỏi + context → trả lời + SQL/bảng/chart |
| POST | `/ask/stream` | SSE streaming token + sự kiện tool |
| POST | `/sql/generate` | text→SQL (dialect-aware) |
| POST | `/sql/explain` | giải thích/đặt tên SQL |
| POST | `/sql/fix` | sửa SQL từ lỗi DB |
| GET | `/health` | trạng thái LLM/cấu hình ✅ |

### 5.4 "Smart" modules — nơi làm AI khôn (tune độc lập)
- **SQL Reader/Validator**: SQLGlot parse, giải thích tiếng Việt, **chặn DDL/DML**, ép LIMIT/timeout.
- **SQL Generator**: text→SQL dialect-aware (biết MySQL client bạn đã thêm), few-shot nghiệp vụ, vòng tự sửa (sinh → chạy → đọc lỗi → sửa).
- **Schema/Architecture Indexer**: crawl metadata qua REST API → bản đồ kiến trúc DB, cache lại.
- **Semantic layer / glossary**: thuật ngữ tiếng Việt ↔ cột/bảng thật.
- **Vector store / RAG**: embedding schema + câu hỏi mẫu → grounding (tiết kiệm token, tăng chính xác).

### 5.5 LLM & an toàn
- **Claude (Anthropic API)**, model mới nhất (`claude-sonnet-4-6` / `claude-opus-4-8`), tool use + prompt caching. Trừu tượng `llm/base.py` để đổi provider.
- Chỉ SELECT; chặn DDL/DML; sanitize lỗi (redact connection string/key/path/IP); response size guard (~25K token); **rate limit theo user** (bảo vệ Superset khỏi quá tải).

---

## 6. Frontend — phần THÊM duy nhất

```
superset-frontend/src/features/aiAssistant/
├── components/  AskAIPanel.tsx, ChatMessage.tsx, SqlResultBlock.tsx,
│               TableResultBlock.tsx, ChartPreviewBlock.tsx, SuggestedPrompts.tsx
├── hooks/useAskAI.ts          # gọi sidecar (SSE), đính token user
├── store/aiAssistantSlice.ts
└── config.ts                  # URL sidecar (env build-time)
```
- Nút **"Ask AI"** navbar → Drawer; nút trong SQL Lab (Explain/Fix/Generate), Explore (Suggest viz).
- Chuẩn dự án: `@superset-ui/core/components`, antd tokens, **không `any`**, Jest + RTL.
- **Sidecar offline → panel báo "AI offline", Superset chạy bình thường** (cô lập lỗi).

---

## 7. Triển khai chạy cạnh nhau

```yaml
# docker-compose.yml (thêm service riêng — KHÔNG đổi service superset)
services:
  superset:
    # ... bản hiện tại, giữ nguyên
  superset-ai:
    build: ./superset-ai            # base image python:3.11.13-slim-bookworm
    environment:
      - SUPERSET_AI_SUPERSET_BASE_URL=http://superset:8088
      - SUPERSET_AI_ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - SUPERSET_AI_LLM_MODEL=claude-sonnet-4-6
    ports: ["8800:8800"]
    depends_on: [superset]
```
Frontend trỏ tới sidecar qua env build-time / reverse proxy chung domain.

---

## 8. Tái dùng từ `mcp-superset`

| Thành phần | Tái dùng? |
|---|---|
| `client.py` (httpx, retry, RISON, CSRF, referer) | ✅ Gần nguyên |
| Tool schema / danh mục tool | ✅ Cao |
| Logic an toàn SQL (keyword chặn, bảo vệ role) | ✅ Copy được |
| Tri thức quirk API (RISON, `NATIVE_FILTER-<uuid>`) | ✅ Cao |
| `auth.py` login service-account | ⚠️ Thay bằng token pass-through |
| Transport MCP/FastMCP | ❌ Dùng REST FastAPI |

> Kiểm tra **license** repo `bintocher/mcp-superset` trước khi copy; giữ attribution + ASF header.

---

## 9. Lộ trình (phases)

### Phase 0 — Skeleton + môi trường (~2–3 ngày) · *đang làm*
- Folder `superset-ai/` FastAPI + `/health`, `pyproject.toml` (ruff/mypy bám Superset), `Dockerfile` cùng base image, ASF header. ✅ đã scaffold.
- **Còn lại**: hoàn tất `requirements/*.txt`, dựng venv 3.11, chạy `ruff`/`mypy`/`pytest` xanh + build Docker.

### Phase 1 — Client + đọc qua API (~1 tuần)
- `superset_client` (tái dùng từ A), **token pass-through**, tool tối thiểu: `list_datasets`, `get_dataset_schema`, `run_select_sql` (chỉ SELECT).
- Test gọi REST API với quyền user thật (kiểm chứng RLS).

### Phase 2 — Q&A + Text-to-SQL (~1–1.5 tuần)
- LLM orchestrator tool-use; system prompt + few-shot (vi/en).
- `/ask` + `/ask/stream` (SSE); `/sql/explain|fix|generate`; SQL Reader/Validator (SQLGlot); lưu hội thoại.

### Phase 3 — Smart modules (~1–2 tuần, lặp dần)
- Schema/Architecture Indexer + Semantic layer + Vector store (RAG) + vòng tự sửa SQL.

### Phase 4 — Frontend Ask AI Panel (~1–1.5 tuần)
- Drawer chat + Redux + hook SSE (đính token). Render text/SQL/table/chart-preview; "Open in SQL Lab" / "Save as chart". Jest + RTL.

### Phase 5 — Hardening & vận hành (~3–5 ngày)
- Rate limit, response guard, sanitize, CORS/TLS, docker-compose, logging/metrics; tài liệu; `UPDATING.md`.

---

## 10. Rủi ro & giảm thiểu

| Rủi ro | Giảm thiểu |
|---|---|
| AI gây tải lên Superset | Rate limit theo user, timeout, chỉ SELECT, ép LIMIT |
| Mất RLS/phân quyền | **Token pass-through** — mọi API gọi nhân danh user |
| Overhead HTTP / giới hạn REST | Cache schema, RAG; bổ sung endpoint khi cần (không sửa core) |
| LLM sinh SQL nguy hiểm | Validate AST, chặn DDL/DML, luôn show SQL cho user duyệt |
| Rò rỉ dữ liệu ra LLM | RAG gửi schema + sample giới hạn, cờ tắt sample, cân nhắc LLM self-host |
| CORS/đa domain | Reverse proxy chung domain hoặc CORS chặt |
| Lệ thuộc code community | Tái dùng có chọn lọc + kiểm tra license |

---

## 11. Định nghĩa hoàn thành (DoD)

- [ ] `superset-ai/` chạy **tiến trình riêng**; **tắt sidecar không ảnh hưởng Superset** (kiểm chứng).
- [ ] Superset **không nạp thêm lib AI**, RAM/khởi động không đổi; sidecar không cài Superset.
- [ ] Môi trường: Python 3.11, `ruff`/`mypy`/`pytest` xanh, Docker cùng base image, lib chung pin trùng.
- [ ] User hỏi tiếng Việt → trả lời + SQL chạy được + bảng/chart, **đúng quyền & RLS** (2 user khác RLS).
- [ ] Đọc dữ liệu hoàn toàn qua REST API; chặn DDL/DML; sanitize; rate limit.
- [ ] "Open in SQL Lab" / "Save as chart" hoạt động.
- [ ] Test: pytest (sidecar) + Jest/RTL (panel) xanh.
- [ ] Tài liệu vận hành + cấu hình env/khóa LLM.

---

## 12. Tham chiếu nhanh (Phase 0)

```bash
# Dựng & kiểm tra môi trường sidecar
cd superset-ai
python3.11 -m venv .venv && source .venv/bin/activate   # cần python3.11-venv
pip install -r requirements/development.txt
ruff check . && ruff format --check . && mypy superset_ai && pytest
uvicorn superset_ai.main:app --host 0.0.0.0 --port 8800 --reload
curl -s http://localhost:8800/health | jq

# (tùy chọn) spike mcp-superset để xác nhận REST API + trích bản đồ tool
uvx mcp-superset   # KHÔNG dùng production (login service-account, mất RLS)
```
