# -*- coding: utf-8 -*-
# ============================================================
# ACKO Insurance - Create All Database Tables
# Run this script directly:  python create_tables.py
# ============================================================

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

def get_database_url() -> str:
    """
    Resolve DATABASE_URL from environment, falling back to individual
    POSTGRES_* vars, then finally a local default.
    """
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "root")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    name = os.getenv("POSTGRES_DB", "acko_insurance")
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS app_users (
    id            SERIAL PRIMARY KEY,
    email         VARCHAR(255) UNIQUE NOT NULL,
    full_name     VARCHAR(255),
    phone         VARCHAR(20),
    role          VARCHAR(50) DEFAULT 'customer',
    created_at    TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS quotation_submissions (
    id                    SERIAL PRIMARY KEY,
    user_id               INTEGER REFERENCES app_users(id) ON DELETE SET NULL,
    vehicle_type          VARCHAR(100),
    vehicle_make          VARCHAR(100),
    vehicle_model         VARCHAR(100),
    manufacturing_year    INTEGER,
    engine_cc             INTEGER,
    idv                   NUMERIC(12, 2),
    policy_type           VARCHAR(100),
    ncb_percent           NUMERIC(5, 2),
    num_addons            INTEGER DEFAULT 0,
    claim_history_count   INTEGER DEFAULT 0,
    state                 VARCHAR(100),
    city_tier             VARCHAR(20),
    customer_age          INTEGER,
    predicted_premium     NUMERIC(12, 2),
    action                VARCHAR(20) DEFAULT 'pending'
                              CHECK (action IN ('pending', 'bought', 'declined')),
    created_at            TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS claim_submissions (
    id                      SERIAL PRIMARY KEY,
    user_id                 INTEGER REFERENCES app_users(id) ON DELETE SET NULL,
    vehicle_type            VARCHAR(100),
    vehicle_make            VARCHAR(100),
    vehicle_model           VARCHAR(100),
    manufacturing_year      INTEGER,
    incident_type           VARCHAR(100),
    damage_type             VARCHAR(100),
    damage_severity_score   NUMERIC(5, 2),
    idv                     NUMERIC(12, 2),
    policy_type             VARCHAR(100),
    state                   VARCHAR(100),
    predicted_approval      BOOLEAN,
    predicted_amount        NUMERIC(12, 2),
    fraud_risk              VARCHAR(20) DEFAULT 'low'
                                CHECK (fraud_risk IN ('low', 'medium', 'high')),
    status                  VARCHAR(20) DEFAULT 'submitted'
                                CHECK (status IN ('submitted', 'approved', 'rejected')),
    created_at              TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS policy_purchases (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER REFERENCES app_users(id) ON DELETE SET NULL,
    quotation_id    INTEGER REFERENCES quotation_submissions(id) ON DELETE SET NULL,
    vehicle_type    VARCHAR(100),
    vehicle_make    VARCHAR(100),
    vehicle_model   VARCHAR(100),
    policy_type     VARCHAR(100),
    premium         NUMERIC(12, 2),
    idv             NUMERIC(12, 2),
    start_date      DATE,
    end_date        DATE,
    status          VARCHAR(20) DEFAULT 'active'
                        CHECK (status IN ('active', 'expired', 'cancelled')),
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chat_logs (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER REFERENCES app_users(id) ON DELETE SET NULL,
    session_id  VARCHAR(255),
    source      VARCHAR(20) DEFAULT 'customer'
                    CHECK (source IN ('customer', 'management')),
    intent      VARCHAR(255),
    user_msg    TEXT,
    bot_reply   TEXT,
    latency_ms  INTEGER,
    created_at  TIMESTAMP DEFAULT NOW()
);
"""

def create_all_tables(database_url: str | None = None) -> list[str]:
    """
    Create all required tables. Returns the table names present in the
    public schema after creation.
    """
    database_url = database_url or get_database_url()
    try:
        engine = create_engine(database_url, pool_pre_ping=True)

        # Create tables one by one to avoid multi-statement issues
        statements = [s.strip() for s in CREATE_TABLES_SQL.split(';') if s.strip()]

        with engine.begin() as conn:
            for stmt in statements:
                conn.execute(text(stmt))

        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema='public' ORDER BY table_name"
            )).fetchall()
            return [row[0] for row in result]

    except Exception as e:
        raise RuntimeError(str(e)) from e

def main():
    database_url = get_database_url()
    safe_url = database_url
    if "@" in safe_url and "://" in safe_url:
        # Hide password if present in URL: scheme://user:pass@host/...
        scheme, rest = safe_url.split("://", 1)
        if "@" in rest and ":" in rest.split("@", 1)[0]:
            user_part, tail = rest.split("@", 1)
            user = user_part.split(":", 1)[0]
            safe_url = f"{scheme}://{user}:***@{tail}"

    print(f"Connecting to: {safe_url}")
    tables = create_all_tables(database_url=database_url)
    print("[OK] All tables created successfully!\n")
    print("Tables now in database:")
    for t in tables:
        print(f"   >> {t}")

if __name__ == "__main__":
    main()
