Tạo chart mới ngay trên dashboard nhúng (Pha 8 của EMBEDDED_HIERARCHICAL_PERSONALIZATION_PLAN.md)

Trạng thái: **chưa triển khai**. Quyết định đã chốt 2026-08-01. Đọc cùng
`EMBEDDED_HIERARCHICAL_PERSONALIZATION_PLAN.md` (Pha 1–7 đã xong: resolve
cascade, allow-list chart, capabilities role/user, lưu layout user/role).

---

## 1. Mục tiêu

Guest (embedded) có thể **tự tạo chart mới** từ các dataset được cấp, với giao
diện dựng chart **đầy đủ như Explore của admin**, rồi đưa chart đó vào layout
riêng của mình. Chart mới:

- **không** thuộc master dashboard, **không** sửa dữ liệu gốc;
- thuộc **user** (chỉ mình thấy) hoặc thuộc **role** (cả role thấy, nếu người
  tạo có quyền tạo chart cho role);
- **dùng chung cho mọi dashboard** mà user/role đó truy cập (không khoá theo
  một dashboard);
- **không** cho phép tạo/sửa dataset mới trong embed — chỉ chọn dataset có sẵn.

## 2. Quyết định đã chốt (2026-08-01)

| # | Câu hỏi | Chốt |
|---|---|---|
| 1 | Phạm vi dataset được chọn | Whitelist 2 tầng: **(dashboard, role)** và **(dashboard, user)** — cùng pattern grant/deny như allow-list chart hiện có |
| 2 | Chart mới thuộc về ai | **user**, hoặc **role** nếu có quyền; **dùng chung cho mọi dashboard** của user/role đó |
| 3 | Trải nghiệm dựng chart | **Y như giao diện admin** (Explore đầy đủ) ⇒ có preview ad-hoc trước khi lưu |
| 4 | Cách làm UI | **Phương án B** — builder nằm trong bundle embedded, không mở route `/explore/` cho guest |

## 3. Hai xung đột thiết kế phát sinh và cách giải

### 3.1 Chart dùng chung mọi dashboard × whitelist dataset theo dashboard

Chart tạo trên dashboard A (dataset X) sẽ xuất hiện ở pool của dashboard B —
nơi dataset X có thể **không** được cấp cho role/user đó.

**Giải (fail-closed, mặc định của plan này):** chart riêng chỉ hiện trên một
dashboard nếu `chart.datasource_id ∈ effective_datasets(dashboard, role, user)`
của **dashboard đang xem**. Chart không bị xoá, chỉ ẩn; khi admin cấp lại
dataset thì nó hiện lại. Cùng triết lý với `_GuestRlsHardeningMixin`.

### 3.2 Role chart dùng chung mọi dashboard × trùng tên role giữa các tenant

Trong mô hình hiện tại **workspace == dashboard (1:1)** (xem docstring
`superset/embed_layout/models.py`), nên mọi bảng đều khoá theo `dashboard_id`.
Nếu chart của role trở thành **toàn cục**, mà hai khách hàng khác nhau đều dùng
role tên `manager`, thì chart role của khách A sẽ hiện cho khách B. Đây là rò
dữ liệu chéo tenant, không phải chuyện thẩm mỹ.

**Giải:** khoá chart-của-role theo cặp **(workspace_key, role)**, với
`workspace_key = token.user.workspace_id`. Claim này đã được đọc sẵn trong
`get_guest_identity` (`superset/embed_layout/service.py`) nhưng hiện chưa dùng.

⚠️ **Điều kiện vận hành bắt buộc:** hệ thống cấp token phải luôn set
`workspace_id` cho mọi guest token. Nếu `workspace_id` rỗng, plan này coi role
scope là **không khả dụng** (chỉ cho tạo chart scope `user`) thay vì rơi về
phạm vi toàn cục — fail-closed. Chart scope `user` khoá theo `user_key`
(username trong token) nên không bị ảnh hưởng.

## 4. Data model (bảng mới + thay đổi)

### 4.1 `embed_role_dataset` — whitelist dataset theo role

```
id            PK
dashboard_id  FK dashboards.id  ON DELETE CASCADE, index
role          String(255), index
dataset_id    FK tables.id      ON DELETE CASCADE
UNIQUE (dashboard_id, role, dataset_id)
```

