# Tech Stack Overview

| Area / Concern                    | Tool / Platform                                              | Purpose / Role                                               | Notes                                                        |
| --------------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------ | ------------------------------------------------------------ |
| CMS Platform                      | **Directus**                                                 | Headless CMS managing dynamic data and content for all modules. | Chosen for flexibility, self-hosting, and strong API generation. |
| Frontend / Framework              | **Next.js**                                                  | Full-stack React framework for the web app frontend and API routes. | Provides SSR/ISR and seamless Vercel integration.            |
| Hosting / Deployment              | **Vercel**                                                   | Cloud hosting and CI/CD for frontend and edge functions.     | Optimized for Next.js and global performance.                |
| Project Structure / Monorepo      | **Turborepo**                                                | Organizes multiple packages/services under one repo.         | Ensures shared configs and efficient builds.                 |
| Language / Types                  | **TypeScript**                                               | Adds type safety and clarity to frontend and backend code.   | Reduces runtime bugs and improves DX.                        |
| Styling Framework                 | **Tailwind CSS**                                             | Utility-first styling for consistent, responsive UI.         | Enables rapid design iteration.                              |
| Component Primitives              | **Radix UI**                                                 | Accessible, unstyled primitives for UI building blocks.      | Keeps control over design while ensuring accessibility.      |
| Component System / Theme          | **shadcn/ui**                                                | Prebuilt component system built on Radix + Tailwind.         | Speeds up development with consistent design.                |
| Theme Editor / Customizer         | **tweakcn**                                                  | Live theme customization for users or admins.                | Supports white-label and branded SaaS variants.              |
| Design System / Marketing Builder | **Relume**                                                   | Page builder for marketing and landing page content.         | Simplifies marketing site creation.                          |
| State / Data Fetching             | **TanStack Query**                                           | Manages async state and server data caching.                 | Enhances data consistency and performance.                   |
| Authentication (Frontend)         | **better-auth**                                              | Client-side authentication and session handling.             | Lightweight alternative to NextAuth for modern stacks.       |
| Specialized API Layer             | **Trench + tRPC**                                            | Type-safe API layer bridging frontend and backend.           | Reduces boilerplate and improves API reliability.            |
| Database & Storage                | **Supabase**                                                 | Primary PostgreSQL database and file storage.                | Combines database, auth, and realtime features.              |
| Database ORM (Optional)           | **Prisma**                                                   | Type-safe ORM for database access.                           | Optional for advanced queries or migrations.                 |
| Compliance Platform Integration   | **SAMS (OpenControls.ai)**                                   | Compliance and audit automation integration.                 | Helps automate SOC2/GDPR frameworks.                         |
| Payments / Billing                | **Paid.ai**                                                  | Manages subscriptions and payment processing.                | Simplifies SaaS billing automation.                          |
| Background Jobs / Scheduling      | **Supabase + Directus Flows**                                | Handles async tasks and scheduled jobs.                      | Low-maintenance workflow automation.                         |
| Email / Notifications             | **Directus / Resend**                                        | Sends transactional and system emails.                       | Reliable and API-based notification delivery.                |
| Internationalization (i18n)       | **Directus i18n + Next.js**                                  | Localized content management and frontend translations.      | Streamlined for multilingual SaaS use.                       |
| CRM                               | **GoHighLevel**                                              | Manages leads, customers, and marketing flows.               | Integrates well with SaaS sales funnels.                     |
| Analytics / Monitoring            | **Google Analytics**, **Microsoft Clarity**, **Vercel Analytics** | Tracks usage, user behavior, and engagement.                 | Provides insights for UX optimization.                       |
| Observability / Monitoring        | **Trench**                                                   | Logs, traces, and error monitoring.                          | Unified monitoring for APIs and frontend.                    |
| API Documentation                 | **Mintlify**                                                 | Auto-generated developer API docs.                           | Keeps documentation synced with code.                        |
| Caching                           | **Vercel Edge Cache**                                        | Edge caching for static and dynamic pages.                   | Improves load times globally.                                |
| Testing Frameworks                | **Playwright**, **React Testing Library**                    | End-to-end and unit testing of UI and workflows.             | Ensures app stability and reliability.                       |
| Code Quality / Linting            | **ESLint**, **Prettier**, **OXlint**                         | Enforces coding standards and formatting.                    | Maintains clean, consistent codebase.                        |
| Source Control / Repo Hosting     | **GitHub**                                                   | Version control and collaboration platform.                  | Integrates with CI/CD and issue tracking.                    |
| Product & Delivery Ops            | **Huly (huly.app)**                                          | Manages tasks, releases, and roadmap tracking.               | Streamlines team delivery and project visibility.            |

