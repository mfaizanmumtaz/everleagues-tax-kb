# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Development
- `npm run dev` - Start Next.js development server
- `npm run build` - Build production bundle
- `npm run start` - Start production server
- `npm run lint` - Run ESLint

### Notes on Build Configuration
- TypeScript errors are ignored during builds (`ignoreBuildErrors: true` in next.config.mjs)
- Image optimization is disabled (`unoptimized: true`)

## Architecture Overview

### Tech Stack
- **Framework**: Next.js 16 with App Router
- **UI Library**: React 19 with client-side rendering
- **Styling**: Tailwind CSS 4.1 with custom design system
- **Component Library**: Radix UI primitives (accordion, dialog, dropdown, etc.)
- **Forms**: React Hook Form with Zod validation
- **Icons**: Lucide React
- **Analytics**: Vercel Analytics

### Project Structure

```
app/
  layout.tsx          # Root layout with Analytics
  page.tsx            # Main page with section router and GovernanceLogProvider
  globals.css         # Global styles and Tailwind directives

components/
  dashboard-layout.tsx    # Sidebar navigation wrapper
  sections/              # Main feature sections (see below)
  ui/                   # Reusable UI primitives (Radix-based)

contexts/
  governance-log-context.tsx  # Governance logging state management

utils/
  governance-logger.ts        # Immutable audit log utilities

lib/
  utils.ts                   # cn() utility for class merging

hooks/
  use-mobile.ts              # Mobile detection
  use-toast.ts               # Toast notifications
```

### Application Architecture

This is a **single-page application** with client-side section routing managed through React state. The main navigation pattern:

1. [app/page.tsx](app/page.tsx) manages the active section state
2. [components/dashboard-layout.tsx](components/dashboard-layout.tsx) provides the sidebar navigation
3. Section components are rendered conditionally based on `activeSection`

**Available sections:**
- `dashboard` - Dashboard Overview ([components/sections/dashboard-overview.tsx](components/sections/dashboard-overview.tsx))
- `urls` - URL Management ([components/sections/url-management.tsx](components/sections/url-management.tsx))
- `files` - EL Cloud Files ([components/sections/el-cloud-files.tsx](components/sections/el-cloud-files.tsx))
- `chatbot` - Tax Chatbot / Knowledge Base ([components/sections/tax-chatbot.tsx](components/sections/tax-chatbot.tsx))
- `governance-logs` - Governance Audit Log ([components/sections/governance-audit-log.tsx](components/sections/governance-audit-log.tsx))

### Governance Audit Logging System

A critical compliance feature for tracking document state changes. Key characteristics:

**Immutability**: Logs are frozen using `Object.freeze()` and append-only
**Context Provider**: [contexts/governance-log-context.tsx](contexts/governance-log-context.tsx) manages log state globally
**Usage Pattern**:
```tsx
const { addLog } = useGovernanceLog()
addLog(documentId, documentName, action, fieldChanged, previousValue, newValue, reason, userId, userEmail)
```

**Utility Functions** in [utils/governance-logger.ts](utils/governance-logger.ts):
- `createGovernanceLogEntry()` - Creates immutable log entries
- `filterGovernanceLogs()` - Filters by date, user, document, action, field
- `exportLogsToCSV()` / `exportLogsToJSON()` - Export functionality
- `getUniqueUsers()` / `getUniqueDocuments()` / `getUniqueActions()` / `getUniqueFields()` - Filter helpers

**Compliance**: Logs support tax audits, legal discovery, and healthcare compliance (HIPAA, PCAOB, IRS Circular 230)

### Styling Conventions

**Utility Function**: Use `cn()` from [lib/utils.ts](lib/utils.ts) to merge Tailwind classes
```tsx
import { cn } from "@/lib/utils"
className={cn("base-class", conditional && "conditional-class")}
```

**Theme Variables**: Custom CSS variables for colors (sidebar, accent, foreground, etc.) - check [app/globals.css](app/globals.css)

**Component Pattern**: Most UI components in [components/ui/](components/ui/) are Radix UI wrappers with Tailwind styling

### Path Aliases

TypeScript path alias `@/*` maps to root directory:
```tsx
import Component from "@/components/ui/button"
import { cn } from "@/lib/utils"
```

### State Management

- **Global State**: React Context for governance logs ([contexts/governance-log-context.tsx](contexts/governance-log-context.tsx))
- **Local State**: React `useState` for section routing and UI state
- **No Redux/Zustand**: Application uses React Context and component state exclusively

### Form Handling

Forms use React Hook Form with Zod schemas:
```tsx
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
```

See [components/ui/form.tsx](components/ui/form.tsx) for form field components

## Adding New Features

### Adding a New Section

1. Create section component in [components/sections/](components/sections/)
2. Add section type to `Section` union in [app/page.tsx](app/page.tsx:12)
3. Add nav item to `navItems` array in [components/dashboard-layout.tsx](components/dashboard-layout.tsx:14)
4. Add case to switch statement in [app/page.tsx](app/page.tsx:17)

### Adding Governance Logging

When implementing document state changes:
1. Wrap component tree with `GovernanceLogProvider` (already done at root)
2. Use `useGovernanceLog()` hook to access `addLog()`
3. Log all state changes with previous/new values and reason
4. Action types: `state_changed`, `metadata_updated`, `authority_changed`, `bulk_action`, `document_published`, `document_deprecated`

### UI Components

Prefer using existing Radix UI components from [components/ui/](components/ui/) rather than building from scratch. Common components:
- Button, Input, Select, Checkbox, Switch
- Dialog, Sheet, Popover, Dropdown Menu
- Table, Card, Badge, Separator
- Toast (via Sonner), Alert Dialog

## Important Patterns

### Client Components
Most components use `"use client"` directive as the app is heavily interactive

### TypeScript
Strict mode enabled. Use proper typing for all components and functions.

### Icons
Use Lucide React icons:
```tsx
import { Shield, User, FileText } from "lucide-react"
```

### Date Handling
Use `date-fns` for date manipulation (already included in dependencies)
