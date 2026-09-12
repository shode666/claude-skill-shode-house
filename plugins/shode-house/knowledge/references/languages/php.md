# PHP — Best Practices

> **Use cases**: Web (Laravel/Symfony), WordPress, headless CMS, e-commerce, internal tool
> **Why**: ทำเร็ว/ต้นทุนต่ำ, hosting ทุกที่, ecosystem ใหญ่

## Setup
- **Version**: 8.3+ (8.4 latest — type, perf, asymmetric visibility)
- **PM**: **Composer**
- **Lint+Format**: **PHP CS Fixer** หรือ **Pint** (Laravel)
- **Static Analysis**: **PHPStan** level 8/9 / **Psalm**
- **Test**: **PHPUnit** หรือ **Pest** (modern, expressive)

## Type Discipline (PHP 8+)
- `declare(strict_types=1);` ทุกไฟล์
- Type hint ทุก param + return
- **Readonly property** (PHP 8.1+) for immutable
- **Enum** (PHP 8.1+) — backed enum สำหรับ DB value
- **Nullable** explicit `?Type` หรือ union `Type|null`
- **First-class callable**: `$fn = strtolower(...)`
- **Property promotion** ใน constructor

## Frameworks
- **Laravel 11+** (mainstream, full-stack, eloquent, queue, broadcasting)
- **Symfony 7+** (enterprise, modular, decoupled)
- **Slim** (micro), **Mezzio** (PSR), **Hyperf** (Swoole, async)

## Frontend with PHP
- **Livewire** (reactive Laravel)
- **Inertia.js** (SPA + Vue/React)
- **Filament** (admin panel for Laravel)

## Database
- **Eloquent** (Laravel ORM)
- **Doctrine** (Symfony ORM)
- **Cycle ORM** (DataMapper)
- Migration via framework (Laravel artisan, Symfony doctrine)

## Async / Concurrency
- **Swoole** / **OpenSwoole** for true async
- **ReactPHP** for event loop
- **Fibers** (PHP 8.1+) — built-in coroutine primitive
- Job queue (Laravel Horizon, Symfony Messenger)

## Testing
- **Pest** (modern, BDD-style) > PHPUnit
- **Mockery** for mock
- **Laravel Dusk** (Selenium) for browser test

## Best Practices
- **PSR**: PSR-4 autoload, PSR-12 style, PSR-7 HTTP message, PSR-15 middleware
- File ≤ 300 lines, function ≤ 30
- Readonly DTO + value object
- Repository pattern + service layer
- Avoid Facade (Laravel) ใน core domain
- Use container (DI) > static call

## Security
- Always escape output (`htmlspecialchars`, Blade `{{ }}` auto)
- CSRF token (built-in framework)
- Prepared statement (PDO / Eloquent)
- `password_hash` + `password_verify` (bcrypt/argon2)
- Validate input (Form Request, Symfony validator)
- HTTPS-only (`secure: true` cookie)

## Composer Discipline
- `composer.lock` commit
- `composer install --no-dev --optimize-autoloader` for prod
- Pin major version (`^11.0`)
- `composer audit` for CVE check

## ห้าม
- ห้าม `eval`, `extract`, `${...}` variable variable
- ห้าม `mysql_*` (deprecated; use PDO หรือ ORM)
- ห้าม raw `$_POST` / `$_GET` → request object + validate
- ห้าม `error_reporting(0)` — fix root cause
- ห้าม `include` raw user input → path traversal
- ห้าม short tag `<?` (use `<?php`)
- ห้าม global state (use DI container)
- ห้าม `// @phpstan-ignore` โดยไม่มี ticket
