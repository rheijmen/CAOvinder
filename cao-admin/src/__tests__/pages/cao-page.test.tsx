import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import CAOPage from '../../app/cao/page';
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

describe('CAO Page', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('File List', () => {
    it('should display list of CAO files on load', async () => {
      const mockFiles = [
        { filename: 'cao-metalektro.pdf', size: 1024000, created_at: '2024-02-01' },
        { filename: 'cao-bouw.pdf', size: 2048000, created_at: '2024-01-15' },
      ];

      (api.getCaoFiles as jest.Mock).mockResolvedValue(mockFiles);

      render(<CAOPage />);

      await waitFor(() => {
        expect(screen.getByText('cao-metalektro.pdf')).toBeInTheDocument();
        expect(screen.getByText('cao-bouw.pdf')).toBeInTheDocument();
      });
    });

    it('should handle empty file list gracefully', async () => {
      (api.getCaoFiles as jest.Mock).mockResolvedValue([]);

      render(<CAOPage />);

      await waitFor(() => {
        expect(screen.getByText(/No CAO files found/i)).toBeInTheDocument();
      });
    });

    it('should show loading state while fetching files', () => {
      (api.getCaoFiles as jest.Mock).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );

      render(<CAOPage />);

      expect(screen.getByText(/Loading/i)).toBeInTheDocument();
    });

    it('should handle API errors gracefully', async () => {
      (api.getCaoFiles as jest.Mock).mockRejectedValue(new Error('API Error'));

      render(<CAOPage />);

      await waitFor(() => {
        expect(screen.getByText(/Error loading CAO files/i)).toBeInTheDocument();
      });
    });
  });

  describe('Search Functionality', () => {
    it('should filter files based on search query', async () => {
      const mockFiles = [
        { filename: 'cao-metalektro.pdf', size: 1024000, created_at: '2024-02-01' },
        { filename: 'cao-bouw.pdf', size: 2048000, created_at: '2024-01-15' },
        { filename: 'cao-retail.pdf', size: 1536000, created_at: '2024-01-20' },
      ];

      (api.getCaoFiles as jest.Mock).mockResolvedValue(mockFiles);

      render(<CAOPage />);

      await waitFor(() => {
        expect(screen.getByText('cao-metalektro.pdf')).toBeInTheDocument();
      });

      const searchInput = screen.getByPlaceholderText(/Search CAO files/i);
      fireEvent.change(searchInput, { target: { value: 'metal' } });

      await waitFor(() => {
        expect(screen.getByText('cao-metalektro.pdf')).toBeInTheDocument();
        expect(screen.queryByText('cao-bouw.pdf')).not.toBeInTheDocument();
        expect(screen.queryByText('cao-retail.pdf')).not.toBeInTheDocument();
      });
    });

    it('should show no results message for unmatched search', async () => {
      const mockFiles = [
        { filename: 'cao-metalektro.pdf', size: 1024000, created_at: '2024-02-01' },
      ];

      (api.getCaoFiles as jest.Mock).mockResolvedValue(mockFiles);

      render(<CAOPage />);

      await waitFor(() => {
        expect(screen.getByText('cao-metalektro.pdf')).toBeInTheDocument();
      });

      const searchInput = screen.getByPlaceholderText(/Search CAO files/i);
      fireEvent.change(searchInput, { target: { value: 'nonexistent' } });

      await waitFor(() => {
        expect(screen.getByText(/No files match your search/i)).toBeInTheDocument();
      });
    });

    it('should be case-insensitive', async () => {
      const mockFiles = [
        { filename: 'cao-MetalEktro.pdf', size: 1024000, created_at: '2024-02-01' },
      ];

      (api.getCaoFiles as jest.Mock).mockResolvedValue(mockFiles);

      render(<CAOPage />);

      await waitFor(() => {
        expect(screen.getByText('cao-MetalEktro.pdf')).toBeInTheDocument();
      });

      const searchInput = screen.getByPlaceholderText(/Search CAO files/i);
      fireEvent.change(searchInput, { target: { value: 'METAL' } });

      await waitFor(() => {
        expect(screen.getByText('cao-MetalEktro.pdf')).toBeInTheDocument();
      });
    });
  });

  describe('OCR Processing', () => {
    it('should trigger OCR processing when button is clicked', async () => {
      const mockFiles = [
        { filename: 'cao-metalektro.pdf', size: 1024000, created_at: '2024-02-01' },
      ];

      (api.getCaoFiles as jest.Mock).mockResolvedValue(mockFiles);
      (api.processOcr as jest.Mock).mockResolvedValue({
        status: 'success',
        ocr_file: 'cao-metalektro.ocr.json'
      });

      render(<CAOPage />);

      await waitFor(() => {
        expect(screen.getByText('cao-metalektro.pdf')).toBeInTheDocument();
      });

      const ocrButton = screen.getByRole('button', { name: /Process OCR/i });
      fireEvent.click(ocrButton);

      await waitFor(() => {
        expect(api.processOcr).toHaveBeenCalledWith('cao-metalektro.pdf');
        expect(screen.getByText(/OCR processing complete/i)).toBeInTheDocument();
      });
    });

    it('should show processing state during OCR', async () => {
      const mockFiles = [
        { filename: 'cao-metalektro.pdf', size: 1024000, created_at: '2024-02-01' },
      ];

      (api.getCaoFiles as jest.Mock).mockResolvedValue(mockFiles);
      (api.processOcr as jest.Mock).mockImplementation(
        () => new Promise(resolve => setTimeout(resolve, 100))
      );

      render(<CAOPage />);

      await waitFor(() => {
        expect(screen.getByText('cao-metalektro.pdf')).toBeInTheDocument();
      });

      const ocrButton = screen.getByRole('button', { name: /Process OCR/i });
      fireEvent.click(ocrButton);

      expect(screen.getByText(/Processing.../i)).toBeInTheDocument();
    });

    it('should handle OCR processing errors', async () => {
      const mockFiles = [
        { filename: 'cao-metalektro.pdf', size: 1024000, created_at: '2024-02-01' },
      ];

      (api.getCaoFiles as jest.Mock).mockResolvedValue(mockFiles);
      (api.processOcr as jest.Mock).mockRejectedValue(new Error('OCR failed'));

      render(<CAOPage />);

      await waitFor(() => {
        expect(screen.getByText('cao-metalektro.pdf')).toBeInTheDocument();
      });

      const ocrButton = screen.getByRole('button', { name: /Process OCR/i });
      fireEvent.click(ocrButton);

      await waitFor(() => {
        expect(screen.getByText(/OCR processing failed/i)).toBeInTheDocument();
      });
    });

    it('should disable OCR button if file already processed', async () => {
      const mockFiles = [
        {
          filename: 'cao-metalektro.pdf',
          size: 1024000,
          created_at: '2024-02-01',
          ocr_status: 'completed'
        },
      ];

      (api.getCaoFiles as jest.Mock).mockResolvedValue(mockFiles);

      render(<CAOPage />);

      await waitFor(() => {
        expect(screen.getByText('cao-metalektro.pdf')).toBeInTheDocument();
      });

      const ocrButton = screen.getByRole('button', { name: /Already Processed/i });
      expect(ocrButton).toBeDisabled();
    });
  });

  describe('File Operations', () => {
    it('should allow file download', async () => {
      const mockFiles = [
        { filename: 'cao-metalektro.pdf', size: 1024000, created_at: '2024-02-01' },
      ];

      (api.getCaoFiles as jest.Mock).mockResolvedValue(mockFiles);
      (api.downloadFile as jest.Mock).mockResolvedValue(new Blob(['pdf content']));

      render(<CAOPage />);

      await waitFor(() => {
        expect(screen.getByText('cao-metalektro.pdf')).toBeInTheDocument();
      });

      const downloadButton = screen.getByRole('button', { name: /Download/i });
      fireEvent.click(downloadButton);

      await waitFor(() => {
        expect(api.downloadFile).toHaveBeenCalledWith('cao-metalektro.pdf');
      });
    });

    it('should display file size in human-readable format', async () => {
      const mockFiles = [
        { filename: 'small.pdf', size: 1024, created_at: '2024-02-01' }, // 1 KB
        { filename: 'medium.pdf', size: 1048576, created_at: '2024-02-01' }, // 1 MB
        { filename: 'large.pdf', size: 1073741824, created_at: '2024-02-01' }, // 1 GB
      ];

      (api.getCaoFiles as jest.Mock).mockResolvedValue(mockFiles);

      render(<CAOPage />);

      await waitFor(() => {
        expect(screen.getByText('1.00 KB')).toBeInTheDocument();
        expect(screen.getByText('1.00 MB')).toBeInTheDocument();
        expect(screen.getByText('1.00 GB')).toBeInTheDocument();
      });
    });
  });
});