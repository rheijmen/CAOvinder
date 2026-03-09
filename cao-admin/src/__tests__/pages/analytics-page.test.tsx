import { render, screen } from '@testing-library/react';
import AnalyticsPage from '@/app/analytics/page';

describe('Analytics Page', () => {
  it('should render analytics page with correct title', () => {
    render(<AnalyticsPage />);

    expect(screen.getByText('Analytics')).toBeInTheDocument();
  });

  it('should show key metrics cards', () => {
    render(<AnalyticsPage />);

    expect(screen.getByText(/Total CAOs Processed/i)).toBeInTheDocument();
    expect(screen.getByText(/Average Compliance Score/i)).toBeInTheDocument();
    expect(screen.getByText(/Processing Time/i)).toBeInTheDocument();
    expect(screen.getByText(/Success Rate/i)).toBeInTheDocument();
  });

  it('should display charts section', () => {
    render(<AnalyticsPage />);

    expect(screen.getByText(/Processing Trends/i)).toBeInTheDocument();
    expect(screen.getByText(/Compliance Distribution/i)).toBeInTheDocument();
  });
});