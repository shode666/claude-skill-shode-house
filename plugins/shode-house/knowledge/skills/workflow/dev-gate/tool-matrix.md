# Quality tool selection by stack

Owner: Dave/Chris. Load when selecting missing gate tooling or configuring checks,
before choosing commands. Existing verified project commands do not require this
matrix. These are preserved examples, not version-verified CLI syntax: check the
installed tool's documentation before use. No dependency installation is implied.

## Tool examples by stack

| Stack | 1 Format | 2 Imports | 3 Unused | 4 Lint | 5 Type | 6 Complexity | 9 Security |
|---|---|---|---|---|---|---|---|
| **Python** | `ruff format` / black | `ruff --fix I` / isort | `ruff --fix F401,F841` | `ruff E,F,B,N,UP,S,A,C90,SIM,RET` | `mypy --strict` | `radon cc -nb` | `bandit` / semgrep |
| **TypeScript/JS** | `biome format` / prettier | `biome check --apply` / `eslint-plugin-import/order` | `eslint --fix no-unused-vars,no-unused-imports` / ts-unused-exports | `biome check` / `eslint @typescript-eslint/strict` | `tsc --strict --noUncheckedIndexedAccess` | `eslint complexity` | `npm audit` / semgrep |
| **Go** | `gofmt` / `goimports` | `goimports` (built-in) | `golangci-lint unused` | `golangci-lint` (`govet,staticcheck,ineffassign,unused,gosec`) | (compile = check) | `gocyclo -over 10` | `gosec` (in golangci) |
| **Java** | `google-java-format` / spotless | spotless (importOrder) | `error-prone UnusedVariable` | spotbugs + checkstyle | `@Nullable`/`@NonNull` strict | `pmd CyclomaticComplexity` | spotbugs (FindSecBugs) |
| **Kotlin** | `ktfmt` / ktlint | ktlint (import-ordering) | `detekt UnusedImports` | `detekt` | (compile + `-Werror`) | detekt complexity rules | detekt (`detekt-formatting`) |
| **Rust** | `cargo fmt` (rustfmt) | rustfmt (built-in) | `cargo +nightly udeps` | `cargo clippy -- -D warnings` | (compile = check) | clippy `cognitive_complexity` | `cargo audit` |
| **Vue/Nuxt** | prettier + biome | biome | eslint-plugin-vue + ts-unused-exports | eslint-plugin-vue + biome | tsc + `vue-tsc` | eslint complexity | npm audit |
| **PHP** | php-cs-fixer / pint | php-cs-fixer (ordered_imports) | rector dead-code | phpstan / psalm | phpstan strict | phpmd | `composer audit` |

> **Rule**: ใช้ all-in-one tool (Ruff / Biome / golangci-lint) ดีกว่า stitch หลาย tool — boundary error น้อย, config เดียว
