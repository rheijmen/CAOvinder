/**
 * API client for processing jobs
 */

export interface ProcessingJob {
  id: string;
  cao_name: string;
  status: "queued" | "running" | "complete" | "failed";
  stage: string;
  progress: number;
  started_at?: string;
  message: string;
  error_details?: string;
  retry_from_step?: number;
  ocr_file?: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Retry a failed job from its failure point
 */
export async function retryJob(jobId: string): Promise<{ message: string; job: ProcessingJob }> {
  const response = await fetch(`${API_BASE}/api/v1/jobs/${jobId}/retry`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to retry job");
  }

  return response.json();
}

/**
 * Get job status
 */
export async function getJob(jobId: string): Promise<ProcessingJob> {
  const response = await fetch(`${API_BASE}/api/v1/jobs/${jobId}`);

  if (!response.ok) {
    throw new Error("Failed to fetch job status");
  }

  return response.json();
}

/**
 * List all jobs
 */
export async function listJobs(status?: string): Promise<{ data: ProcessingJob[]; total: number }> {
  const url = status
    ? `${API_BASE}/api/v1/jobs?status=${status}`
    : `${API_BASE}/api/v1/jobs`;

  const response = await fetch(url);

  if (!response.ok) {
    throw new Error("Failed to fetch jobs");
  }

  return response.json();
}

/**
 * Poll job status until completion or failure
 */
export async function pollJobStatus(
  jobId: string,
  onUpdate: (job: ProcessingJob) => void,
  intervalMs: number = 2000
): Promise<ProcessingJob> {
  return new Promise((resolve, reject) => {
    const checkStatus = async () => {
      try {
        const job = await getJob(jobId);
        onUpdate(job);

        if (job.status === "complete") {
          resolve(job);
        } else if (job.status === "failed") {
          reject(new Error(job.error_details || "Job failed"));
        } else {
          // Continue polling
          setTimeout(checkStatus, intervalMs);
        }
      } catch (error) {
        reject(error);
      }
    };

    checkStatus();
  });
}

// Pipeline-specific types
export interface PipelineStatus {
  pipeline_id: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  cao_file?: string;
  started_at?: string;
  duration?: number | null;
  stages: {
    gemini: StageStatus;
    mistral_large: StageStatus;
    mistral_small: StageStatus;
  };
}

export interface StageStatus {
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'cancelled';
  duration: number | null;
  error?: string;
}

export interface PipelineResults {
  pipeline_id: string;
  cao_name: string;
  setu_file: string;
  judge_report: string;
  extracted_fields: Record<string, { found: boolean; confidence: number }>;
}

/**
 * Start a new 3-LLM extraction pipeline
 */
export async function startPipeline(ocrFile: string) {
  const response = await fetch(`${API_BASE}/api/v1/pipeline/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ocr_file: ocrFile })
  });

  if (!response.ok) {
    throw new Error('Failed to start pipeline');
  }

  return response.json();
}

/**
 * Get pipeline status
 */
export async function getPipelineStatus(pipelineId: string): Promise<PipelineStatus> {
  const response = await fetch(`${API_BASE}/api/v1/pipeline/${pipelineId}/status`);

  if (!response.ok) {
    throw new Error('Failed to get pipeline status');
  }

  return response.json();
}

/**
 * Get all pipelines
 */
export async function getAllPipelines(): Promise<PipelineStatus[]> {
  const response = await fetch(`${API_BASE}/api/v1/pipelines`);

  if (!response.ok) {
    throw new Error('Failed to get pipelines');
  }

  const data = await response.json();
  return data.pipelines || [];
}

/**
 * Retry failed pipeline
 */
export async function retryPipeline(pipelineId: string) {
  const response = await fetch(`${API_BASE}/api/v1/pipeline/${pipelineId}/retry`, {
    method: 'POST'
  });

  if (!response.ok) {
    throw new Error('Failed to retry pipeline');
  }

  return response.json();
}

/**
 * Get pipeline results
 */
export async function getPipelineResults(pipelineId: string): Promise<PipelineResults> {
  const response = await fetch(`${API_BASE}/api/v1/pipeline/${pipelineId}/results`);

  if (!response.ok) {
    throw new Error('Failed to get pipeline results');
  }

  return response.json();
}