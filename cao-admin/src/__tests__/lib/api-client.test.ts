/**
 * Unit tests for API client functions
 */

import * as api from '../../lib/api/client';
import { processFile } from '../../lib/api/processing';

// Mock fetch globally
global.fetch = jest.fn();

describe('API Client', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (global.fetch as jest.Mock).mockClear();
  });

  describe('getCaoFiles', () => {
    it('should fetch CAO files from API', async () => {
      const mockFiles = [
        { filename: 'cao-test.pdf', size: 1024, created_at: '2024-01-01' }
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockFiles,
      });

      const files = await api.getCaoFiles();

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/cao/files'),
        expect.any(Object)
      );
      expect(files).toEqual(mockFiles);
    });

    it('should handle API errors gracefully', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
      });

      await expect(api.getCaoFiles()).rejects.toThrow('Failed to fetch CAO files');
    });

    it('should handle network errors', async () => {
      (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

      await expect(api.getCaoFiles()).rejects.toThrow('Network error');
    });
  });

  describe('getCaoDetails', () => {
    it('should fetch CAO details by name', async () => {
      const mockDetails = {
        name: 'cao-metalektro',
        setu_data: { caoName: 'CAO Metalektro' },
        moments: [],
        timeline: null,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockDetails,
      });

      const details = await api.getCaoDetails('cao-metalektro');

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/cao/cao-metalektro'),
        expect.any(Object)
      );
      expect(details).toEqual(mockDetails);
    });

    it('should handle 404 for non-existent CAO', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
      });

      await expect(api.getCaoDetails('non-existent')).rejects.toThrow('CAO not found');
    });
  });

  describe('searchCao', () => {
    it('should search CAO files with query', async () => {
      const mockResults = [
        { filename: 'cao-metalektro.pdf', relevance: 0.95 }
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResults,
      });

      const results = await api.searchCao('metal');

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/cao/search?q=metal'),
        expect.any(Object)
      );
      expect(results).toEqual(mockResults);
    });

    it('should encode special characters in search query', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });

      await api.searchCao('test & special');

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('q=test%20%26%20special'),
        expect.any(Object)
      );
    });

    it('should return empty array for no results', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });

      const results = await api.searchCao('nonexistent');

      expect(results).toEqual([]);
    });
  });

  describe('processOcr', () => {
    it('should trigger OCR processing', async () => {
      const mockResponse = {
        status: 'success',
        ocr_file: 'test.ocr.json',
        processing_time: 12.5,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await api.processOcr('test.pdf');

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/process/ocr'),
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
          body: JSON.stringify({ filename: 'test.pdf' }),
        })
      );
      expect(result).toEqual(mockResponse);
    });

    it('should handle OCR processing errors', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ detail: 'Invalid PDF file' }),
      });

      await expect(api.processOcr('invalid.pdf')).rejects.toThrow('Invalid PDF file');
    });
  });

  describe('extractSetu', () => {
    it('should extract SETU data from OCR', async () => {
      const mockResponse = {
        status: 'success',
        setu_file: 'test.setu.json',
        judge_report: 'test.judge_report.json',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await api.extractSetu('test.md', 'Test CAO');

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/process/extract-setu'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            ocr_file: 'test.md',
            cao_name: 'Test CAO',
          }),
        })
      );
      expect(result).toEqual(mockResponse);
    });
  });

  describe('validateSetu', () => {
    it('should validate SETU data', async () => {
      const mockResponse = {
        is_valid: true,
        errors: [],
        warnings: ['Missing optional field: description'],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await api.validateSetu('test.setu.json');

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/process/validate-setu'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ setu_file: 'test.setu.json' }),
        })
      );
      expect(result).toEqual(mockResponse);
    });

    it('should return validation errors', async () => {
      const mockResponse = {
        is_valid: false,
        errors: ['Missing required field: documentType'],
        warnings: [],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await api.validateSetu('invalid.setu.json');

      expect(result.is_valid).toBe(false);
      expect(result.errors).toContain('Missing required field: documentType');
    });
  });

  describe('generateTimeline', () => {
    it('should generate timeline for CAO', async () => {
      const mockTimeline = {
        cao_name: 'Test CAO',
        events: [
          { date: '2024-01-01', type: 'cao_start', description: 'CAO begins' },
          { date: '2024-06-01', type: 'salary_increase', description: '3% increase' },
        ],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockTimeline,
      });

      const timeline = await api.generateTimeline('test-cao');

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/cao/test-cao/timeline'),
        expect.objectContaining({
          method: 'POST',
        })
      );
      expect(timeline).toEqual(mockTimeline);
    });
  });

  describe('getTimeline', () => {
    it('should fetch existing timeline', async () => {
      const mockTimeline = {
        cao_name: 'Test CAO',
        events: [],
        generated_at: '2024-01-01T00:00:00',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockTimeline,
      });

      const timeline = await api.getTimeline('test-cao');

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/cao/test-cao/timeline'),
        expect.objectContaining({
          method: 'GET',
        })
      );
      expect(timeline).toEqual(mockTimeline);
    });

    it('should return null for non-existent timeline', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 404,
      });

      const timeline = await api.getTimeline('no-timeline');

      expect(timeline).toBeNull();
    });
  });

  describe('validateCompliance', () => {
    it('should validate SETU compliance', async () => {
      const mockResponse = {
        compliance_score: 0.85,
        violations: [
          { type: 'minimum_wage', severity: 'high', description: 'Below WML' },
        ],
        recommendations: [],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await api.validateCompliance('test.setu.json');

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/compliance/validate'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ setu_file: 'test.setu.json' }),
        })
      );
      expect(result).toEqual(mockResponse);
    });
  });

  describe('downloadFile', () => {
    it('should download file as blob', async () => {
      const mockBlob = new Blob(['PDF content'], { type: 'application/pdf' });

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        blob: async () => mockBlob,
      });

      const blob = await api.downloadFile('test.pdf');

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/cao/download/test.pdf'),
        expect.any(Object)
      );
      expect(blob).toEqual(mockBlob);
    });

    it('should handle download errors', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 404,
      });

      await expect(api.downloadFile('missing.pdf')).rejects.toThrow('File not found');
    });
  });
});

