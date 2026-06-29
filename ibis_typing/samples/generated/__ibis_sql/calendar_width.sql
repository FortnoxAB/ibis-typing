{{ config(database='my_database', schema='my_schema', materialized='incremental', incremental_strategy='merge', unique_key=[]) }}
{% if is_incremental() %}
SELECT
  ANY_VALUE("t8"."checksum_updated_at") AS "checksum_updated_at",
  DATE_DIFF('DAY', MIN("t8"."day"), MAX("t8"."day")) AS "day_span"
FROM (
  SELECT
    "t7"."checksum_updated_at",
    "t7"."day"
  FROM (
    SELECT
      "t6"."checksum_updated_at",
      "t6"."checksum",
      "t3"."day"
    FROM (
      SELECT
        *
      FROM {{ ref("calendar_checksum_bucket") }} AS "t0"
      WHERE
        "t0"."checksum_updated_at" > (
          SELECT
            MAX("t2"."checksum_updated_at") AS "Max(checksum_updated_at)"
          FROM {{ this }} AS "t2"
        )
    ) AS "t6"
    LEFT OUTER JOIN {{ source("my_schema", "calendar") }} AS "t3"
      ON TRUE
  ) AS "t7"
) AS "t8"
{% else %}
SELECT
  ANY_VALUE("t5"."checksum_updated_at") AS "checksum_updated_at",
  DATE_DIFF('DAY', MIN("t5"."day"), MAX("t5"."day")) AS "day_span"
FROM (
  SELECT
    "t4"."checksum_updated_at",
    "t4"."day"
  FROM (
    SELECT
      "t2"."checksum_updated_at",
      "t2"."checksum",
      "t3"."day"
    FROM {{ ref("calendar_checksum_bucket") }} AS "t2"
    LEFT OUTER JOIN {{ source("my_schema", "calendar") }} AS "t3"
      ON TRUE
  ) AS "t4"
) AS "t5"
{% endif %}