## Architecture Layers

### Layer 1: Frontend (Public-Facing)
**Next.js on Vercel**

- Marketing website with static and server-side rendered pages
- Customer-facing web application and dashboards
- Public API documentation via Mintlify
- Responsive UI built with Tailwind CSS, Radix UI, and shadcn/ui components
- Theme customization capabilities via tweakcn for white-label branding
- Client-side state management via TanStack Query
- Authentication integration with better-auth
- Edge caching via Vercel Edge Network for global performance
- Next.js API routes for server-side logic when needed

### Layer 2: Backend Platform (Core)
**Trench + tRPC Custom Backend**

- Type-safe API layer built with tRPC for full-stack type safety
- Custom business logic and application-specific endpoints
- Authentication and authorization handling
- Integration point for all backend services
- Full observability and monitoring via Trench
- Direct database access via Supabase client or Prisma ORM
- RESTful and type-safe APIs consumed by Next.js frontend

**Directus CMS (Content Management)**

- Headless CMS for managing dynamic content and structured data
- Auto-generated REST & GraphQL APIs for content delivery
- Built-in admin interface for content editors
- Content versioning and workflows via Directus Flows
- Multi-language content support (i18n)
- Asset management integrated with Supabase Storage
- Webhooks for content change notifications

### Layer 3: Specialized Processing
**Background Jobs & Automation**

- Supabase functions for database triggers and scheduled tasks
- Directus Flows for content-driven workflow automation
- Complex async processing and job queuing
- Email notifications via Resend
- Webhook handling for external integrations
- Scheduled maintenance and cleanup tasks

### Layer 4: Data & Storage
**Supabase (Postgres + Storage)**

- Primary PostgreSQL database for all application data
- Row-Level Security (RLS) for multi-tenant data isolation
- Real-time subscriptions for live data updates
- File and asset storage (blob storage)
- Automatic backups and point-in-time recovery
- Database connection pooling and optimization
- Optional Prisma ORM layer for type-safe database access

### Layer 5: External Integrations

- **Paid.ai:** Subscription management and payment processing
- **SAMS (OpenControls.ai):** Compliance framework and audit automation
- **GoHighLevel:** CRM, lead management, and marketing automation
- **Resend:** Transactional email delivery service
- **Google Analytics & Microsoft Clarity:** User behavior analytics and session replay
- **Vercel Analytics:** Performance and Web Vitals monitoring
- **Trench:** Application observability, logging, and error tracking
- **Mintlify:** Developer API documentation platform
- **better-auth providers:** OAuth and social authentication integrations

## Visual Overview (Mermaid Diagram)

```mermaid
flowchart TB
  %% --- ZONE DEFINITIONS ---
  subgraph FrontendZone["Frontend Zone ðŸŸ¦"]
    A[User
      ðŸ‘¤]
    B[Frontend Layer
      Next.js + Tailwind + shadcn ui + TanStack Query]
  end

  subgraph BackendZone["Backend Zone ðŸŸ©"]
    C[API Layer
      Trench + tRPC]
    D[CMS / Content Layer
      nDirectus]
  end

  subgraph Infrastructure["Infrastructure ðŸŸ¨"]
    E[(Database & Storage
       Supabase + Prisma)]
    F[Background Jobs / Flows
      Directus Flows]
  end

  subgraph Integrations["External Integrations ðŸŸ¥"]
    G[Payments / Billing
      Paid.ai]
    H[Email & Notifications
      Resend]
    I[Analytics & Monitoring
      GA + Clarity + Trench]
  end

  %% --- CONNECTIONS ---
  A --> B
  B --> C
  C --> D
  C --> E
  D --> E
  C --> G
  C --> H
  F --> E
  B --> I
  C --> I

  %% --- STYLE CUSTOMIZATION ---
  style FrontendZone fill:#A7C7E7,stroke:#6B8BA4
  style BackendZone fill:#B7E7A1,stroke:#6BA46B
  style Infrastructure fill:#FFF2A1,stroke:#A49547
  style Integrations fill:#F6A1A1,stroke:#A14E4E
  ```

## Architecture Summary

The SaaS platform follows a **modular three-tier architecture** with clear separation of concerns.

**Layer 1 (Frontend):** End users interact with the **Next.js frontend** hosted on Vercel, which manages routing, UI rendering, and client-side state via **TanStack Query**. The frontend is fully type-safe with TypeScript and uses modern design patterns with Tailwind CSS and shadcn/ui components. Marketing pages are built with Relume for rapid iteration.

