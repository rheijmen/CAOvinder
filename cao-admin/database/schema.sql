-- CAO Intelligence Platform - PostgreSQL Schema
-- Multi-tenant SaaS architecture with SETU v2.0 compliance
-- Version: 1.0.0

-- =====================================================
-- EXTENSIONS
-- =====================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm"; -- For fuzzy text search
CREATE EXTENSION IF NOT EXISTS "btree_gin"; -- For composite indexes

-- =====================================================
-- ENUMS
-- =====================================================
CREATE TYPE user_role AS ENUM ('superadmin', 'org_admin', 'reviewer', 'viewer');
CREATE TYPE subscription_plan AS ENUM ('starter', 'professional', 'enterprise');
CREATE TYPE processing_status AS ENUM (
    'uploaded', 'queued', 'ocr_processing', 'ocr_complete',
    'extracting', 'reviewing', 'judging', 'complete', 'failed', 'requires_review'
);
CREATE TYPE compliance_status AS ENUM (
    'compliant', 'partial', 'non_compliant', 'version_mismatch', 'unknown'
);
CREATE TYPE discrepancy_type AS ENUM ('missing', 'mismatch', 'invalid', 'ambiguous');
CREATE TYPE discrepancy_status AS ENUM ('open', 'reviewing', 'resolved', 'ignored');
CREATE TYPE priority_level AS ENUM ('low', 'medium', 'high');
CREATE TYPE job_status AS ENUM ('queued', 'running', 'paused', 'completed', 'failed');
CREATE TYPE llm_provider AS ENUM ('mistral', 'gemini', 'claude', 'custom');

-- =====================================================
-- ORGANIZATIONS (TENANTS)
-- =====================================================
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL, -- URL-friendly name
    plan subscription_plan NOT NULL DEFAULT 'starter',

    -- Settings
    settings JSONB DEFAULT '{}'::jsonb,
    branding JSONB DEFAULT '{}'::jsonb, -- logo, colors, etc.
    llm_preferences JSONB DEFAULT '{
        "primary_llm": "gemini",
        "cost_limit": null
    }'::jsonb,

    -- Limits based on plan
    max_users INTEGER DEFAULT 5,
    max_documents_per_month INTEGER DEFAULT 100,
    max_api_calls_per_day INTEGER DEFAULT 1000,
    storage_limit_gb INTEGER DEFAULT 10,

    -- Billing
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    trial_ends_at TIMESTAMP,

    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP -- Soft delete
);

CREATE INDEX idx_organizations_slug ON organizations(slug);
CREATE INDEX idx_organizations_plan ON organizations(plan);

-- =====================================================
-- USERS & AUTHENTICATION
-- =====================================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,

    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    role user_role NOT NULL DEFAULT 'viewer',

    -- Auth
    password_hash VARCHAR(255), -- NULL for SSO users
    email_verified BOOLEAN DEFAULT FALSE,
    two_factor_secret VARCHAR(255),
    two_factor_enabled BOOLEAN DEFAULT FALSE,

    -- Preferences
    preferences JSONB DEFAULT '{}'::jsonb,
    notification_settings JSONB DEFAULT '{
        "email": true,
        "in_app": true,
        "processing_complete": true,
        "review_required": true
    }'::jsonb,

    -- Metadata
    last_login_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);

CREATE INDEX idx_users_organization_id ON users(organization_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);

-- =====================================================
-- CAO DOCUMENTS
-- =====================================================
CREATE TABLE cao_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,

    -- Basic info
    name VARCHAR(255) NOT NULL,
    sector VARCHAR(255),
    company VARCHAR(255),
    version INTEGER NOT NULL DEFAULT 1,
    status processing_status NOT NULL DEFAULT 'uploaded',

    -- Dates
    effective_date DATE,
    expiry_date DATE,

    -- File info
    original_file_name VARCHAR(255) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    file_hash VARCHAR(64), -- SHA256
    storage_path TEXT, -- S3 or local path

    -- Processing data
    ocr_content TEXT,
    ocr_tables JSONB, -- Extracted tables from OCR
    ocr_completed_at TIMESTAMP,

    -- SETU extraction
    setu_data JSONB, -- Full SETU v2.0 document
    setu_version VARCHAR(20), -- SETU schema version used

    -- Statutory references
    statutory_refs JSONB, -- Government mandated values

    -- Judge report from 3-LLM pipeline
    judge_report JSONB, -- Decisions and confidence scores

    -- Processing metadata
    processed_at TIMESTAMP,
    processing_time_seconds INTEGER,
    processing_cost_eur DECIMAL(10,4),
    tokens_used JSONB, -- {"ocr": 1000, "gemini": 5000, "mistral": 3000}

    -- Compliance
    compliance_status compliance_status DEFAULT 'unknown',
    compliance_score DECIMAL(5,2), -- 0-100
    validation_errors JSONB DEFAULT '[]'::jsonb,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb, -- page_count, language, etc.
    tags TEXT[], -- User-defined tags

    -- User tracking
    uploaded_by UUID REFERENCES users(id),
    last_modified_by UUID REFERENCES users(id),

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_cao_documents_organization_id ON cao_documents(organization_id);
CREATE INDEX idx_cao_documents_status ON cao_documents(status);
CREATE INDEX idx_cao_documents_compliance_status ON cao_documents(compliance_status);
CREATE INDEX idx_cao_documents_sector ON cao_documents(sector);
CREATE INDEX idx_cao_documents_company ON cao_documents(company);
CREATE INDEX idx_cao_documents_effective_date ON cao_documents(effective_date);
CREATE INDEX idx_cao_documents_tags ON cao_documents USING GIN(tags);
CREATE INDEX idx_cao_documents_metadata ON cao_documents USING GIN(metadata);