describe('Processing API', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('processFile', () => {
    it('should process file through complete pipeline', async () => {
      const mockOcrResponse = {
        status: 'success',
        ocr_file: 'test.ocr.json',
      };

      const mockSetuResponse = {
        status: 'success',
        setu_file: 'test.setu.json',
        judge_report: 'test.judge.json',
      };

      const mockTimelineResponse = {
        cao_name: 'Test CAO',
        events: [],
      };

      // Mock sequential API calls
      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockOcrResponse,
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockSetuResponse,
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockTimelineResponse,
        });

      const result = await processFile('test.pdf', 'Test CAO');

      expect(result).toEqual({
        ocr: mockOcrResponse,
        setu: mockSetuResponse,
        timeline: mockTimelineResponse,
      });
      expect(fetch).toHaveBeenCalledTimes(3);
    });

    it('should handle pipeline failures gracefully', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({ detail: 'OCR failed' }),
      });

      await expect(processFile('test.pdf', 'Test CAO')).rejects.toThrow('OCR failed');
    });

    it('should support progress callbacks', async () => {
      const progressCallback = jest.fn();

      const mockOcrResponse = { status: 'success', ocr_file: 'test.ocr.json' };
      const mockSetuResponse = { status: 'success', setu_file: 'test.setu.json' };
      const mockTimelineResponse = { cao_name: 'Test CAO', events: [] };

      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({ ok: true, json: async () => mockOcrResponse })
        .mockResolvedValueOnce({ ok: true, json: async () => mockSetuResponse })
        .mockResolvedValueOnce({ ok: true, json: async () => mockTimelineResponse });

      await processFile('test.pdf', 'Test CAO', progressCallback);

      expect(progressCallback).toHaveBeenCalledWith('ocr', 'processing');
      expect(progressCallback).toHaveBeenCalledWith('ocr', 'completed');
      expect(progressCallback).toHaveBeenCalledWith('extraction', 'processing');
      expect(progressCallback).toHaveBeenCalledWith('extraction', 'completed');
      expect(progressCallback).toHaveBeenCalledWith('timeline', 'processing');
      expect(progressCallback).toHaveBeenCalledWith('timeline', 'completed');
    });
  });
});