**Layer 2 (Backend):** The core application logic runs through a **custom API layer built with Trench + tRPC**, providing type-safe endpoints from frontend to backend. This layer handles authentication, business logic, and data operations. **Directus** operates as a separate **headless CMS** specifically for managing dynamic content, providing its own APIs for content delivery and a built-in admin interface for content editors.

**Layer 3 (Specialized Processing):** Background jobs and workflow automation are handled through **Supabase functions** and **Directus Flows**. This layer manages async tasks, scheduled jobs, email notifications via Resend, and webhook integrations with external services.

**Layer 4 (Data & Storage):** **Supabase** provides the underlying PostgreSQL database and blob storage. It offers real-time subscriptions, row-level security for multi-tenancy, and automatic backups. Both the custom backend and Directus connect to this data layer.

**Layer 5 (External Integrations):** The platform integrates with external services including **Paid.ai** (payments), **SAMS** (compliance), **GoHighLevel** (CRM), **Resend** (email), and various analytics tools (**Google Analytics**, **Microsoft Clarity**, **Trench**).

## Integration Patterns

### Primary Data Flow
```
Next.js Frontend â†’ Vercel Edge Cache â†’ tRPC API (Trench) â†’ Supabase Postgres
```
- Application data and business logic flow through the custom tRPC backend
- Full type safety from frontend to database
- Trench provides observability across the entire stack
- Vercel Edge Cache optimizes response times globally

### Content Delivery Flow
```
Next.js Frontend â†’ Directus REST/GraphQL APIs â†’ Supabase Postgres
```
- Dynamic content is served directly from Directus
- Content editors manage content via Directus admin UI
- Directus provides versioning and workflow automation for content
- Same Supabase database, different access pattern

### Authentication Flow
```
User â†’ better-auth (Frontend) â†’ tRPC Backend â†’ Supabase Auth
                              â†’ Session Management
                              â†’ Permission Checks
```
- better-auth handles frontend authentication state
- Backend validates sessions and enforces permissions
- Supabase provides underlying auth infrastructure

### Payment Processing Flow
```
Customer Action â†’ Next.js â†’ Paid.ai Checkout
                         â†’ Paid.ai Webhook â†’ tRPC API
                         â†’ Update Supabase â†’ Provision Access
```
- Payment processing handled by Paid.ai
- Webhooks trigger backend logic to provision subscriptions
- Subscription status stored in Supabase

### Multi-Tenant Architecture
```
Customer Login â†’ Authentication â†’ Organization Context
                                â†’ Row-Level Security (Supabase)
                                â†’ White-label Theme (tweakcn)
                                â†’ Scoped Data Access
```
- Each customer/organization has isolated data via RLS
- White-label theming per organization using tweakcn
- Backend enforces tenant-scoped queries

## Key Benefits

This architecture provides:

- **Type Safety:** End-to-end type safety from frontend through tRPC to database with TypeScript and Prisma
- **Content Flexibility:** Directus CMS allows non-technical users to manage content independently
- **Performance:** Edge caching via Vercel and optimized data fetching with TanStack Query
- **Scalability:** Modular architecture allows independent scaling of frontend, backend, and content services
- **Developer Experience:** Modern tooling (tRPC, Tailwind, shadcn/ui) enables rapid development
- **Multi-Tenancy:** Built-in support for SaaS business models with RLS and white-labeling
- **Observability:** Comprehensive monitoring with Trench across all application layers
- **Security:** Multiple layers of authentication, authorization, and data isolation
- **Compliance Ready:** Integration with SAMS for audit automation and compliance tracking
- **Global Performance:** Edge network deployment via Vercel for worldwide users

## Architecture Philosophy

**Separation of Concerns:** The architecture clearly separates application logic (tRPC backend) from content management (Directus CMS). This allows developers to build custom features while content editors independently manage dynamic content.

**Type-Safe First:** TypeScript is used throughout the stack, with tRPC providing compile-time type safety between frontend and backend, eliminating entire classes of runtime errors.

**Platform Leverage:** The architecture leverages best-in-class platforms for their strengths:
- Vercel for frontend hosting and edge optimization
- Supabase for database and storage infrastructure
- Directus for content management workflows
- Trench for comprehensive observability

**Key Principles:**
- Build custom logic where it provides unique value
- Use managed services to reduce operational overhead
- Maintain type safety across the entire stack
- Design for multi-tenancy from day one
- Ensure all systems are observable and debuggable
- Optimize for developer velocity without sacrificing quality