### 4.2 `embed_user_dataset` — grant/deny theo user (đè lên role)

```
id            PK
dashboard_id  FK dashboards.id  ON DELETE CASCADE, index
user_key      String(255), index
dataset_id    FK tables.id      ON DELETE CASCADE
mode          String(10)  'grant' | 'deny'
UNIQUE (dashboard_id, user_key, dataset_id)
```

### 4.3 `embed_owned_chart` — chủ sở hữu của chart do embed tạo

```
id                 PK
chart_id           FK slices.id ON DELETE CASCADE, UNIQUE   -- 1 slice = 1 chủ
scope              String(10)  'user' | 'role'
user_key           String(255) NULL, index   -- bắt buộc khi scope='user'
role               String(255) NULL, index   -- bắt buộc khi scope='role'
workspace_key      String(255) NULL, index   -- bắt buộc khi scope='role' (§3.2)
created_from_dashboard_id  FK dashboards.id NULL ON DELETE SET NULL  -- chỉ để truy vết
created_by_key     String(255)              -- user_key của người tạo
created_on / updated_on  DateTime
CHECK: (scope='user' AND user_key IS NOT NULL)
    OR (scope='role' AND role IS NOT NULL AND workspace_key IS NOT NULL)
```

Không dùng `slices.owners` / `created_by_fk`: guest không có row trong
`ab_user`. Hai cột đó để NULL (`AuditMixinNullable` cho phép).

### 4.4 Hai capability mới

Thêm vào `CAPABILITY_FIELDS` (`superset/embed_layout/models.py`):

- `can_create_charts` — tự tạo chart cho chính mình
- `can_create_role_charts` — publish chart cho cả role

Migration `ALTER TABLE`: `embed_role_perm` (NOT NULL, default `False`),
`embed_user_perm` (nullable — tri-state override, `NULL` = kế thừa role).
Tách khỏi `can_add_charts` hiện có (đó là "thêm chart **có sẵn**" vào layout,
đọc bởi `SliceAdder`), vì tạo chart là quyền ghi + query ad-hoc.

## 5. Quy tắc phân giải

### 5.1 `effective_datasets(dashboard_id, role, user_key)`

```
role_ids  = {embed_role_dataset where dashboard_id, role}
grants    = {embed_user_dataset where dashboard_id, user_key, mode='grant'}
denies    = {embed_user_dataset where dashboard_id, user_key, mode='deny'}
result    = (role_ids | grants) - denies
```

⚠️ Khác `_compute_allowed` của chart: khi role **chưa** cấu hình gì,
`result = ∅` (**fail-closed**), không phải "toàn bộ". Lý do: pool chart đã bị
giới hạn tự nhiên bởi `dashboard.slices`; dataset thì không có giới hạn tự
nhiên nào — mặc định permissive sẽ mở toàn bộ instance.

### 5.2 `owned_charts(identity)`

```
user_charts = {embed_owned_chart where scope='user' and user_key = identity.user_key}
role_charts = {embed_owned_chart where scope='role'
                 and role = identity.role
                 and workspace_key = identity.workspace_id}   -- rỗng nếu workspace_id NULL
```

### 5.3 Pool hiệu lực trên một dashboard

```
master_pool  = dashboard.slices                                  -- như hiện nay
private_pool = {c in owned_charts(identity)
                  if c.datasource_id in effective_datasets(...)} -- §3.1
pool         = master_pool | private_pool
allowed      = _compute_allowed(master_pool, role allow-list, user grants/denies)
               | private_pool                                    -- chart riêng luôn allowed cho chủ
```

Phải sửa trong `superset/embed_layout/service.py`: `_pool_ids`,
`_compute_allowed`, `resolve_layout`, và validation chart-id trong
`save_user_layout` / `save_role_layout` (hiện đều clamp cứng vào
`dashboard.slices`).

## 6. API backend (`/api/v1/embed_layout/`)

