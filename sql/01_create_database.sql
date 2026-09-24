-- OpenBI — 01 — ensure schemas exist (runs every ETL pass, idempotent)

CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS warehouse;
