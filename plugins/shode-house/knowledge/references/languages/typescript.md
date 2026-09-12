# TypeScript — Best Practices

> **Use cases**: Web frontend, Node backend, full-stack, SaaS, edge runtime
> **Why**: Type safety + ecosystem ใหญ่; maintainable กว่า JS pure

## Setup
- **Runtime**: Node 20+ LTS / **Bun** (faster, all-in-one)
- **PM**: **pnpm** (default), Bun, npm
- **TS config**: `strict: true`, `noUncheckedIndexedAccess`, `noImplicitOverride`, `exactOptionalPropertyTypes`
- **Lint+Format**: **Biome** (Rust-based, replace ESLint+Prettier) > legacy ESLint+Prettier

## Type Discipline
- ห้าม `any` → ใช้ `unknown` + narrow ด้วย type guard / Zod
- Discriminated union > class hierarchy
- `as const` สำหรับ literal type
- Generic เมื่อจำเป็น — ห้าม over-generic
- Branded type สำหรับ ID (`type UserId = string & { readonly __brand: 'UserId' }`)
- `satisfies` operator ตรวจ shape โดยไม่ widen type

## Backend Stack
- **Framework**: NestJS (DI + decorator), Hono (edge), Fastify (perf), Express (legacy), Elysia (Bun-native), tRPC (e2e type)
- **ORM**: **Drizzle** (default — bundle-light, SQL-first), Prisma (rich), Kysely (query builder)
- **Validation**: Zod (runtime + type infer), Valibot (smaller bundle)
- **Auth**: Auth.js, Better Auth, Clerk, Lucia
- **Queue**: BullMQ (Redis), Inngest (managed)

## Frontend Stack
- **React 18+**: function + hooks, no class
- **Next 14+**: App Router, Server Component default, Server Actions
- **Vue 3**: `<script setup>` + Composition + Pinia
- **Svelte 5**: runes
- **State**: tanstack Query (server state), Zustand (client), Jotai (atomic)
- **Style**: Tailwind 3+, shadcn/ui, Vanilla Extract

## Testing
- **Vitest** (default) > Jest (faster, Vite-native)
- **Playwright** for E2E
- **MSW** for API mock
- Test colocate (`*.test.ts` next to source)

## Best Practices
- File ≤ 300 lines, function ≤ 30 lines, ≤ 4 params
- Named export > default export (refactor + autocomplete ดีกว่า)
- Top-level error boundary ใน React
- Suspense + ErrorBoundary pair
- Server Component default, `'use client'` ตอนต้องการ
- Avoid useEffect — derive state, event handler, server data
- Immutable update (Immer หรือ spread)

## ห้าม
- `any`, `// @ts-ignore` (โดยไม่มี ticket comment)
- `JSON.parse` raw → ใช้ Zod parse
- `eval`, `Function` constructor
- Mutable global state
- `any` in API boundary (request/response)
- Sync I/O ใน Node (block event loop)
