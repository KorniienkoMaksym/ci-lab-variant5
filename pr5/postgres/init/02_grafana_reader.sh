#!/bin/sh
# Окремий користувач лише для читання — для Grafana
# (принцип найменших привілеїв). Значення — з файлу .env.
set -e
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" \
     -d "$POSTGRES_DB" <<EOSQL
CREATE ROLE $GRAFANA_DB_USER LOGIN
    PASSWORD '$GRAFANA_DB_PASSWORD';
GRANT USAGE ON SCHEMA public TO $GRAFANA_DB_USER;
GRANT SELECT ON ALL TABLES IN SCHEMA public
    TO $GRAFANA_DB_USER;
-- і на таблиці, які буде створено пізніше
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON TABLES TO $GRAFANA_DB_USER;
EOSQL
