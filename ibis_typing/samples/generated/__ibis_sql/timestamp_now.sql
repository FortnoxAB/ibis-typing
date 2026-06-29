{{ config(database='my_database', schema='my_schema', materialized='table') }}
SELECT
  CAST(CAST(CURRENT_TIMESTAMP AS TIMESTAMP) AS TIMESTAMP(6)) AS "timestamp"
FROM (
  SELECT
    CAST("t0"."timestamp" AS TIMESTAMP(6)) AS "timestamp"
  FROM (
    SELECT
      *
    FROM (VALUES
      (NULL)) AS TimestampNow__62f0537e(timestamp)
  ) AS "t0"
) AS "t1"