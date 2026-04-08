# 🧠 Team Memory: The Source of Truth

**Instructions:**
1. Go to **Settings > Rules & Skills > Memories**.
2. Click **Create Memory**.
3. Name it: `Team Standards & Architecture Patterns`.
4. Copy the content below into the memory body.

---

# Team Standards & Architecture Patterns

## 1. Coding Conventions
- **Naming:** 
  - Variables/Functions: `camelCase` (e.g., `getUserData`)
  - Components: `PascalCase` (e.g., `UserProfile`)
  - Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_RETRY_COUNT`)
  - Files: Match the export (e.g., `UserProfile.tsx`, `utils.ts`)
- **TypeScript:** 
  - Strict Mode: ON.
  - `any`: STRICTLY FORBIDDEN. Use `unknown` or define the type.
  - Interfaces: Prefer `interface` over `type` for object definitions.
- **Comments:** Explain "Why", not "What". Code should be self-documenting.

## 2. Tech Stack Rules (The Hyperstack)
- **Framework:** Next.js 14+ (App Router).
- **Data Fetching:** Server Components (RSC) for initial load. Server Actions for mutations. TanStack Query for complex client-side state.
- **Styling:** Tailwind CSS + Shadcn/UI. Avoid arbitrary values; use theme tokens.
- **Database:** Supabase (PostgreSQL) managed via Prisma ORM.
- **Components:**
  - Client Components: Mark with `"use client"` at the very top.
  - Server Components: Default. Keep them logic-free (rendering only).

## 3. Git Workflow
- **Branches:** `feature/feature-name`, `fix/bug-name`, `chore/task-name`.
- **Commit Messages:** Conventional Commits.
  - `feat: add user login`
  - `fix: resolve hydration error`
  - `docs: update API spec`
  - `style: format code`

## 4. Testing Requirements
- **Unit Tests:** Business logic must have 100% coverage (Vitest).
- **Components:** UI components must have snapshot tests.
- **Integration:** Critical user flows (Login, Checkout) must have E2E tests (Playwright).
- **Visual:** Use Playwright snapshots for visual regression.

## 5. Security Checklist
- [ ] Inputs validated with Zod.
- [ ] Secrets accessed via `process.env`.
- [ ] No sensitive data in client-side bundles.
- [ ] API routes protected by Auth middleware.
- [ ] Dependencies scanned for vulnerabilities.

## 6. Communication Protocols (Multi-Agent)
- **Handoffs:** When completing a task, explicitly tag the next agent.
  - Example: "@QA Engineer Feature X is ready for testing. Relevant files: [list]."
- **Conflict Resolution:** If unsure about an architectural decision, ALWAYS defer to @System Architect.
- **Context Sharing:**
  - Updates to API contracts -> Notify @Frontend Specialist & @Backend Specialist.
  - Schema changes -> Notify @Database Architect.
- **Status Updates:** Start every major response with a status indicator: `[PLANNING]`, `[BUILDING]`, `[TESTING]`, `[DONE]`.
