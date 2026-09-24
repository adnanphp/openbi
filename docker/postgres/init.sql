-- OpenBI — Postgres bootstrap
-- Runs once on first container creation.
-- Database `openbi` is created automatically via POSTGRES_DB env var.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS warehouse;

GRANT ALL ON SCHEMA staging   TO CURRENT_USER;
GRANT ALL ON SCHEMA warehouse TO CURRENT_USER;

-- Sanity check visible in docker logs
DO $$
BEGIN
    RAISE NOTICE 'OpenBI init: schemas staging + warehouse created in %', current_database();
END $$;
