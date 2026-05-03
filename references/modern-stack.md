# Modern Stack Reference (2025+)

> Read on-demand เมื่อ Sara/Aaron/Dave ต้องเลือก stack

## Runtime
- **Edge**: Cloudflare Workers, Vercel Edge, Deno Deploy, Bun
- **Serverless**: AWS Lambda (cold start mitigation), Cloud Run
- **Container**: K8s (EKS/GKE/AKS), ECS, Cloud Run, Fly.io, Railway

## Languages momentum
- TypeScript (mainstream), Python (ML/data + web), Go (infra)
- **Rust** (perf/safety), **Bun runtime** (JS perf)
- Kotlin (JVM mobile + backend), Swift 5.9+ (iOS)

## Modern Web
- **React Server Components** (Next 14+ App Router) default
- **Vue 3** Composition + `<script setup>`, **Nuxt 3**
- **Svelte 5** (runes), **Solid**, **Astro** (content)
- **HTMX** + Hypermedia (no-build for simple)

## Build / Tools
- **Vite** > Webpack; **Turbopack** (Next)
- **Biome** > ESLint+Prettier (Rust, faster)
- **uv** > pip+poetry (Py — Rust, 10x)
- **pnpm** > npm/yarn (disk-efficient)
- **Bun** runtime + bundler + test runner (all-in-one)

## Database
- **Drizzle ORM** > Prisma (TS — bundle-light)
- **sqlc** (Go — type-safe SQL)
- **SQLAlchemy 2.0** (Py — async typed)
- Postgres + extension (pgvector, pg_partman, TimescaleDB)
- **Turso** / **Cloudflare D1** (edge SQLite)
- **Neon** / **Supabase** (Postgres serverless)

## AI / LLM
- **Vector DB**: pgvector (default), Pinecone, Qdrant, Weaviate
- **RAG**: chunk → embed → retrieve → rerank → generate
- **Eval**: braintrust, promptfoo, langfuse (LLM-as-judge + golden)
- **Frameworks**: Vercel AI SDK, LangChain (caution), DSPy
- **Hosting**: OpenAI, Anthropic, Gemini, local (Ollama, vLLM)
- **Pattern**: structured output (JSON schema), tool use, agentic loop, guardrail

## Observability
- **OpenTelemetry** (vendor-neutral) default
- **Grafana stack** (Loki/Mimir/Tempo) self-hosted; Datadog managed
- **Sentry** (errors), **PostHog** (product analytics + feature flag)

## Auth
- **Clerk**, **Auth.js** (NextAuth), **Supabase Auth**, **Better Auth**
- **Passkey** (WebAuthn) > password
- **SSO**: OIDC default, SAML enterprise
