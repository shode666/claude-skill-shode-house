# C++ — Best Practices

> **Use cases**: Performance-critical, embedded, finance/trading, game engine, system programming
> **Why**: Low-level + perf, ใช้กับระบบที่ Rust ยังไม่ครอบ

## Setup
- **Standard**: C++20 (default), C++23 (latest)
- **Compiler**: GCC 13+, Clang 17+, MSVC 19.40+
- **Build**: **CMake 3.27+** + **Ninja** generator
- **PM**: **Conan 2** หรือ **vcpkg**
- **Lint**: **clang-tidy** + **cppcheck**
- **Format**: **clang-format** (Google/LLVM/custom style)
- **Sanitizer**: AddressSanitizer (ASan), UBSan, ThreadSanitizer (TSan), MemorySanitizer

## Modern C++ Discipline
- **RAII** (Resource Acquisition Is Initialization) — destructor cleanup
- **Smart pointer**: `unique_ptr` (default) > `shared_ptr` (refcount cost)
- **No raw `new`/`delete`** ใน application (use smart pointer + container)
- **`auto`** for type inference (when obvious)
- **`constexpr`** / **`consteval`** for compile-time
- **`if constexpr`** for template branching
- **Concepts** (C++20) for template constraint
- **Ranges** (C++20) > raw iterator
- **`std::span`** for view of contiguous data
- **`std::optional`** for nullable
- **`std::variant`** for type-safe union
- **`std::format`** (C++20) > printf/cout

## Concurrency (C++20+)
- **`std::jthread`** (auto-join, cancellable) > `std::thread`
- **`std::stop_token`** for cooperative cancel
- **`std::atomic<T>`** for lock-free
- **Coroutine** (C++20 — co_await, co_yield)
- **Executor** (Senders/Receivers, P2300, C++26)
- Thread pool library (Folly, oneTBB)

## Library Choice
- **fmt** (or std::format C++20)
- **spdlog** for logging
- **nlohmann::json** for JSON
- **Boost** subset (network, asio, beast)
- **Qt** for cross-platform GUI
- **gRPC + Protobuf** for RPC
- **GoogleTest + GoogleMock** for test

## Performance
- **Profile first** (`perf`, **Tracy**, Intel VTune)
- **Cache-friendly data layout** (struct of array vs array of struct)
- **Move semantic** > copy (use `std::move`)
- **Reserve container** ก่อน push_back (avoid reallocation)
- **`std::string_view`** for non-owning string
- **Const correctness** everywhere

## Build / CMake
- **Modern CMake** (3.20+, target-based)
- **CMakePresets.json** for config
- **find_package** + **FetchContent** for deps
- **ccache** + **distcc** for fast rebuild
- **Module** (C++20) — slowly adopted

## Testing
- **GoogleTest + GoogleMock** (default)
- **Catch2** (header-only, modern)
- **doctest** (lightweight)
- **CTest** for runner

## Best Practices
- **Core Guidelines** (Stroustrup, Sutter) — follow แทน C++98 habit
- File ≤ 500 lines, function ≤ 50
- Header guard / `#pragma once`
- Forward declaration > include header
- Avoid macro (use constexpr / inline function)
- `noexcept` for moves, swap, simple getter
- Rule of zero/three/five (default → 3 → 5)

## Safety
- **Sanitizer ทุก commit** (ASan + UBSan)
- **Static analysis** (clang-tidy strict + clang-analyzer)
- **Fuzzing** (libFuzzer, AFL++)
- Bound check (`at()` > `[]` for safety; `[]` for perf hot path)

## ห้าม
- ห้าม raw `new`/`delete` (smart pointer + container)
- ห้าม raw C-style cast (use `static_cast`/`reinterpret_cast`/etc.)
- ห้าม `goto`
- ห้าม global mutable state
- ห้าม `using namespace std;` ใน header (or top of file)
- ห้าม macro for constant (use `constexpr`)
- ห้าม `printf` family (use `std::format`/fmt)
- ห้าม dangling pointer / use-after-free (sanitizer + RAII)
- ห้าม `volatile` for thread sync (use atomic)