| Method | Route | Mô tả |
|---|---|---|
| GET | `/datasets/<dash>/` | Danh sách dataset được cấp + metadata đủ để control panel chạy |
| POST | `/chart/<dash>/` | Tạo chart. Body: `scope`, `slice_name`, `viz_type`, `datasource_id`, `params`, `query_context` |
| PUT | `/chart/<chart_id>/` | Sửa chart mình sở hữu (role chart cần `can_create_role_charts`) |
| DELETE | `/chart/<chart_id>/` | Xoá chart mình sở hữu + dọn khỏi layout user/role |
| GET | `/charts/mine/<dash>/` | Thư viện chart riêng (hoặc gộp vào `resolve`) |

`resolve` mở rộng thêm 4 khoá: `allowed_datasets`, `owned_charts`,
`slice_payloads`, `datasource_payloads` (§8.2).

**Không** mở `/api/v1/dataset/` hay `/api/v1/chart/` cho guest:

- `DatasourceFilter` (`superset/views/base.py:534`) lọc theo perm
  `datasource_access` → guest luôn rỗng; muốn mở phải cấp perm cho **role FAB
  dùng chung**, tức mọi guest token đều được nâng quyền → không phân biệt được
  role/user/dashboard.
- `POST /api/v1/chart/` không dùng được: `CreateChartCommand.validate` gọi
  `populate_owners` với `g.user` (`superset/commands/chart/create.py:76`), mà
  `GuestUser` không có `.id` → vỡ.
- Payload dataset của FAB lộ `sql`, `database`, `template_params`, `owners`.

### 6.1 Payload dataset trả cho guest

Chỉ những field control panel cần: `id`, `uid`, `type='table'`, `table_name`,
`columns[]` (`column_name`, `verbose_name`, `type`, `is_dttm`, `groupby`,
`filterable`), `metrics[]` (`metric_name`, `verbose_name`, `d3format`),
`main_dttm_col`, `granularity_sqla`, `time_grain_sqla`, `order_by_choices`,
`verbose_map`, `column_formats`, `owners: []`, và `database` **rút gọn**
(`backend`, `allows_subquery: false`, `disable_data_preview: true`).

Lưu ý: `DashboardDatasetSchema.post_dump` xoá hẳn `database` cho guest
(`superset/dashboards/schemas.py:306`), nhưng control panel **cần**
`database.backend` để render time grain → endpoint mới phải tự trả bản rút gọn
chứ không tái dùng schema đó.

## 7. Security manager — 3 nhánh có điều kiện

Tất cả nằm trong `superset/security/manager.py`, đều gắn điều kiện, **không**
nới toàn cục.

### 7.1 Query preview ad-hoc (`raise_for_access`, nhánh datasource ~L583)

Hiện guest chỉ query được khi `form_data.dashboardId` có **và** slice thuộc
dashboard đó. Thêm nhánh:

```
is_guest_user()
AND cap(can_create_charts) trên dashboard trong form_data.dashboardId
AND datasource.id ∈ effective_datasets(dashboard_id, role, user_key)
AND payload qua được validator §7.4
```

### 7.2 `query_context_modified` (~L164)

Hàm này chặn guest đổi `metrics`/`columns`/`groupby`/`orderby` so với chart đã
lưu. **Không sửa hàm** — bọc điều kiện tại chỗ gọi (~L558): chỉ bỏ qua khi

- request **không** có `slice_id` (đang preview chart chưa lưu), **hoặc**
- `slice_id` là chart thuộc `owned_charts(identity)`.

Slice thuộc master dashboard vẫn bị chặn nguyên như cũ — nếu không, mọi guest
token sẽ đổi được payload của chart được share.

### 7.3 Render chart riêng (`raise_for_access`, điều kiện `slc in dashboard_.slices`)

Chart riêng không nằm trong `dashboard_slices` → thêm `or is_owned_embed_chart(slc, identity)`.

### 7.4 Validator payload (dùng ở **cả** create/update **và** data query)

Guest cầm token gọi API trực tiếp được, nên validate ở tầng service, không dựa
vào UI:

| Kiểm tra | Quy tắc |
|---|---|
| datasource | `datasource_type == 'table'` và `id ∈ effective_datasets` |
| viz_type | ∈ `EMBED_ALLOWED_VIZ_TYPES`. **Chặn `handlebars`** (render HTML thô → XSS trong iframe khách) |
| adhoc metric/column | `expressionType == 'SIMPLE'` nếu `EMBED_ALLOW_ADHOC_SQL=False` (mặc định) |
| adhoc filter | chặn `expressionType == 'SQL'`, `where`, `having` dạng tự do khi cờ trên = False |
| Jinja | reject mọi `{{`, `{%`, và `template_params` khác rỗng |
| row_limit | ≤ `EMBED_MAX_ROW_LIMIT` |
| kích thước | `params` + `query_context` ≤ `EMBED_MAX_CHART_JSON_BYTES` |
| quota | số chart/user ≤ `EMBED_MAX_CHARTS_PER_USER` |
| slice_name | strip, ≤ 250 ký tự |