-- Full-text search index
CREATE INDEX idx_cao_documents_search ON cao_documents
USING GIN(to_tsvector('dutch', name || ' ' || COALESCE(sector, '') || ' ' || COALESCE(company, '')));

-- =====================================================
-- DISCREPANCIES & RESOLUTIONS
-- =====================================================
CREATE TABLE discrepancies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cao_document_id UUID REFERENCES cao_documents(id) ON DELETE CASCADE,

    field_path TEXT NOT NULL, -- e.g., "loongebouw.schalen[0].bedrag"
    field_name TEXT NOT NULL, -- Human-readable name
    type discrepancy_type NOT NULL,

    -- Values
    current_value JSONB,
    expected_value JSONB,
    suggested_value JSONB,

    -- Validation
    validation_rule TEXT, -- Which SETU rule was violated
    error_message TEXT,

    -- Status
    status discrepancy_status NOT NULL DEFAULT 'open',
    priority priority_level NOT NULL DEFAULT 'medium',

    -- Resolution
    resolved_value JSONB,
    resolved_by UUID REFERENCES users(id),
    resolved_at TIMESTAMP,
    resolution_reasoning TEXT,

    -- AI suggestions
    ai_confidence DECIMAL(5,2), -- 0-100
    ai_reasoning TEXT,

    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_discrepancies_cao_document_id ON discrepancies(cao_document_id);
CREATE INDEX idx_discrepancies_status ON discrepancies(status);
CREATE INDEX idx_discrepancies_priority ON discrepancies(priority);
CREATE INDEX idx_discrepancies_field_path ON discrepancies(field_path);

-- =====================================================
-- PROCESSING JOBS
-- =====================================================
CREATE TABLE processing_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    cao_document_id UUID REFERENCES cao_documents(id) ON DELETE CASCADE,

    -- Pipeline configuration
    pipeline_config JSONB NOT NULL, -- Stages, LLMs, settings

    -- Status
    status job_status NOT NULL DEFAULT 'queued',
    progress INTEGER DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    current_stage VARCHAR(50),

    -- Cost tracking
    estimated_cost_eur DECIMAL(10,4),
    actual_cost_eur DECIMAL(10,4),
    cost_breakdown JSONB, -- {"ocr": 0.50, "llm": 2.30}

    -- Performance
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    error_details JSONB,
    retry_count INTEGER DEFAULT 0,

    -- Stage progress tracking
    stages_progress JSONB DEFAULT '[]'::jsonb,

    -- User tracking
    initiated_by UUID REFERENCES users(id),

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_processing_jobs_organization_id ON processing_jobs(organization_id);
CREATE INDEX idx_processing_jobs_cao_document_id ON processing_jobs(cao_document_id);
CREATE INDEX idx_processing_jobs_status ON processing_jobs(status);
CREATE INDEX idx_processing_jobs_created_at ON processing_jobs(created_at DESC);

-- =====================================================
-- API KEYS & ACCESS TOKENS
-- =====================================================
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,

    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(255) NOT NULL, -- SHA256 of the actual key
    key_prefix VARCHAR(10) NOT NULL, -- First 10 chars for identification

    -- Permissions
    permissions JSONB DEFAULT '[]'::jsonb, -- ["cao:read", "cao:write", etc.]

    -- Rate limiting
    rate_limit_per_minute INTEGER DEFAULT 60,
    rate_limit_per_day INTEGER DEFAULT 10000,

    -- Usage tracking
    last_used_at TIMESTAMP,
    usage_count BIGINT DEFAULT 0,

    -- Lifecycle
    expires_at TIMESTAMP,
    revoked_at TIMESTAMP,
    revoked_by UUID REFERENCES users(id),

    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_api_keys_organization_id ON api_keys(organization_id);
