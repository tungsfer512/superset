<!--
Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.  The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
-->

# Kiểm tra DISPLAY_TIME_ZONE trên UI

Fixture cho tính năng ở [docs/docs/configuration/timezones.mdx](../../docs/docs/configuration/timezones.mdx).
Dữ liệu lưu ở UTC; mỗi dòng mang sẵn giờ VN kỳ vọng nên không phải nhẩm.

```bash
docker exec -i superset_db psql -U superset -d examples < scripts/tz-test/tz_test.sql
```

## Vì sao bộ dữ liệu này phát hiện được lỗi

Các dòng nằm quanh mốc `17:00 UTC` = `00:00 VN`, nên số dòng theo **ngày UTC**
khác số dòng theo **ngày VN** ở cả 4 ngày:

| Ngày | Đếm theo UTC (SAI) | Đếm theo VN (ĐÚNG) |
|---|---|---|
| 2026-08-19 | 2 | **1** |
| 2026-08-20 | 3 | **2** |
| 2026-08-21 | 3 | **4** |
| 2026-08-22 | 1 | **2** |

Chỉ cần nhìn biểu đồ COUNT theo ngày là biết SQL chạy ở timezone nào.

## Chuẩn bị

1. **Thêm database connection** — Settings → Database Connections → + Database →
   PostgreSQL, URI: `postgresql://examples:examples@db:5432/examples`
2. **Tạo dataset** từ bảng `public.tz_test`.
3. Trong dataset, đánh dấu `is temporal` cho `ts_naive`, `ts_tz`, `ts_epoch`, `d`.
   Riêng `ts_epoch` phải đặt **Datetime format** = `epoch_s`.

## Các phép thử

### 1. Time grain theo ngày — phép thử chính

Chart Line/Bar, X-axis = `ts_naive`, Time grain = **Day**, Metric = `COUNT(*)`.

Kỳ vọng: **1, 2, 4, 2** cho ngày 19/20/21/22.
Nếu ra **2, 3, 3, 1** thì conversion chưa chạy.

Lặp lại với `ts_tz` và `ts_epoch` → phải ra **cùng một kết quả**.
`ts_tz` là ca dễ sai nhất: nó đã mang sẵn timezone, nếu bị đọc như UTC lần nữa
thì lệch thêm 7 tiếng. Đây chính là bug đã bị bắt bằng bộ dữ liệu này
(xem `test_tz_awareness_comes_from_the_declared_type`).

### 2. Cột DATE không được dịch

Cùng chart nhưng X-axis = `d`. Kỳ vọng: **2, 3, 3, 1** — tức KHÔNG đổi.
Một cột ngày không có phần giờ thì dịch nó chỉ làm sai lịch.

### 3. Giá trị hiển thị khớp nhãn kỳ vọng

Chart Table, Columns = `utc_label`, `vn_label`, `ts_naive`,
Time grain = **Original value**.

Kỳ vọng: cột `ts_naive` hiển thị **trùng khít** `vn_label` từng dòng, và lệch
đúng 7 tiếng so với `utc_label`.

### 4. Lọc theo khoảng thời gian

Vẫn chart Table, thêm Time range: `2026-08-21 ≤ col < 2026-08-22`.

Kỳ vọng: đúng **4 dòng**, id = 4, 5, 6, 7.
Nếu ra 3 dòng thì filter đang so ở UTC còn hiển thị ở VN — hai thứ lệch nhau.

### 5. Thời gian tương đối

Đổi Time range sang `Last week` / `today`. Mốc phải tính theo nửa đêm giờ VN,
không phải giờ UTC hay giờ máy chủ.

### 6. Timezone theo user

User info → Edit user → **Display time zone** = `Europe/Paris` (UTC+02:00 vào
tháng 8) → mở lại chart ở phép thử 1.

Kỳ vọng: phân bố đổi thành **2, 3, 3, 1**, vì `17:00 UTC` = `19:00` Paris, vẫn
cùng ngày. Đây cũng là phép thử cache: nếu vẫn thấy 1,2,4,2 thì cache key chưa
tách theo user.

### 7. Timezone khi nhúng

Nhúng dashboard với `urlParams: { timezone: 'Europe/Paris' }`.
Kỳ vọng giống phép thử 6. Bỏ tham số đi thì quay lại 1,2,4,2.

## Lưu ý quan trọng

**SQL Lab KHÔNG được convert** — đây là chủ ý, nó chạy đúng SQL bạn gõ. Query
`SELECT ts_naive FROM tz_test` trong SQL Lab sẽ ra giờ UTC. Đừng lấy SQL Lab làm
chuẩn để đối chiếu với chart.

Muốn xem SQL thật mà chart chạy: menu ba chấm của chart → **View query**.
Phải thấy `AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Ho_Chi_Minh'` bọc quanh cột
(hoặc chỉ một `AT TIME ZONE '<tz>'` nếu cột là `timestamptz`).

## Dọn dẹp

```bash
docker exec superset_db psql -U superset -d examples -c "DROP TABLE tz_test;"
```

## Kiểm tra một engine bất kỳ

`check_engine_timezones.py` dựng biểu thức convert bằng **chính engine spec của
Superset**, chạy nó, rồi so kết quả với `zoneinfo` của Python. Nhờ vậy nó bắt cả
trường hợp engine nhận tên zone nhưng dịch sai, không chỉ lỗi cú pháp.

```bash
# mẫu 10 zone khó (không DST, DST hai bán cầu, offset lẻ 45 phút)
docker compose exec superset \
  python scripts/tz-test/check_engine_timezones.py "postgresql://user:pw@host/db"

# quét toàn bộ 436 zone mà picker chào
docker compose exec superset \
  python scripts/tz-test/check_engine_timezones.py "postgresql://user:pw@host/db" --all
```

Kết quả đã đo (xem bảng đầy đủ trong
[docs/docs/configuration/timezones.mdx](../../docs/docs/configuration/timezones.mdx)):

| Engine | Cách convert | Zone đúng |
|---|---|---|
| PostgreSQL 16 | theo tên | 436 / 436 |
| MySQL 8 | theo tên, dự phòng offset | 436 / 436 |
| Trino 483 | theo tên | 436 / 436 |
| ClickHouse 24.10 | theo tên | 434 / 436 |
| SQLite | theo offset | 315 / 436 |

Dùng script này cho các engine cloud (BigQuery, Snowflake, Redshift,
Databricks) mà không dựng local được.