Về `EMBED_ALLOW_ADHOC_SQL=True` (nếu sau này cần "y như admin" trọn vẹn): rủi
ro được giảm nhưng **không** biến mất — `sanitize_clause`
(`superset/sql/parse.py:1506`) chặn multi-statement, feature flag
`ALLOW_ADHOC_SUBQUERY` mặc định `False` (`superset/config.py:552`) chặn
subquery, và RLS vẫn thêm `WHERE`. Còn lại: guest viết được biểu thức/hàm DB
tuỳ ý trên dataset được cấp. Nên để `False` và chỉ bật cho tenant tin cậy.

## 8. Frontend

### 8.1 Builder modal — tin tốt về store

`src/embedded/EmbeddedContextProviders.tsx:31` dùng **store toàn cục**
`src/views/store`, mà store này đã combine sẵn `explore`, `saveModal`,
`exploreDatasources` (`src/views/store.ts:38-40`), và `DynamicPluginProvider`
đã có mặt → **mount được control panel của Explore trong embed mà không cần
store lồng, plugin viz load bình thường**. Đây là lý do phương án B đạt được
"y như admin" mà không phải mở route `/explore/`.

Component mới `src/embedded/EmbedChartBuilderModal.tsx`, bố cục 3 cột như
Explore, tái dùng: `DatasourcePanel`, `ControlPanelsContainer`,
`ExploreChartPanel`, `getControlsState` / `getFormDataFromControls`,
`hydrateExplore`.

Thay/ẩn: `SaveModal` của Explore (lưu `/api/v1/chart/` + gắn dashboard) → save
riêng của embed, có chọn scope **"Chỉ tôi"** / **"Cả role X"** (mục sau chỉ
hiện khi `can_create_role_charts` và `workspace_id` có giá trị). Ẩn: "Edit
dataset", "View query", "Share/permalink", dropdown dataset đổi nguồn ngoài
whitelist.

Điểm vào: nút "Tạo chart" trên `EmbedPersonalizeBar` khi
`can('can_create_charts')`. Sau khi lưu: chart vào pool → kéo vào layout (đang
ở edit mode) → "Lưu view của tôi" theo luồng Pha 3 hiện có.

### 8.2 Inject chart/datasource vào bootstrap

Chart riêng không có trong `/api/v1/dashboard/<id>/charts` và `/datasets`, nên
`embedLayout.ts` phải **thêm** chứ không chỉ **cắt** (hiện chỉ có
`pruneLayoutToAllowed`, `src/embedded/embedLayout.ts:106`):

- merge `slice_payloads` → `charts` + `sliceEntities`;
- merge `datasource_payloads` → `datasources`;
- rồi mới prune như cũ.

Đây là phần frontend nặng thứ hai sau builder, và là chỗ dễ sinh bug "chart
trắng" nhất.

### 8.3 Thư viện chart trong `SliceAdder`

Gộp `allowed_charts` (chart của master dashboard) + `owned_charts`, có nhãn
phân biệt **Của tôi** / **Của role** / **Của dashboard**, kèm hành động Đổi
tên / Xoá cho chart mình sở hữu.

### 8.4 Trang admin (`src/pages/EmbedAdmin/index.tsx`)

- 2 tab mới: **Dataset theo role**, **Dataset theo user** (grant/deny).
- 2 cột capability mới trong bảng quyền role + user.
- 1 tab **Chart do embed tạo**: xem theo user/role/workspace, admin thu hồi
  hoặc chuyển scope. Cần vì `slices` sẽ có chart không có owner FAB — nếu
  không có trang này thì không ai quản được.

## 9. Ma trận quyền

