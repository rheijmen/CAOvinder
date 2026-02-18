# CAO Intelligence Admin Interface

A modern, production-ready admin dashboard for managing Dutch CAO (Collective Labour Agreement) document processing with AI-powered SETU v2.0 compliance checking.

## Features

### 🎯 Core Capabilities

- **CAO Document Management**: Upload, search, organize, and version control CAO PDFs
- **3-LLM Processing Pipeline**: Automated extraction using Gemini, Mistral, and Claude
- **SETU v2.0 Compliance**: Real-time validation against Dutch staffing industry standards
- **HITL Resolution**: Human-in-the-loop interface for discrepancy resolution
- **Multi-tenancy**: Full SaaS architecture with organization isolation
- **Cost Optimization**: Real-time cost tracking and budget management

### 📊 Dashboard Components

1. **Main Dashboard** (`/`)
   - Processing pipeline status
   - Real-time metrics and KPIs
   - Recent CAO activity
   - Cost tracking

2. **CAO Library** (`/cao`)
   - Advanced search and filtering
   - Grid/List view toggle
   - Bulk operations
   - Version management
   - Smart duplicate detection

3. **SETU Compliance Workbench** (`/compliance`)
   - Side-by-side comparison views
   - Field-level validation
   - Discrepancy highlighting
   - Resolution workflow
   - Audit trail

4. **Pipeline Control** (`/pipeline`)
   - Visual pipeline designer
   - Job queue management
   - Real-time progress monitoring
   - LLM provider status

## Tech Stack

- **Frontend**: Next.js 14, TypeScript, Tailwind CSS, Shadcn UI
- **State Management**: Zustand, TanStack Query
- **Charts**: Recharts
- **Backend Integration**: FastAPI (Python)
- **Database**: PostgreSQL with multi-tenant architecture
- **Authentication**: NextAuth.js (ready for SSO)

## Getting Started

### Prerequisites

```bash
Node.js 20+
PostgreSQL 15+
Python 3.11+ (for backend API)
```

### Installation

1. **Install dependencies:**
```bash
npm install
```

2. **Set up environment variables:**
```bash
cp .env.example .env.local
```

Edit `.env.local`:
```env
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/cao_intelligence

# API Backend
NEXT_PUBLIC_API_URL=http://localhost:8000

# Authentication
NEXTAUTH_SECRET=your-secret-key
NEXTAUTH_URL=http://localhost:3000

# Storage (S3 or local)
STORAGE_TYPE=local
STORAGE_PATH=/data/cao-documents
```

3. **Initialize the database:**
```bash
psql -U postgres -d cao_intelligence -f database/schema.sql
```

4. **Run the development server:**
```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## Project Structure

```
cao-admin/
├── src/
│   ├── app/                  # Next.js 14 app directory
│   │   ├── page.tsx          # Main dashboard
│   │   ├── cao/              # CAO library pages
│   │   ├── compliance/       # SETU compliance pages
│   │   ├── pipeline/         # Processing pipeline
│   │   └── api/              # API routes
│   │
│   ├── components/
│   │   ├── layout/           # Sidebar, TopBar
│   │   ├── dashboard/        # Dashboard widgets
│   │   ├── cao-library/      # CAO management components
│   │   ├── compliance/       # Compliance review components
│   │   ├── pipeline/         # Pipeline control components
│   │   └── ui/               # Shadcn UI components
│   │
│   ├── lib/
│   │   ├── api/              # API client functions
│   │   ├── store/            # Zustand stores
│   │   └── utils.ts          # Utility functions
│   │
│   └── types/                # TypeScript definitions
│       └── index.ts          # Core types
│
├── database/
│   └── schema.sql            # PostgreSQL schema
│
└── public/                   # Static assets
```

## Key Components

### CAODocument Type
```typescript
interface CAODocument {
  id: string
  name: string
  status: ProcessingStatus
  complianceStatus: ComplianceStatus
  setuData?: SETUDocument
  judgeReport?: JudgeReport
  discrepancies?: Discrepancy[]
}
```

### Processing Pipeline
```typescript
interface PipelineConfig {
  stages: [
    { type: 'ocr', provider: 'mistral' },
    { type: 'extract', provider: 'gemini' },
    { type: 'review', provider: 'mistral' },
    { type: 'judge', provider: 'mistral' }
  ]
}
```

## API Integration

The admin interface connects to the FastAPI backend:

```typescript
// Example: Fetch CAO documents
const { data } = await fetch('/api/v1/caos')
const caos = await data.json()

// Example: Start processing job
const job = await fetch('/api/v1/jobs', {
  method: 'POST',
  body: JSON.stringify({
    cao_document_id: 'uuid',
    pipeline_config: pipelineConfig
  })
})
```

## Database Schema Highlights

### Multi-tenant Architecture
- Organization-level data isolation
- Row-level security (RLS) policies
- Subscription plan management

### Key Tables
- `organizations` - Tenant management
- `cao_documents` - Main document storage
- `discrepancies` - SETU compliance issues
- `processing_jobs` - Async job queue
- `audit_logs` - Full audit trail

## Deployment

### Production Build
```bash
npm run build
npm start
```

### Docker Deployment
```bash
docker build -t cao-admin .
docker run -p 3000:3000 cao-admin
```

### Environment Variables for Production
```env
NODE_ENV=production
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
S3_BUCKET=cao-documents
SENTRY_DSN=https://...
```

## SaaS Features

### Multi-tenancy
- Complete data isolation per organization
- Custom branding support
- White-label capabilities

### Billing Integration
- Stripe integration ready
- Usage-based pricing support
- Plan limits enforcement

### API Management
- API key generation
- Rate limiting
- Usage analytics

## Security

- JWT-based authentication
- Role-based access control (RBAC)
- API rate limiting
- SQL injection prevention
- XSS protection
- CSRF tokens

## Performance

- Server-side rendering (SSR)
- Optimistic UI updates
- Lazy loading
- Image optimization
- Database query optimization
- Redis caching layer

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

Proprietary - All rights reserved

## Support

For issues and questions, contact the development team or create an issue in the repository.
