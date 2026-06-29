{% snapshot calendar_width_snapshot %}
{{ config(database='my_database', schema='my_schema', unique_key=[], strategy='timestamp', updated_at='checksum_updated_at') }}
SELECT
  *
FROM {{ ref("calendar_width") }}
{% endsnapshot %}