-- Licensed to the Apache Software Foundation (ASF) under one
-- or more contributor license agreements.  See the NOTICE file
-- distributed with this work for additional information
-- regarding copyright ownership.  The ASF licenses this file
-- to you under the Apache License, Version 2.0 (the
-- "License"); you may not use this file except in compliance
-- with the License.  You may obtain a copy of the License at
--
--   http://www.apache.org/licenses/LICENSE-2.0
--
-- Unless required by applicable law or agreed to in writing,
-- software distributed under the License is distributed on an
-- "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
-- KIND, either express or implied.  See the License for the
-- specific language governing permissions and limitations
-- under the License.

-- Test fixture for DISPLAY_TIME_ZONE (see docs/docs/configuration/timezones.mdx).
--
-- Data is stored in UTC, as the feature assumes. Every row carries the wall
-- clock Superset is expected to show, so the dataset checks itself: no mental
-- arithmetic while reading a chart.
--
-- The rows straddle the 17:00 UTC / 00:00 Asia/Ho_Chi_Minh day boundary on
-- purpose, so the count per UTC day and the count per Vietnam day differ on
-- every single day. A chart grouped by day therefore states outright which
-- time zone the SQL ran in:
--
--   day         count by UTC (wrong)   count by VN (right)
--   2026-08-19  2                      1
--   2026-08-20  3                      2
--   2026-08-21  3                      4
--   2026-08-22  1                      2
--
-- Usage:
--   docker exec -i superset_db psql -U superset -d examples < tz_test.sql

DROP TABLE IF EXISTS tz_test;

CREATE TABLE tz_test (
  id           integer PRIMARY KEY,
  ts_naive     timestamp,        -- naive UTC: the common case
  ts_tz        timestamptz,      -- same instant, zone-aware: must NOT double convert
  ts_epoch     bigint,           -- same instant as epoch seconds
  d            date,             -- calendar date: must NOT shift
  utc_label    text,             -- what the raw data says
  vn_label     text,             -- what Superset must display
  vn_day       text,             -- the VN day the row must be grouped into
  bucket       text,             -- a dimension, to exercise grouped series
  amount       numeric
);

INSERT INTO tz_test (id, ts_naive, utc_label, vn_label, vn_day, bucket, amount) VALUES
  -- comfortably inside a day, no boundary involved
  (1, TIMESTAMP '2026-08-19 10:00:00', '2026-08-19 10:00', '2026-08-19 17:00', '2026-08-19', 'A', 10),

  -- 17:00 UTC is exactly midnight in Vietnam: this row belongs to the NEXT day
  (2, TIMESTAMP '2026-08-19 17:00:00', '2026-08-19 17:00', '2026-08-20 00:00', '2026-08-20', 'A', 20),

  -- one minute before the boundary: still the same VN day
  (3, TIMESTAMP '2026-08-20 16:59:00', '2026-08-20 16:59', '2026-08-20 23:59', '2026-08-20', 'B', 30),

  -- the boundary again, and one minute past it
  (4, TIMESTAMP '2026-08-20 17:00:00', '2026-08-20 17:00', '2026-08-21 00:00', '2026-08-21', 'A', 40),
  (5, TIMESTAMP '2026-08-20 17:01:00', '2026-08-20 17:01', '2026-08-21 00:01', '2026-08-21', 'B', 50),

  -- mid-morning in Vietnam
  (6, TIMESTAMP '2026-08-21 03:30:00', '2026-08-21 03:30', '2026-08-21 10:30', '2026-08-21', 'A', 60),

  -- the last second of a VN day
  (7, TIMESTAMP '2026-08-21 16:59:59', '2026-08-21 16:59:59', '2026-08-21 23:59:59', '2026-08-21', 'B', 70),

  -- straight into the next VN day
  (8, TIMESTAMP '2026-08-21 17:00:00', '2026-08-21 17:00', '2026-08-22 00:00', '2026-08-22', 'A', 80),
  (9, TIMESTAMP '2026-08-22 06:00:00', '2026-08-22 06:00', '2026-08-22 13:00', '2026-08-22', 'B', 90);

-- derive the other representations of the very same instant
UPDATE tz_test SET
  ts_tz    = ts_naive AT TIME ZONE 'UTC',
  ts_epoch = EXTRACT(EPOCH FROM ts_naive AT TIME ZONE 'UTC')::bigint,
  d        = ts_naive::date;

GRANT SELECT ON tz_test TO examples;
