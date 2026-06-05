import { render, screen } from '@testing-library/react';
import OrganizationPage from '@/app/organization/page';

describe('Organization Page', () => {
  it('should render organization page with correct title', () => {
    render(<OrganizationPage />);

    expect(screen.getByText('Organization Settings')).toBeInTheDocument();
  });

  it('should show organization tabs', () => {
    render(<OrganizationPage />);

    expect(screen.getByText('General')).toBeInTheDocument();
    expect(screen.getByText('Users')).toBeInTheDocument();
    expect(screen.getByText('API Keys')).toBeInTheDocument();
    expect(screen.getByText('Integrations')).toBeInTheDocument();
  });

  it('should display organization info', () => {
    render(<OrganizationPage />);

    expect(screen.getByText(/Acme Corporation/i)).toBeInTheDocument();
    expect(screen.getByText(/Enterprise Plan/i)).toBeInTheDocument();
  });
});