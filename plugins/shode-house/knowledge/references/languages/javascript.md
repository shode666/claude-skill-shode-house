# JavaScript — Best Practices

> **Use cases**: Frontend, Node.js, tooling, browser extension
> **Why**: ฐานเว็บหลัก (legacy + new), no compile step
> **Note**: ทีมใหม่แนะนำ TypeScript; JS pure เฉพาะ small project / config / migration

## Setup
- **Runtime**: Node 20+ LTS, Bun, Deno
- **PM**: pnpm (default), Bun, npm
- **Lint+Format**: Biome (Rust) > ESLint+Prettier
- **Module**: ESM (`type: "module"` ใน package.json) — CommonJS legacy

## Best Practices
- `const` > `let` > `var` (ห้าม `var`)
- Arrow function for callback, `function` for hoisted
- Destructure import + assignment
- Template literal > string concat
- Optional chaining `?.` + nullish `??`
- `Array.prototype` chaining (map/filter/reduce); `for...of` for side-effect
- `async/await` > Promise.then chain
- Top-level `await` (ESM)
- JSDoc สำหรับ type hint (ถ้าไม่ใช้ TS)

## Modern Patterns
- Module-level state minimized
- Named export > default
- Strict equality `===` (avoid `==`)
- Immutable update (spread, structuredClone)
- Object pattern instead of class (มัก simpler)
- Generator/iterator สำหรับ large dataset
- AbortController สำหรับ fetch cancel

## Frontend
- **React/Vue/Svelte** (เลือก 1)
- **Vite** (default bundler)
- **TanStack Query** (server state)
- Web Component สำหรับ design system reusable
- Service Worker + IndexedDB สำหรับ offline

## Node Backend
- Express (legacy/simple), Fastify (perf), Hono (edge), Koa (modern)
- Native `node:test` (built-in test runner)
- `node:fetch` built-in (no axios needed)

## Testing
- Vitest (Vite-native), Jest (legacy), node:test (built-in)
- Playwright for E2E

## ห้าม
- `var`
- `==` (use `===`)
- `eval`, `Function` constructor
- Mutable global
- `JSON.parse` raw → wrap try/catch + validate
- Sync I/O ใน server (block event loop)
- Callback hell → use async/await
- Direct DOM manipulation ใน React/Vue (use ref)

## Migration to TypeScript
- เริ่มที่ tsconfig `allowJs: true`
- เปลี่ยน `.js` → `.ts` ทีละไฟล์ (boundary first)
- JSDoc → type annotation
- Strict mode after coverage > 80%
