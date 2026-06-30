# Ask AI panel (`aiAssistant`)

Frontend cho dịch vụ `superset-ai` (sidecar). Cung cấp một panel chat hỏi–đáp
ngôn ngữ tự nhiên ngay trong Superset.

- **Self-contained**: state cục bộ (hook `useAskAi`), **không** cần wire vào
  Redux store toàn cục.
- **Gọi sidecar** qua `fetch` (`POST /ask`) với `credentials: 'include'` — đặt
  sidecar sau reverse proxy **cùng domain** để cookie phiên Superset được
  chuyển tiếp (giữ RBAC/RLS theo user).
- Tuân thủ chuẩn: `@superset-ui/core/components`, không `any`, functional +
  hooks, Jest + RTL.

## Cấu hình URL sidecar

Mặc định gọi `'/superset-ai'` (đường dẫn reverse proxy cùng domain). Đổi runtime:

```js
window.supersetAiBaseUrl = 'https://my-host:8800';
```

## Gắn vào giao diện

`AskAIButton` là entry point (nút + panel). Mount ở app shell, ví dụ trong
navbar/menu:

```tsx
import { AskAIButton } from 'src/features/aiAssistant';

// ... trong component của navbar:
<AskAIButton />
```

Hoặc tự điều khiển panel:

```tsx
import { AskAIPanel } from 'src/features/aiAssistant';

const [open, setOpen] = useState(false);
<AskAIPanel open={open} onClose={() => setOpen(false)} />
```

## Thành phần

| File | Vai trò |
|------|---------|
| `config.ts` | Phân giải URL sidecar |
| `api.ts` | `askAi()` gọi `POST /ask` |
| `hooks/useAskAi.ts` | State hội thoại (messages, status, error) |
| `components/AskAIButton.tsx` | Nút mở panel |
| `components/AskAIPanel.tsx` | Drawer chat (input, danh sách tin nhắn) |
| `components/ChatMessage.tsx` | Bong bóng tin nhắn + artifacts |
| `components/SqlResultBlock.tsx` | SQL đã chạy (có nút copy) |
| `components/TableResultBlock.tsx` | Bảng kết quả |
| `components/SuggestedPrompts.tsx` | Câu hỏi gợi ý |

## Còn lại (enhancement)

- Streaming token-level qua `POST /ask/stream` (SSE) — hiện dùng `/ask`
  non-stream cho đơn giản & ổn định.
- Nút "Open in SQL Lab" / "Save as chart" từ artifact.
- Tích hợp nút trong SQL Lab / Explore.