| Hành động | Điều kiện |
|---|---|
| Mở builder | `can_create_charts` |
| Thấy dataset trong picker | `dataset ∈ effective_datasets(dashboard, role, user)` |
| Preview (query ad-hoc) | `can_create_charts` + dataset trong whitelist + qua validator |
| Lưu chart scope `user` | `can_create_charts` |
| Lưu chart scope `role` | `can_create_role_charts` **và** `workspace_id` có giá trị |
| Sửa/xoá chart `user` | là chủ (`user_key` khớp) |
| Sửa/xoá chart `role` | `can_create_role_charts` + cùng `(workspace_key, role)` |
| Đưa chart riêng vào layout user | `can_customize_layout` (như Pha 3) |
| Đưa chart riêng vào layout role | `can_edit_role_layout` (như Pha 3) |

## 10. RLS — điều kiện bắt buộc để chart mới có dữ liệu

RLS đang **fail-closed** (`docker/pythonpath_dev/superset_config.py`,
`_GuestRlsHardeningMixin`): guest query dataset mà token không mang clause →
tiêm `1 = 0` → 0 dòng.

⇒ Hệ thống cấp token phải mint `rls_rules` cho **mọi** dataset nằm trong
whitelist của (dashboard, role, user), không chỉ dataset của các chart trên
dashboard. Dataset dùng chung (lookup/mapping) thì đưa vào
`guest_rls_exempt_dataset` (Settings → "Guest RLS Exempt Datasets").

Triệu chứng nếu quên: chart mới lưu thành công, render được, nhưng **luôn rỗng**
— dễ bị chẩn đoán sai thành bug builder.

## 11. Dọn dẹp & đối soát

| Sự kiện | Xử lý |
|---|---|
| Xoá dataset | FK CASCADE dọn whitelist; chart riêng dùng dataset đó → `slices` mồ côi ⇒ job dọn hoặc ẩn |
| Rút dataset khỏi whitelist | Chart riêng tự ẩn theo §3.1, layout giữ nguyên (không xoá dữ liệu) |
| Xoá chart riêng | Xoá row `embed_owned_chart` + `slices` + gỡ node khỏi `embed_user_layout` / `embed_workspace_role_layout` của mọi dashboard |
| Đổi role của user | Chart scope `user` giữ; chart scope `role` cũ biến mất khỏi pool (đúng ý nghĩa) |
| Xoá dashboard | Whitelist CASCADE; chart riêng **giữ lại** (chúng toàn cục theo user/role) |

## 12. Pha triển khai

| Pha | Nội dung | Tiêu chí xong |
|---|---|---|
| **8.1** | Migration + 3 bảng + 2 capability + `effective_datasets` + `GET /datasets/<dash>/` | curl với guest token trả đúng whitelist; role chưa cấu hình → rỗng |
| **8.2** | 3 nhánh security manager + validator §7.4 | POST `/api/v1/chart/data` ad-hoc trên dataset được cấp → có dữ liệu; dataset ngoài whitelist → 403; jinja/SQL adhoc → 400 |
| **8.3** | Create/update/delete chart + `resolve` mở rộng + inject frontend §8.2 | Chart tạo bằng curl render được trong embed, không xuất hiện với user/role khác |
| **8.4** | Builder modal §8.1 + save scope | Dựng chart end-to-end trên UI nhúng, có preview |
| **8.5** | Admin UI §8.4 | Admin cấp/thu whitelist + xem/thu hồi chart embed |
| **8.6** | Hardening | Quota, viz allowlist, test negative (jinja, SQL adhoc, dataset lạ, chart người khác), dọn dẹp §11 |

Rủi ro cao nhất: **8.3** (inject bootstrap — dễ bug âm thầm) và **8.2**
(validator — đây là biên bảo mật thật sự, cần test negative đầy đủ).

## 13. Câu hỏi còn mở

1. `workspace_id` hiện có được app cấp token set cho mọi token chưa? Nếu chưa
   → chart scope `role` không dùng được đến khi bổ sung (§3.2).
2. Đồng ý quy tắc ẩn chart riêng khi dataset không nằm trong whitelist của
   dashboard đang xem (§3.1) chứ không phải "đã tạo là luôn thấy"?
3. `EMBED_ALLOW_ADHOC_SQL` để `False` mặc định (chặn metric SQL tự do) —
   chấp nhận builder hơi kém "y như admin" ở điểm này?
