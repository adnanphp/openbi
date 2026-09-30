{% macro round_currency(col, scale=2) %}
    ROUND({{ col }}::numeric, {{ scale }})
{% endmacro %}
