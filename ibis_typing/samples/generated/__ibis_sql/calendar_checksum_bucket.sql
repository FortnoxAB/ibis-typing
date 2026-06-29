{{ config(database='my_database', schema='my_schema', materialized='incremental', incremental_strategy='merge', unique_key=[]) }}
{% if is_incremental() %}
SELECT
  "t13"."timestamp" AS "checksum_updated_at",
  "t13"."checksum"
FROM (
  SELECT
    "t12"."checksum_updated_at",
    "t12"."checksum",
    "t12"."checksum_updated_at_right",
    "t12"."checksum_right",
    "t3"."timestamp"
  FROM (
    SELECT
      "t10"."checksum_updated_at",
      COALESCE("t10"."checksum", 0) AS "checksum",
      "t10"."checksum_updated_at_right",
      "t10"."checksum_right"
    FROM (
      SELECT
        "t9"."checksum_updated_at",
        "t9"."checksum",
        "t4"."checksum_updated_at" AS "checksum_updated_at_right",
        "t4"."checksum" AS "checksum_right"
      FROM (
        SELECT
          "t7"."timestamp" AS "checksum_updated_at",
          "t7"."checksum"
        FROM (
          SELECT
            "t6"."checksum",
            "t3"."timestamp"
          FROM (
            SELECT
              CAST(BIT_XOR(HASH("t2"."day")) % 9223372036854775808 AS BIGINT) AS "checksum"
            FROM {{ source("my_schema", "calendar") }} AS "t2"
          ) AS "t6"
          INNER JOIN {{ ref("timestamp_now") }} AS "t3"
            ON TRUE
        ) AS "t7"
      ) AS "t9"
      FULL OUTER JOIN {{ this }} AS "t4"
        ON TRUE
    ) AS "t10"
    WHERE
      NOT (
        COALESCE("t10"."checksum", 0) IS NOT DISTINCT FROM "t10"."checksum_right"
      )
  ) AS "t12"
  INNER JOIN {{ ref("timestamp_now") }} AS "t3"
    ON TRUE
) AS "t13"
{% else %}
SELECT
  "t5"."timestamp" AS "checksum_updated_at",
  "t5"."checksum"
FROM (
  SELECT
    "t4"."checksum",
    "t2"."timestamp"
  FROM (
    SELECT
      CAST(BIT_XOR(HASH("t0"."day")) % 9223372036854775808 AS BIGINT) AS "checksum"
    FROM {{ source("my_schema", "calendar") }} AS "t0"
  ) AS "t4"
  INNER JOIN {{ ref("timestamp_now") }} AS "t2"
    ON TRUE
) AS "t5"
{% endif %}