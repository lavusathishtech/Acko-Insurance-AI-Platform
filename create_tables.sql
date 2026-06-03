-- ============================================================
-- ACKO Insurance Database - Table Creation Script
-- Database: acko_insurance
-- Run this in pgAdmin or psql to create all required tables
-- ============================================================

-- Create Database (run separately if needed)
-- CREATE DATABASE acko_insurance;

-- Connect to the database first:
-- \c acko_insurance

-- ============================================================
-- 1. app_users
-- ============================================================
CREATE TABLE IF NOT EXISTS app_users (
    id            SERIAL PRIMARY KEY,
    email         VARCHAR(255) UNIQUE NOT NULL,
    full_name     VARCHAR(255),
    phone         VARCHAR(20),
    role          VARCHAR(50) DEFAULT 'customer',  -- e.g. customer | management
    created_at    TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- 2. quotation_submissions
-- ============================================================
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

-- ============================================================
-- 3. claim_submissions
-- ============================================================
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

-- ============================================================
-- 4. policy_purchases
-- ============================================================
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

-- ============================================================
-- 5. chat_logs
-- ============================================================
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

-- ============================================================
-- Verify all tables created
-- ============================================================
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
