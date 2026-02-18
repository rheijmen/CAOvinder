/**
 * Modern API Client for CAO Intelligence Platform
 *
 * This is the SINGLE source of truth for all API calls from frontend to backend.
 * The frontend NEVER directly accesses the database or runs business logic.
 */

import { CAODocument, ProcessingJob, Discrepancy, Organization, User } from '@/types';

// API Configuration from environment
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_VERSION = 'v1';

/**
 * Base API client with authentication and error handling
 */
class APIClient {
  private baseURL: string;
  private token: string | null = null;

  constructor() {
    this.baseURL = `${API_BASE_URL}/api/${API_VERSION}`;
  }

  /**
   * Set authentication token (JWT)
   */
  setAuthToken(token: string) {
    this.token = token;
    // Store in secure cookie or localStorage
    if (typeof window !== 'undefined') {
      localStorage.setItem('auth_token', token);
    }
  }

  /**
   * Generic fetch wrapper with auth headers
   */
  private async fetch<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;

    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    // Add auth token if available
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new APIError(
        error.message || `API Error: ${response.statusText}`,
        response.status,
        error
      );
    }

    return response.json();
  }

  // ==========================================
  // CAO Document Management APIs
  // ==========================================

  /**
   * Get all CAO documents with filtering
   */
  async getCaoDocuments(params?: {
    search?: string;
    sector?: string;
    status?: string;
    page?: number;
    limit?: number;
  }): Promise<{ data: CAODocument[]; total: number }> {
    const queryParams = new URLSearchParams(params as any);
    return this.fetch(`/caos?${queryParams}`);
  }

  /**
   * Get single CAO document by ID
   */
  async getCaoDocument(id: string): Promise<CAODocument> {
    return this.fetch(`/caos/${id}`);
  }

  /**
   * Upload new CAO document
   */
  async uploadCaoDocument(file: File, metadata?: Partial<CAODocument>): Promise<CAODocument> {
    const formData = new FormData();
    formData.append('file', file);
    if (metadata) {
      formData.append('metadata', JSON.stringify(metadata));
    }

    return this.fetch('/caos/upload', {
      method: 'POST',
      body: formData,
      headers: {}, // Let browser set content-type for FormData
    });
  }

  /**
   * Start processing pipeline for CAO
   */
  async startProcessing(caoId: string, pipelineConfig?: any): Promise<ProcessingJob> {
    return this.fetch(`/caos/${caoId}/process`, {
      method: 'POST',
      body: JSON.stringify({ pipeline_config: pipelineConfig }),
    });
  }

  /**
   * Reprocess CAO document
   */
  async reprocessCao(caoId: string): Promise<ProcessingJob> {
    return this.fetch(`/caos/${caoId}/reprocess`, {
      method: 'POST',
    });
  }

  // ==========================================
  // SETU Compliance APIs
  // ==========================================

  /**
   * Get compliance discrepancies for a CAO
   */
  async getDiscrepancies(caoId: string): Promise<Discrepancy[]> {
    return this.fetch(`/caos/${caoId}/discrepancies`);
  }

  /**
   * Resolve a discrepancy
   */
  async resolveDiscrepancy(
    discrepancyId: string,
    resolution: {
      finalValue: any;
      reasoning: string;
    }
  ): Promise<Discrepancy> {
    return this.fetch(`/discrepancies/${discrepancyId}/resolve`, {
      method: 'POST',
      body: JSON.stringify(resolution),
    });
  }

  /**
   * Get SETU validation report
   */
  async getSetuReport(caoId: string): Promise<any> {
    return this.fetch(`/caos/${caoId}/setu-report`);
  }

  /**
   * Get judge report from 3-LLM pipeline
   */
  async getJudgeReport(caoId: string): Promise<any> {
    return this.fetch(`/caos/${caoId}/judge-report`);
  }

  // ==========================================
  // Processing Pipeline APIs
  // ==========================================

  /**
   * Get all processing jobs
   */
  async getProcessingJobs(params?: {
    status?: 'queued' | 'running' | 'completed' | 'failed';
    limit?: number;
  }): Promise<ProcessingJob[]> {
    const queryParams = new URLSearchParams(params as any);
    return this.fetch(`/jobs?${queryParams}`);
  }

  /**
   * Get single processing job
   */
  async getProcessingJob(jobId: string): Promise<ProcessingJob> {
    return this.fetch(`/jobs/${jobId}`);
  }

  /**
   * Pause a running job
   */
  async pauseJob(jobId: string): Promise<ProcessingJob> {
    return this.fetch(`/jobs/${jobId}/pause`, {
      method: 'POST',
    });
  }

  /**
   * Resume a paused job
   */
  async resumeJob(jobId: string): Promise<ProcessingJob> {
    return this.fetch(`/jobs/${jobId}/resume`, {
      method: 'POST',
    });
  }

  /**
   * Cancel a job
   */
  async cancelJob(jobId: string): Promise<void> {
    return this.fetch(`/jobs/${jobId}/cancel`, {
      method: 'DELETE',
    });
  }

  /**
   * Get pipeline configuration templates
   */
  async getPipelineTemplates(): Promise<any[]> {
    return this.fetch('/pipelines/templates');
  }

  // ==========================================
  // Analytics & Metrics APIs
  // ==========================================

  /**
   * Get processing metrics
   */
  async getMetrics(params?: {
    period?: 'day' | 'week' | 'month';
    start_date?: string;
    end_date?: string;
  }): Promise<any> {
    const queryParams = new URLSearchParams(params as any);
    return this.fetch(`/analytics/metrics?${queryParams}`);
  }

  /**
   * Get cost breakdown
   */
  async getCostAnalytics(organizationId?: string): Promise<any> {
    return this.fetch(`/analytics/costs${organizationId ? `?org=${organizationId}` : ''}`);
  }

  /**
   * Get compliance statistics
   */
  async getComplianceStats(): Promise<any> {
    return this.fetch('/analytics/compliance');
  }

  // ==========================================
  // Organization & User Management APIs
  // ==========================================

  /**
   * Get current user's organization
   */
  async getCurrentOrganization(): Promise<Organization> {
    return this.fetch('/organization');
  }

  /**
   * Update organization settings
   */
  async updateOrganization(orgId: string, updates: Partial<Organization>): Promise<Organization> {
    return this.fetch(`/organizations/${orgId}`, {
      method: 'PATCH',
      body: JSON.stringify(updates),
    });
  }

  /**
   * Get current user profile
   */
  async getCurrentUser(): Promise<User> {
    return this.fetch('/auth/me');
  }

  /**
   * Login user
   */
  async login(email: string, password: string): Promise<{ token: string; user: User }> {
    const response = await this.fetch<{ token: string; user: User }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });

    this.setAuthToken(response.token);
    return response;
  }

  /**
   * Logout user
   */
  async logout(): Promise<void> {
    await this.fetch('/auth/logout', { method: 'POST' });
    this.token = null;
    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth_token');
    }
  }

  // ==========================================
  // WebSocket Connection for Real-time Updates
  // ==========================================

  /**
   * Connect to WebSocket for real-time updates
   */
  connectWebSocket(handlers: {
    onJobUpdate?: (job: ProcessingJob) => void;
    onDiscrepancyFound?: (discrepancy: Discrepancy) => void;
    onNotification?: (notification: any) => void;
  }): WebSocket {
    const wsUrl = API_BASE_URL.replace('http', 'ws') + '/ws';
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('WebSocket connected');
      // Send auth token
      if (this.token) {
        ws.send(JSON.stringify({ type: 'auth', token: this.token }));
      }
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      switch (data.type) {
        case 'job_update':
          handlers.onJobUpdate?.(data.payload);
          break;
        case 'discrepancy_found':
          handlers.onDiscrepancyFound?.(data.payload);
          break;
        case 'notification':
          handlers.onNotification?.(data.payload);
          break;
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    return ws;
  }
}

/**
 * Custom API Error class
 */
class APIError extends Error {
  constructor(
    message: string,
    public statusCode: number,
    public details?: any
  ) {
    super(message);
    this.name = 'APIError';
  }
}

// Export singleton instance
export const apiClient = new APIClient();

// Export for use in React Query hooks
export default apiClient;