import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import CompliancePage from '../../app/compliance/page';
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

describe('Compliance Page', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Validation Rules Display', () => {
    it('should display all 7 validation rules', () => {
      render(<CompliancePage />);

      expect(screen.getByText(/Minimum Wage Compliance/i)).toBeInTheDocument();
      expect(screen.getByText(/Social Insurance Premiums/i)).toBeInTheDocument();
      expect(screen.getByText(/Pension Parameters/i)).toBeInTheDocument();
      expect(screen.getByText(/Holiday Allowance/i)).toBeInTheDocument();
      expect(screen.getByText(/Working Hours Limits/i)).toBeInTheDocument();
      expect(screen.getByText(/Overtime Compensation/i)).toBeInTheDocument();
      expect(screen.getByText(/Leave Entitlements/i)).toBeInTheDocument();
    });

    it('should show rule descriptions and thresholds', () => {
      render(<CompliancePage />);

      expect(screen.getByText(/WML.*€.*per month/i)).toBeInTheDocument();
      expect(screen.getByText(/8%.*holiday allowance/i)).toBeInTheDocument();
      expect(screen.getByText(/40 hours.*per week/i)).toBeInTheDocument();
    });
  });

  describe('Cross-Reference Validation', () => {
    it('should run validation when SETU file is selected', async () => {
      const mockSetuFiles = [
        { filename: 'cao-metalektro.setu.json', created_at: '2024-02-01' },
        { filename: 'cao-bouw.setu.json', created_at: '2024-01-15' },
      ];

      const mockValidationResult = {
        cao_name: 'CAO Metalektro',
        validation_date: '2024-02-19',
        rules: [
          {
            rule: 'minimum_wage',
            status: 'passed',
            message: 'All wage scales exceed WML'
          },
          {
            rule: 'holiday_allowance',
            status: 'failed',
            message: 'Holiday allowance is 7.5%, below required 8%',
            details: {
              found: 7.5,
              required: 8.0
            }
          }
        ],
        summary: {
          total_rules: 7,
          passed: 6,
          failed: 1,
          warnings: 0
        }
      };

      (api.getSetuFiles as jest.Mock).mockResolvedValue(mockSetuFiles);
      (api.validateCompliance as jest.Mock).mockResolvedValue(mockValidationResult);

      render(<CompliancePage />);

      await waitFor(() => {
        expect(screen.getByText('cao-metalektro.setu.json')).toBeInTheDocument();
      });

      const selectButton = screen.getByRole('button', { name: /Validate/i });
      fireEvent.click(selectButton);

      await waitFor(() => {
        expect(api.validateCompliance).toHaveBeenCalledWith('cao-metalektro.setu.json');
        expect(screen.getByText(/6 passed/i)).toBeInTheDocument();
        expect(screen.getByText(/1 failed/i)).toBeInTheDocument();
      });
    });

    it('should display validation results with color coding', async () => {
      const mockValidationResult = {
        rules: [
          { rule: 'minimum_wage', status: 'passed' },
          { rule: 'holiday_allowance', status: 'failed' },
          { rule: 'pension_parameters', status: 'warning' }
        ]
      };

      (api.validateCompliance as jest.Mock).mockResolvedValue(mockValidationResult);

      render(<CompliancePage />);

      const validateButton = screen.getByRole('button', { name: /Run Validation/i });
      fireEvent.click(validateButton);

      await waitFor(() => {
        const passedElement = screen.getByText(/minimum_wage.*passed/i);
        expect(passedElement).toHaveClass('text-green-600');

        const failedElement = screen.getByText(/holiday_allowance.*failed/i);
        expect(failedElement).toHaveClass('text-red-600');

        const warningElement = screen.getByText(/pension_parameters.*warning/i);
        expect(warningElement).toHaveClass('text-yellow-600');
      });
    });

    it('should show detailed failure reasons', async () => {
      const mockValidationResult = {
        rules: [
          {
            rule: 'minimum_wage',
            status: 'failed',
            message: 'Scale 1, Step 1 is below WML',
            details: {
              scale: 1,
              step: 1,
              found_wage: 1800,
              minimum_required: 1995
            }
          }
        ]
      };

      (api.validateCompliance as jest.Mock).mockResolvedValue(mockValidationResult);

      render(<CompliancePage />);

      const validateButton = screen.getByRole('button', { name: /Run Validation/i });
      fireEvent.click(validateButton);

      await waitFor(() => {
        expect(screen.getByText(/Scale 1, Step 1 is below WML/i)).toBeInTheDocument();
        expect(screen.getByText(/€1,800/i)).toBeInTheDocument();
        expect(screen.getByText(/€1,995/i)).toBeInTheDocument();
      });
    });

    it('should allow exporting validation report', async () => {
      const mockValidationResult = {
        cao_name: 'CAO Metalektro',
        validation_date: '2024-02-19',
        summary: { total_rules: 7, passed: 7, failed: 0 }
      };

      (api.validateCompliance as jest.Mock).mockResolvedValue(mockValidationResult);
      (api.exportComplianceReport as jest.Mock).mockResolvedValue(
        new Blob(['report content'], { type: 'application/pdf' })
      );

      render(<CompliancePage />);

      const validateButton = screen.getByRole('button', { name: /Run Validation/i });
      fireEvent.click(validateButton);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Export Report/i })).toBeInTheDocument();
      });

      const exportButton = screen.getByRole('button', { name: /Export Report/i });
      fireEvent.click(exportButton);

      await waitFor(() => {
        expect(api.exportComplianceReport).toHaveBeenCalledWith('CAO Metalektro', expect.any(Object));
      });
    });
  });

  describe('Statutory Reference Data', () => {
    it('should display current statutory values', async () => {
      const mockStatutoryData = {
        effective_date: '2024-01-01',
        wml: {
          monthly_fulltime: 1995.00,
          hourly_21_plus: 11.51
        },
        social_insurance: {
          ww: 2.64,
          zvw: 6.68,
          aow: 17.90
        },
        pension: {
          retirement_age: 67.25,
          stipp_premium: 1.6
        }
      };

      (api.getStatutoryData as jest.Mock).mockResolvedValue(mockStatutoryData);

      render(<CompliancePage />);

      await waitFor(() => {
        expect(screen.getByText(/€1,995.00/i)).toBeInTheDocument();
        expect(screen.getByText(/67.25 years/i)).toBeInTheDocument();
        expect(screen.getByText(/17.90%/i)).toBeInTheDocument();
      });
    });

    it('should allow updating statutory reference period', async () => {
      const mockStatutoryPeriods = [
        { period: '2024-01', label: 'January 2024' },
        { period: '2023-07', label: 'July 2023' },
      ];

      (api.getStatutoryPeriods as jest.Mock).mockResolvedValue(mockStatutoryPeriods);

      render(<CompliancePage />);

      await waitFor(() => {
        expect(screen.getByText('January 2024')).toBeInTheDocument();
      });

      const periodSelect = screen.getByRole('combobox', { name: /Period/i });
      fireEvent.change(periodSelect, { target: { value: '2023-07' } });

      await waitFor(() => {
        expect(api.getStatutoryData).toHaveBeenCalledWith('2023-07');
      });
    });
  });

  describe('Batch Validation', () => {
    it('should validate multiple CAOs at once', async () => {
      const mockSetuFiles = [
        { filename: 'cao-metalektro.setu.json' },
        { filename: 'cao-bouw.setu.json' },
        { filename: 'cao-retail.setu.json' },
      ];

      const mockBatchResults = [
        { cao: 'metalektro', passed: 7, failed: 0 },
        { cao: 'bouw', passed: 6, failed: 1 },
        { cao: 'retail', passed: 5, failed: 2 },
      ];

      (api.getSetuFiles as jest.Mock).mockResolvedValue(mockSetuFiles);
      (api.validateBatch as jest.Mock).mockResolvedValue(mockBatchResults);

      render(<CompliancePage />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Validate All/i })).toBeInTheDocument();
      });

      const validateAllButton = screen.getByRole('button', { name: /Validate All/i });
      fireEvent.click(validateAllButton);

      await waitFor(() => {
        expect(api.validateBatch).toHaveBeenCalledWith(mockSetuFiles);
        expect(screen.getByText(/metalektro.*100%/i)).toBeInTheDocument();
        expect(screen.getByText(/bouw.*86%/i)).toBeInTheDocument();
        expect(screen.getByText(/retail.*71%/i)).toBeInTheDocument();
      });
    });

    it('should show progress during batch validation', async () => {
      const mockSetuFiles = Array(10).fill(null).map((_, i) => ({
        filename: `cao-${i}.setu.json`
      }));

      (api.getSetuFiles as jest.Mock).mockResolvedValue(mockSetuFiles);
      (api.validateBatch as jest.Mock).mockImplementation(
        () => new Promise(resolve => setTimeout(resolve, 1000))
      );

      render(<CompliancePage />);

      const validateAllButton = screen.getByRole('button', { name: /Validate All/i });
      fireEvent.click(validateAllButton);

      expect(screen.getByText(/Validating.*0.*10/i)).toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    it('should handle validation errors gracefully', async () => {
      (api.validateCompliance as jest.Mock).mockRejectedValue(
        new Error('Invalid SETU structure')
      );

      render(<CompliancePage />);

      const validateButton = screen.getByRole('button', { name: /Run Validation/i });
      fireEvent.click(validateButton);

      await waitFor(() => {
        expect(screen.getByText(/Validation failed.*Invalid SETU structure/i)).toBeInTheDocument();
      });
    });

    it('should handle missing statutory data', async () => {
      (api.getStatutoryData as jest.Mock).mockRejectedValue(
        new Error('Statutory data not found for period')
      );

      render(<CompliancePage />);

      await waitFor(() => {
        expect(screen.getByText(/Statutory data unavailable/i)).toBeInTheDocument();
      });
    });
  });
});