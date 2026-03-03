import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import HomePage from '../../app/page';
import * as api from '../../lib/api/client';

// Mock the API client
jest.mock('../../lib/api/client');

// Mock Next.js router
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    refresh: jest.fn(),
  }),
}));

describe('Home Page', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Overview Statistics', () => {
    it('should display total CAO count', async () => {
      const mockStats = {
        total_caos: 47,
        processed_caos: 23,
        pending_caos: 24,
        failed_caos: 0
      };

      (api.getOverviewStats as jest.Mock).mockResolvedValue(mockStats);

      render(<HomePage />);

      await waitFor(() => {
        expect(screen.getByText('47')).toBeInTheDocument();
        expect(screen.getByText(/Total CAOs/i)).toBeInTheDocument();
      });
    });

    it('should display processing statistics', async () => {
      const mockStats = {
        total_caos: 50,
        processed_caos: 30,
        pending_caos: 18,
        failed_caos: 2,
        processing_rate: 60
      };

      (api.getOverviewStats as jest.Mock).mockResolvedValue(mockStats);

      render(<HomePage />);

      await waitFor(() => {
        expect(screen.getByText('30')).toBeInTheDocument();
        expect(screen.getByText(/Processed/i)).toBeInTheDocument();
        expect(screen.getByText('18')).toBeInTheDocument();
        expect(screen.getByText(/Pending/i)).toBeInTheDocument();
        expect(screen.getByText('2')).toBeInTheDocument();
        expect(screen.getByText(/Failed/i)).toBeInTheDocument();
        expect(screen.getByText('60%')).toBeInTheDocument();
      });
    });

    it('should display compliance summary', async () => {
      const mockStats = {
        compliance_summary: {
          total_validated: 20,
          fully_compliant: 15,
          partial_compliance: 3,
          non_compliant: 2,
          compliance_rate: 75
        }
      };

      (api.getOverviewStats as jest.Mock).mockResolvedValue(mockStats);

      render(<HomePage />);

      await waitFor(() => {
        expect(screen.getByText('75%')).toBeInTheDocument();
        expect(screen.getByText(/Compliance Rate/i)).toBeInTheDocument();
        expect(screen.getByText(/15.*fully compliant/i)).toBeInTheDocument();
      });
    });

    it('should display recent activity', async () => {
      const mockActivity = {
        recent_activities: [
          {
            timestamp: '2024-02-19T10:30:00Z',
            action: 'OCR Processing',
            cao: 'CAO Metalektro',
            status: 'completed'
          },
          {
            timestamp: '2024-02-19T09:15:00Z',
            action: 'Pipeline Extraction',
            cao: 'CAO Bouw',
            status: 'in_progress'
          },
          {
            timestamp: '2024-02-19T08:00:00Z',
            action: 'Compliance Validation',
            cao: 'CAO Retail',
            status: 'failed'
          }
        ]
      };

      (api.getRecentActivity as jest.Mock).mockResolvedValue(mockActivity);

      render(<HomePage />);

      await waitFor(() => {
        expect(screen.getByText('CAO Metalektro')).toBeInTheDocument();
        expect(screen.getByText('CAO Bouw')).toBeInTheDocument();
        expect(screen.getByText('CAO Retail')).toBeInTheDocument();
        expect(screen.getByText(/OCR Processing.*completed/i)).toBeInTheDocument();
      });
    });

    it('should show extraction coverage metrics', async () => {
      const mockStats = {
        extraction_coverage: {
          loongebouw: 85,
          functiegroepen: 92,
          toeslagen: 78,
          verlof: 65,
          pensioen: 88
        }
      };

      (api.getOverviewStats as jest.Mock).mockResolvedValue(mockStats);

      render(<HomePage />);

      await waitFor(() => {
        expect(screen.getByText(/Loongebouw.*85%/i)).toBeInTheDocument();
        expect(screen.getByText(/Functiegroepen.*92%/i)).toBeInTheDocument();
        expect(screen.getByText(/Toeslagen.*78%/i)).toBeInTheDocument();
      });
    });
  });

  describe('Quick Actions', () => {
    it('should display quick action buttons', () => {
      render(<HomePage />);

      expect(screen.getByRole('link', { name: /Process CAO/i })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /Run Pipeline/i })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /Check Compliance/i })).toBeInTheDocument();
    });

    it('should navigate to correct pages', () => {
      render(<HomePage />);

      const caoLink = screen.getByRole('link', { name: /Process CAO/i });
      expect(caoLink).toHaveAttribute('href', '/cao');

      const pipelineLink = screen.getByRole('link', { name: /Run Pipeline/i });
      expect(pipelineLink).toHaveAttribute('href', '/pipeline');

      const complianceLink = screen.getByRole('link', { name: /Check Compliance/i });
      expect(complianceLink).toHaveAttribute('href', '/compliance');
    });
  });

  describe('System Health', () => {
    it('should display API status indicators', async () => {
      const mockHealth = {
        api_status: 'healthy',
        database: 'connected',
        ocr_service: 'available',
        llm_services: {
          gemini: 'operational',
          mistral_large: 'operational',
          mistral_small: 'degraded'
        }
      };

      (api.getSystemHealth as jest.Mock).mockResolvedValue(mockHealth);

      render(<HomePage />);

      await waitFor(() => {
        expect(screen.getByText(/API.*healthy/i)).toBeInTheDocument();
        expect(screen.getByText(/Gemini.*operational/i)).toBeInTheDocument();
        expect(screen.getByText(/Mistral Small.*degraded/i)).toBeInTheDocument();
      });
    });

    it('should show warning for degraded services', async () => {
      const mockHealth = {
        llm_services: {
          gemini: 'operational',
          mistral_large: 'down',
          mistral_small: 'operational'
        }
      };

      (api.getSystemHealth as jest.Mock).mockResolvedValue(mockHealth);

      render(<HomePage />);

      await waitFor(() => {
        expect(screen.getByText(/System Alert/i)).toBeInTheDocument();
        expect(screen.getByText(/Mistral Large.*down/i)).toBeInTheDocument();
      });
    });
  });

  describe('Data Refresh', () => {
    it('should show last update time', async () => {
      const mockStats = {
        last_updated: '2024-02-19T12:00:00Z'
      };

      (api.getOverviewStats as jest.Mock).mockResolvedValue(mockStats);

      render(<HomePage />);

      await waitFor(() => {
        expect(screen.getByText(/Last updated.*12:00/i)).toBeInTheDocument();
      });
    });

    it('should auto-refresh data periodically', async () => {
      const initialStats = { total_caos: 47 };
      const updatedStats = { total_caos: 48 };

      (api.getOverviewStats as jest.Mock)
        .mockResolvedValueOnce(initialStats)
        .mockResolvedValueOnce(updatedStats);

      render(<HomePage />);

      await waitFor(() => {
        expect(screen.getByText('47')).toBeInTheDocument();
      });

      // Fast-forward time for auto-refresh (30 seconds)
      jest.advanceTimersByTime(30000);

      await waitFor(() => {
        expect(screen.getByText('48')).toBeInTheDocument();
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle API errors gracefully', async () => {
      (api.getOverviewStats as jest.Mock).mockRejectedValue(
        new Error('API connection failed')
      );

      render(<HomePage />);

      await waitFor(() => {
        expect(screen.getByText(/Unable to load statistics/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Retry/i })).toBeInTheDocument();
      });
    });

    it('should show loading state while fetching data', () => {
      (api.getOverviewStats as jest.Mock).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );

      render(<HomePage />);

      expect(screen.getByText(/Loading dashboard/i)).toBeInTheDocument();
    });
  });
});