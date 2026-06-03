-- CONTA_PRO Enterprise - Auditoria Forense Interactiva
-- Esquema minimo PostgreSQL para probar y operar el modulo.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS accounts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id text NOT NULL,
    code text NOT NULL,
    name text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, code)
);

CREATE TABLE IF NOT EXISTS xml_documents (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id text NOT NULL,
    issuer_name text,
    receiver_name text,
    raw_xml text,
    parsed_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS taxpayer_validations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id text NOT NULL,
    ruc text NOT NULL,
    legal_name text,
    status text NOT NULL DEFAULT 'PENDIENTE',
    validated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, ruc)
);

CREATE TABLE IF NOT EXISTS journal_items (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id text NOT NULL,
    date date NOT NULL,
    account_code text NOT NULL,
    account_name text,
    voucher_number text NOT NULL,
    description text,
    debit numeric(18, 2) NOT NULL DEFAULT 0,
    credit numeric(18, 2) NOT NULL DEFAULT 0,
    taxpayer_ruc text,
    counterparty_name text,
    xml_document_id uuid REFERENCES xml_documents(id),
    hash_payload text,
    previous_hash text NOT NULL DEFAULT '',
    row_hash text NOT NULL DEFAULT '',
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_journal_items_tenant_account_date
ON journal_items (tenant_id, account_code, date, voucher_number);

CREATE INDEX IF NOT EXISTS idx_journal_items_tenant_ruc
ON journal_items (tenant_id, taxpayer_ruc);

CREATE INDEX IF NOT EXISTS idx_xml_documents_tenant
ON xml_documents (tenant_id);

CREATE INDEX IF NOT EXISTS idx_taxpayer_validations_tenant_ruc
ON taxpayer_validations (tenant_id, ruc);
