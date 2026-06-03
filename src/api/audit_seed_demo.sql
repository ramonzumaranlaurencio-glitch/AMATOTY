-- Datos demo para probar el drawer con tenant 20601234567 y cuenta 12.1.
-- Requiere ejecutar primero src/api/audit_schema.sql y src/api/audit_rls_policy.sql.

BEGIN;

DELETE FROM journal_items WHERE tenant_id = '20601234567';
DELETE FROM xml_documents WHERE tenant_id = '20601234567';
DELETE FROM taxpayer_validations WHERE tenant_id = '20601234567';
DELETE FROM accounts WHERE tenant_id = '20601234567';

INSERT INTO accounts (tenant_id, code, name) VALUES
('20601234567', '12.1', 'Cuentas por cobrar comerciales'),
('20601234567', '40.1', 'Tributos por pagar IGV'),
('20601234567', '42.1', 'Cuentas por pagar comerciales'),
('20601234567', '69.1', 'Costo de ventas'),
('20601234567', '70.1', 'Ventas gravadas');

INSERT INTO taxpayer_validations (tenant_id, ruc, legal_name, status) VALUES
('20601234567', '20123456789', 'ALFA RETAIL S.A.C.', 'HABIDO'),
('20601234567', '20987654321', 'BETA INDUSTRIAL S.A.', 'HABIDO'),
('20601234567', '20444555666', 'GAMMA SERVICIOS E.I.R.L.', 'NO HABIDO');

WITH xml_rows AS (
    INSERT INTO xml_documents (tenant_id, issuer_name, receiver_name, raw_xml, parsed_payload)
    VALUES
    (
        '20601234567',
        'CONTA_PRO ENTERPRISE S.A.C.',
        'ALFA RETAIL S.A.C.',
        '<Invoice><ID>F001-000542</ID><Supplier>CONTA_PRO ENTERPRISE S.A.C.</Supplier><Customer>ALFA RETAIL S.A.C.</Customer></Invoice>',
        '{
          "emisor": {"ruc": "20601234567", "razon_social": "CONTA_PRO ENTERPRISE S.A.C."},
          "receptor": {"ruc": "20123456789", "razon_social": "ALFA RETAIL S.A.C."},
          "items": [
            {"codigo": "SERV-AUD-001", "descripcion": "Servicio de auditoria mensual", "cantidad": 1, "precio_unitario": 52000.00, "total": 52000.00}
          ]
        }'::jsonb
    ),
    (
        '20601234567',
        'CONTA_PRO ENTERPRISE S.A.C.',
        'BETA INDUSTRIAL S.A.',
        '<Invoice><ID>F001-000543</ID><Supplier>CONTA_PRO ENTERPRISE S.A.C.</Supplier><Customer>BETA INDUSTRIAL S.A.</Customer></Invoice>',
        '{
          "emisor": {"ruc": "20601234567", "razon_social": "CONTA_PRO ENTERPRISE S.A.C."},
          "receptor": {"ruc": "20987654321", "razon_social": "BETA INDUSTRIAL S.A."},
          "items": [
            {"codigo": "LIC-ERP-010", "descripcion": "Licencia ERP anual", "cantidad": 1, "precio_unitario": 28750.40, "total": 28750.40}
          ]
        }'::jsonb
    ),
    (
        '20601234567',
        'CONTA_PRO ENTERPRISE S.A.C.',
        'GAMMA SERVICIOS E.I.R.L.',
        '<Invoice><ID>F001-000544</ID><Supplier>CONTA_PRO ENTERPRISE S.A.C.</Supplier><Customer>GAMMA SERVICIOS E.I.R.L.</Customer></Invoice>',
        '{
          "emisor": {"ruc": "20601234567", "razon_social": "CONTA_PRO ENTERPRISE S.A.C."},
          "receptor": {"ruc": "20444555666", "razon_social": "GAMMA SERVICIOS E.I.R.L."},
          "items": [
            {"codigo": "SOP-ERP-020", "descripcion": "Soporte contable especializado", "cantidad": 1, "precio_unitario": 18500.00, "total": 18500.00}
          ]
        }'::jsonb
    )
    RETURNING id, receiver_name
),
hashes AS (
    SELECT
        encode(digest('seed-12.1-1', 'sha256'), 'hex') AS h1,
        encode(digest('seed-12.1-2', 'sha256'), 'hex') AS h2,
        encode(digest('seed-12.1-3', 'sha256'), 'hex') AS h3
),
numbered_xml AS (
    SELECT id, receiver_name, row_number() OVER (ORDER BY receiver_name) AS rn
    FROM xml_rows
)
INSERT INTO journal_items (
    tenant_id,
    date,
    account_code,
    account_name,
    voucher_number,
    description,
    debit,
    credit,
    taxpayer_ruc,
    counterparty_name,
    xml_document_id,
    hash_payload,
    previous_hash,
    row_hash
)
SELECT
    '20601234567',
    data.date,
    '12.1',
    'Cuentas por cobrar comerciales',
    data.voucher,
    data.description,
    data.debit,
    data.credit,
    data.ruc,
    data.counterparty,
    numbered_xml.id,
    data.hash_payload,
    data.previous_hash,
    data.row_hash
FROM hashes
CROSS JOIN LATERAL (
    VALUES
    (1, DATE '2026-05-03', 'F001-000542', 'Venta corporativa con importe superior al promedio', 52000.00::numeric, 0::numeric, '20123456789', 'ALFA RETAIL S.A.C.', 'seed-12.1-1', ''::text, hashes.h1),
    (2, DATE '2026-05-08', 'F001-000543', 'Licencia ERP anual facturada', 28750.40::numeric, 0::numeric, '20987654321', 'BETA INDUSTRIAL S.A.', 'seed-12.1-2', hashes.h1, hashes.h2),
    (3, DATE '2026-05-12', 'F001-000544', 'Servicio con contribuyente observado', 18500.00::numeric, 0::numeric, '20444555666', 'GAMMA SERVICIOS E.I.R.L.', 'seed-12.1-3', hashes.h2, hashes.h3)
) AS data(rn, date, voucher, description, debit, credit, ruc, counterparty, hash_payload, previous_hash, row_hash)
JOIN numbered_xml ON numbered_xml.rn = data.rn;

COMMIT;