CREATE INDEX idx_api_keys_key_prefix ON api_keys(key_prefix);

-- =====================================================
-- AUDIT LOG
-- =====================================================
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,

    action VARCHAR(100) NOT NULL, -- e.g., "cao.upload", "discrepancy.resolve"
    resource_type VARCHAR(50), -- "cao_document", "user", etc.
    resource_id UUID,

    -- Change details
    old_values JSONB,
    new_values JSONB,

    -- Request context
    ip_address INET,
    user_agent TEXT,
    api_key_id UUID REFERENCES api_keys(id) ON DELETE SET NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_logs_organization_id ON audit_logs(organization_id);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);

-- =====================================================
-- ANALYTICS & METRICS
-- =====================================================
CREATE TABLE processing_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,

    -- Time period
    date DATE NOT NULL,

    -- Counters
    documents_processed INTEGER DEFAULT 0,
    documents_failed INTEGER DEFAULT 0,

    -- Performance
    avg_processing_time_seconds DECIMAL(10,2),
    median_processing_time_seconds DECIMAL(10,2),

    -- Cost
    total_cost_eur DECIMAL(10,4) DEFAULT 0,
    ocr_cost_eur DECIMAL(10,4) DEFAULT 0,
    llm_cost_eur DECIMAL(10,4) DEFAULT 0,
    storage_cost_eur DECIMAL(10,4) DEFAULT 0,

    -- Quality
    avg_confidence_score DECIMAL(5,2),
    compliance_rate DECIMAL(5,2), -- Percentage compliant

    -- Usage
    api_calls_count INTEGER DEFAULT 0,
    storage_used_gb DECIMAL(10,4),

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(organization_id, date)
);

CREATE INDEX idx_processing_metrics_organization_date ON processing_metrics(organization_id, date DESC);

-- =====================================================
-- NOTIFICATIONS
-- =====================================================
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,

    type VARCHAR(50) NOT NULL, -- "processing_complete", "review_required", etc.
    title VARCHAR(255) NOT NULL,
    message TEXT,

    -- Related resource
    resource_type VARCHAR(50),
    resource_id UUID,

    -- Status
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP,

    -- Email notification
    email_sent BOOLEAN DEFAULT FALSE,
    email_sent_at TIMESTAMP,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_notifications_user_id_unread ON notifications(user_id, is_read) WHERE is_read = FALSE;
CREATE INDEX idx_notifications_created_at ON notifications(created_at DESC);

-- =====================================================
-- FUNCTIONS & TRIGGERS
-- =====================================================

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update trigger to all relevant tables
CREATE TRIGGER update_organizations_updated_at BEFORE UPDATE ON organizations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_cao_documents_updated_at BEFORE UPDATE ON cao_documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_discrepancies_updated_at BEFORE UPDATE ON discrepancies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_processing_jobs_updated_at BEFORE UPDATE ON processing_jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- ROW LEVEL SECURITY (RLS)
-- =====================================================

-- Enable RLS on all tables
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE cao_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE discrepancies ENABLE ROW LEVEL SECURITY;
ALTER TABLE processing_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE processing_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

-- Example RLS policies (to be customized based on authentication method)
-- These assume a session variable 'app.current_org_id' is set

CREATE POLICY org_isolation_cao_documents ON cao_documents
    FOR ALL
    USING (organization_id = current_setting('app.current_org_id')::UUID);

CREATE POLICY org_isolation_users ON users
    FOR ALL
    USING (organization_id = current_setting('app.current_org_id')::UUID);

-- =====================================================
-- INITIAL DATA
-- =====================================================

-- Insert default superadmin organization (for platform management)
INSERT INTO organizations (id, name, slug, plan, max_users, max_documents_per_month, max_api_calls_per_day, storage_limit_gb)
VALUES (
    '00000000-0000-0000-0000-000000000000',
    'Platform Administration',
    'admin',
    'enterprise',
    1000,
    999999,
    999999,
    10000
);

-- =====================================================
-- COMMENTS
-- =====================================================

COMMENT ON TABLE organizations IS 'Multi-tenant organizations using the platform';
COMMENT ON TABLE cao_documents IS 'Main table for CAO document storage and processing';
COMMENT ON TABLE discrepancies IS 'Tracks all discrepancies found during SETU compliance validation';
COMMENT ON TABLE processing_jobs IS 'Job queue for async document processing pipeline';
COMMENT ON COLUMN cao_documents.setu_data IS 'Complete SETU v2.0 InquiryPayEquity document in JSON format';
COMMENT ON COLUMN cao_documents.judge_report IS 'Output from the 3-LLM judge containing field decisions and confidence scores';