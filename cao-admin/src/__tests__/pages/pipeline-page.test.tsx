import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import PipelinePage from '../../app/pipeline/page';
import * as api from '../../lib/api/client';
import * as processing from '../../lib/api/processing';

// Mock the API modules
jest.mock('../../lib/api/client');
jest.mock('../../lib/api/processing');

// Mock Next.js router
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    refresh: jest.fn(),
  }),
}));

describe('Pipeline Page', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('3-LLM Extraction Pipeline', () => {
    it('should display pipeline stages correctly', async () => {
      render(<PipelinePage />);

      expect(screen.getByText(/Gemini 2.5 Flash/i)).toBeInTheDocument();
      expect(screen.getByText(/Mistral Large/i)).toBeInTheDocument();
      expect(screen.getByText(/Mistral Small/i)).toBeInTheDocument();
    });

    it('should start extraction pipeline when triggered', async () => {
      const mockOcrFiles = [
        { filename: 'cao-metalektro.ocr.json', created_at: '2024-02-01' },
      ];

      (api.getOcrFiles as jest.Mock).mockResolvedValue(mockOcrFiles);
      (processing.startPipeline as jest.Mock).mockResolvedValue({
        pipeline_id: 'pipe-123',
        status: 'started'
      });

      render(<PipelinePage />);

      await waitFor(() => {
        expect(screen.getByText('cao-metalektro.ocr.json')).toBeInTheDocument();
      });

      const startButton = screen.getByRole('button', { name: /Start Pipeline/i });
      fireEvent.click(startButton);

      await waitFor(() => {
        expect(processing.startPipeline).toHaveBeenCalledWith('cao-metalektro.ocr.json');
        expect(screen.getByText(/Pipeline started/i)).toBeInTheDocument();
      });
    });

    it('should show pipeline progress for each stage', async () => {
      const mockPipelineStatus = {
        pipeline_id: 'pipe-123',
        stages: {
          gemini: { status: 'completed', duration: 5.2 },
          mistral_large: { status: 'in_progress', duration: null },
          mistral_small: { status: 'pending', duration: null }
        }
      };

      (processing.getPipelineStatus as jest.Mock).mockResolvedValue(mockPipelineStatus);

      render(<PipelinePage />);

      await waitFor(() => {
        expect(screen.getByText(/Gemini.*completed/i)).toBeInTheDocument();
        expect(screen.getByText(/Mistral Large.*in progress/i)).toBeInTheDocument();
        expect(screen.getByText(/Mistral Small.*pending/i)).toBeInTheDocument();
      });
    });

    it('should handle pipeline errors gracefully', async () => {
      const mockPipelineStatus = {
        pipeline_id: 'pipe-123',
        stages: {
          gemini: { status: 'completed', duration: 5.2 },
          mistral_large: { status: 'failed', error: 'API rate limit exceeded', duration: null },
          mistral_small: { status: 'cancelled', duration: null }
        }
      };

      (processing.getPipelineStatus as jest.Mock).mockResolvedValue(mockPipelineStatus);

      render(<PipelinePage />);

      await waitFor(() => {
        expect(screen.getByText(/Mistral Large.*failed/i)).toBeInTheDocument();
        expect(screen.getByText(/API rate limit exceeded/i)).toBeInTheDocument();
        expect(screen.getByText(/Mistral Small.*cancelled/i)).toBeInTheDocument();
      });
    });

    it('should allow pipeline retry on failure', async () => {
      const mockPipelineStatus = {
        pipeline_id: 'pipe-123',
        status: 'failed',
        stages: {
          gemini: { status: 'completed', duration: 5.2 },
          mistral_large: { status: 'failed', error: 'Timeout', duration: null },
          mistral_small: { status: 'cancelled', duration: null }
        }
      };

      (processing.getPipelineStatus as jest.Mock).mockResolvedValue(mockPipelineStatus);
      (processing.retryPipeline as jest.Mock).mockResolvedValue({
        pipeline_id: 'pipe-124',
        status: 'started'
      });

      render(<PipelinePage />);

      await waitFor(() => {
        expect(screen.getByText(/failed/i)).toBeInTheDocument();
      });

      const retryButton = screen.getByRole('button', { name: /Retry Pipeline/i });
      fireEvent.click(retryButton);

      await waitFor(() => {
        expect(processing.retryPipeline).toHaveBeenCalledWith('pipe-123');
        expect(screen.getByText(/Pipeline restarted/i)).toBeInTheDocument();
      });
    });
  });

  describe('Status Tracking', () => {
    it('should display list of all pipeline runs', async () => {
      const mockPipelines = [
        {
          id: 'pipe-123',
          cao_file: 'cao-metalektro.pdf',
          started_at: '2024-02-01T10:00:00Z',
          status: 'completed',
          duration: 45.3
        },
        {
          id: 'pipe-124',
          cao_file: 'cao-bouw.pdf',
          started_at: '2024-02-01T11:00:00Z',
          status: 'in_progress',
          duration: null
        },
      ];

      (processing.getAllPipelines as jest.Mock).mockResolvedValue(mockPipelines);

      render(<PipelinePage />);

      await waitFor(() => {
        expect(screen.getByText('cao-metalektro.pdf')).toBeInTheDocument();
        expect(screen.getByText('cao-bouw.pdf')).toBeInTheDocument();
        expect(screen.getByText(/completed/i)).toBeInTheDocument();
        expect(screen.getByText(/in progress/i)).toBeInTheDocument();
      });
    });

    it('should auto-refresh status for active pipelines', async () => {
      const initialStatus = {
        pipeline_id: 'pipe-123',
        status: 'in_progress',
        stages: {
          gemini: { status: 'completed', duration: 5.2 },
          mistral_large: { status: 'in_progress', duration: null },
          mistral_small: { status: 'pending', duration: null }
        }
      };

      const updatedStatus = {
        pipeline_id: 'pipe-123',
        status: 'completed',
        stages: {
          gemini: { status: 'completed', duration: 5.2 },
          mistral_large: { status: 'completed', duration: 8.7 },
          mistral_small: { status: 'completed', duration: 3.4 }
        }
      };

      (processing.getPipelineStatus as jest.Mock)
        .mockResolvedValueOnce(initialStatus)
        .mockResolvedValueOnce(updatedStatus);

      render(<PipelinePage />);

      await waitFor(() => {
        expect(screen.getByText(/in progress/i)).toBeInTheDocument();
      });

      // Fast-forward time for auto-refresh
      jest.advanceTimersByTime(5000);

      await waitFor(() => {
        expect(screen.getByText(/completed/i)).toBeInTheDocument();
        expect(screen.queryByText(/in progress/i)).not.toBeInTheDocument();
      });
    });

    it('should display extraction results when pipeline completes', async () => {
      const mockResults = {
        pipeline_id: 'pipe-123',
        cao_name: 'CAO Metalektro',
        setu_file: 'cao-metalektro.setu.json',
        judge_report: 'cao-metalektro.judge_report.json',
        extracted_fields: {
          loongebouw: { found: true, confidence: 0.95 },
          functiegroepen: { found: true, confidence: 0.88 },
          toeslagen: { found: true, confidence: 0.92 },
          verlof: { found: false, confidence: 0.0 }
        }
      };

      (processing.getPipelineResults as jest.Mock).mockResolvedValue(mockResults);

      render(<PipelinePage />);

      await waitFor(() => {
        expect(screen.getByText('CAO Metalektro')).toBeInTheDocument();
        expect(screen.getByText(/loongebouw.*95%/i)).toBeInTheDocument();
        expect(screen.getByText(/functiegroepen.*88%/i)).toBeInTheDocument();
        expect(screen.getByText(/verlof.*not found/i)).toBeInTheDocument();
      });
    });

    it('should allow downloading extraction results', async () => {
      const mockResults = {
        pipeline_id: 'pipe-123',
        setu_file: 'cao-metalektro.setu.json',
        judge_report: 'cao-metalektro.judge_report.json',
      };

      (processing.getPipelineResults as jest.Mock).mockResolvedValue(mockResults);
      (api.downloadFile as jest.Mock).mockResolvedValue(new Blob(['{"setu": "data"}']));

      render(<PipelinePage />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Download SETU/i })).toBeInTheDocument();
      });

      const downloadButton = screen.getByRole('button', { name: /Download SETU/i });
      fireEvent.click(downloadButton);

      await waitFor(() => {
        expect(api.downloadFile).toHaveBeenCalledWith('cao-metalektro.setu.json');
      });
    });
  });

  describe('Error Handling', () => {
    it('should display error when pipeline fails to start', async () => {
      (processing.startPipeline as jest.Mock).mockRejectedValue(
        new Error('Insufficient API credits')
      );

      render(<PipelinePage />);

      const startButton = screen.getByRole('button', { name: /Start Pipeline/i });
      fireEvent.click(startButton);

      await waitFor(() => {
        expect(screen.getByText(/Insufficient API credits/i)).toBeInTheDocument();
      });
    });

    it('should handle network errors gracefully', async () => {
      (processing.getAllPipelines as jest.Mock).mockRejectedValue(
        new Error('Network error')
      );

      render(<PipelinePage />);

      await waitFor(() => {
        expect(screen.getByText(/Failed to load pipelines/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Retry/i })).toBeInTheDocument();
      });
    });
  });
});