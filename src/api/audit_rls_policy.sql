-- Auditoria Forense Interactiva - Row Level Security
-- Ejecutar una vez por ambiente PostgreSQL con un rol owner/admin.

ALTER TABLE journal_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE journal_items FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS journal_items_tenant_isolation ON journal_items;
CREATE POLICY journal_items_tenant_isolation
ON journal_items
USING (tenant_id::text = current_setting('app.tenant_id', true))
WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true));

ALTER TABLE xml_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE xml_documents FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS xml_documents_tenant_isolation ON xml_documents;
CREATE POLICY xml_documents_tenant_isolation
ON xml_documents
USING (tenant_id::text = current_setting('app.tenant_id', true))
WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true));

ALTER TABLE taxpayer_validations ENABLE ROW LEVEL SECURITY;
ALTER TABLE taxpayer_validations FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS taxpayer_validations_tenant_isolation ON taxpayer_validations;
CREATE POLICY taxpayer_validations_tenant_isolation
ON taxpayer_validations
USING (tenant_id::text = current_setting('app.tenant_id', true))
WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true));
