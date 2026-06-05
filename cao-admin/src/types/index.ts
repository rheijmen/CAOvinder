// Core Types for CAO Admin Interface

// === Organizations & Multi-tenancy ===
export interface Organization {
  id: string;
  name: string;
  plan: 'starter' | 'professional' | 'enterprise';
  settings: {
    branding?: {
      logo?: string;
      primaryColor?: string;
    };
    llmPreferences?: {
      primaryLLM: 'gemini' | 'mistral' | 'claude';
      costLimit?: number;
    };
  };
  createdAt: Date;
  updatedAt: Date;
}

export interface User {
  id: string;
  email: string;
  name: string;
  role: 'superadmin' | 'org_admin' | 'reviewer' | 'viewer';
  organizationId: string;
  permissions: Permission[];
}

export interface Permission {
  resource: string;
  actions: ('create' | 'read' | 'update' | 'delete')[];
}

// === CAO Document Management ===
export interface CAODocument {
  id: string;
  organizationId: string;
  name: string;
  sector?: string;
  company?: string;
  version: number;
  status: ProcessingStatus;
  effectiveDate?: Date;
  expiryDate?: Date;

  // File info
  originalFileName: string;
  fileSize: number;
  uploadedAt: Date;
  uploadedBy: string;

  // Processing data
  ocrContent?: string;
  ocrCompletedAt?: Date;
  setuData?: SETUDocument;
  statutoryRefs?: StatutoryReferences;
  judgeReport?: JudgeReport;
  processedAt?: Date;

  // Compliance
  complianceStatus: ComplianceStatus;
  validationErrors?: ValidationError[];
  discrepancies?: Discrepancy[];

  metadata: {
    pageCount?: number;
    language?: string;
    extractedDates?: string[];
    confidence?: number;
  };
}

export type ProcessingStatus =
  | 'uploaded'
  | 'queued'
  | 'ocr_processing'
  | 'ocr_complete'
  | 'extracting'
  | 'reviewing'
  | 'judging'
  | 'complete'
  | 'failed'
  | 'requires_review';

export type ComplianceStatus =
  | 'compliant'
  | 'partial'
  | 'non_compliant'
  | 'version_mismatch'
  | 'unknown';

// === SETU v2.0 Types ===
export interface SETUDocument {
  documentId: string;
  caoName: string;

  // Core SETU fields (simplified for UI)
  loongebouw?: {
    functiegroepen: FunctieGroep[];
    schalen: SalaryScale[];
  };
  toeslagen?: Toeslag[];
  verlof?: VerlofRegeling[];
  pensioenen?: PensioenRegeling[];

  // Metadata
  extractedAt: Date;
  extractedBy: 'gemini' | 'mistral' | 'claude';
  confidence: number;
}

export interface FunctieGroep {
  code: string;
  naam: string;
  minimumLoon: number;
  maximumLoon: number;
}

export interface SalaryScale {
  schaal: string;
  treden: {
    trede: number;
    bedrag: number;
  }[];
}

export interface Toeslag {
  type: string;
  percentage?: number;
  bedrag?: number;
  voorwaarden?: string;
}

export interface VerlofRegeling {
  type: string;
  dagen: number;
  voorwaarden?: string;
}

export interface PensioenRegeling {
  fonds: string;
  werkgeversBijdrage: number;
  werknemersBijdrage: number;
}

// === Statutory References ===
export interface StatutoryReferences {
  documentId: string;
  period: string;

  minimumWage: {
    hourly: number;
    monthly: number;
    effectiveDate: Date;
  };

  socialInsurance: {
    ww: number;
    zvw: number;
    wao: number;
  };

  pensionParameters: {
    aowAge: number;
    maxPensionableSalary: number;
  };
}

// === Judge Report & Discrepancies ===
export interface JudgeReport {
  id: string;
  caoDocumentId: string;
  createdAt: Date;

  geminiOutput: SETUDocument;
  mistralReview: ReviewComment[];

  decisions: FieldDecision[];
  overallConfidence: number;
  requiresHumanReview: boolean;
}

export interface ReviewComment {
  field: string;
  issue: string;
  severity: 'low' | 'medium' | 'high';
  suggestion?: string;
}

export interface FieldDecision {
  fieldPath: string;
  geminiValue: any;
  mistralValue: any;
  finalValue: any;
  reasoning: string;
  confidence: number;
  source: 'gemini' | 'mistral' | 'merged';
}

export interface Discrepancy {
  id: string;
  caoDocumentId: string;
  fieldPath: string;
  type: 'missing' | 'mismatch' | 'invalid' | 'ambiguous';

  currentValue: any;
  suggestedValue?: any;
  validationRule?: string;

  status: 'open' | 'reviewing' | 'resolved' | 'ignored';
  priority: 'low' | 'medium' | 'high';

  resolution?: {
    finalValue: any;
    resolvedBy: string;
    resolvedAt: Date;
    reasoning: string;
  };
}

export interface ValidationError {
  field: string;
  rule: string;
  message: string;
  severity: 'warning' | 'error';
}

// === Processing Pipeline ===
export interface ProcessingJob {
  id: string;
  organizationId: string;
  caoDocumentId: string;

  pipeline: PipelineConfig;
  status: 'queued' | 'running' | 'paused' | 'completed' | 'failed';
  progress: number; // 0-100

  stages: StageProgress[];

  cost: {
    estimated: number;
    actual?: number;
    breakdown: {
      ocr: number;
      llm: number;
      storage: number;
    };
  };

  startedAt?: Date;
  completedAt?: Date;
  error?: string;
}

export interface PipelineConfig {
  name: string;
  stages: PipelineStage[];
  retryPolicy: {
    maxAttempts: number;
    backoffMs: number;
  };
  costLimit?: number;
}

export interface PipelineStage {
  id: string;
  type: 'ocr' | 'extract' | 'review' | 'judge' | 'validate';
  provider: 'mistral' | 'gemini' | 'claude' | 'custom';
  config: Record<string, any>;
  enabled: boolean;
  order: number;
}

export interface StageProgress {
  stageId: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  startedAt?: Date;
  completedAt?: Date;
  tokensUsed?: number;
  cost?: number;
  output?: any;
  error?: string;
}

// === Analytics & Metrics ===
export interface ProcessingMetrics {
  organizationId: string;
  period: 'day' | 'week' | 'month';

  documentsProcessed: number;
  averageProcessingTime: number; // minutes
  successRate: number; // percentage

  costBreakdown: {
    total: number;
    ocr: number;
    llm: number;
    storage: number;
  };

  complianceStats: {
    compliant: number;
    partial: number;
    nonCompliant: number;
  };

  errorRate: number;
  humanInterventions: number;
}

// === UI State Types ===
export interface FilterState {
  search?: string;
  sector?: string[];
  status?: ProcessingStatus[];
  complianceStatus?: ComplianceStatus[];
  dateRange?: {
    from: Date;
    to: Date;
  };
  hasDiscrepancies?: boolean;
}

export interface SortState {
  field: string;
  direction: 'asc' | 'desc';
}

export interface PaginationState {
  page: number;
  pageSize: number;
  total: number;
}

// === API Response Types ===
export interface ApiResponse<T> {
  data: T;
  meta?: {
    pagination?: PaginationState;
    timestamp: Date;
  };
  error?: {
    code: string;
    message: string;
    details?: any;
  };
}

export interface BatchOperationResult {
  succeeded: string[];
  failed: Array<{
    id: string;
    reason: string;
  }>;
}