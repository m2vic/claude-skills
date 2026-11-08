# SoC Architecture by Language

The layers and rules never change. This table maps them to each language. For a language not listed, use its interface mechanism for ports, its module system for layers, and `scripts/check_boundaries.py` for enforcement.

| Language | Port form | Layer unit | Wiring | Boundary tool |
|---|---|---|---|---|
| TypeScript | `interface` | folder per layer | manual, in `bootstrap` | dependency-cruiser, eslint-plugin-boundaries |
| JavaScript | JSDoc typedef plus contract tests | folder per layer | manual | dependency-cruiser, eslint-plugin-boundaries |
| Python | `typing.Protocol` | package per layer | manual, in `bootstrap` | import-linter |
| Go | small `interface` declared in `application` | package per layer under `internal/` | manual, in `cmd/<binary>` or `bootstrap` | go-arch-lint, depguard via golangci-lint |
| Java | `interface` | package per layer, or Maven/Gradle module | Spring config or manual | ArchUnit |
| Kotlin | `interface`; `fun interface` for one method | package per layer, or Gradle module | Koin, Spring or manual | Konsist, ArchUnit |
| C# | `interface` | project per layer | `Microsoft.Extensions.DependencyInjection` | project references, NetArchTest |
| Rust | `trait` | workspace crate per layer, or modules | manual, in the binary crate | crate dependencies (compiler-enforced) |
| PHP | `interface` | namespace per layer | framework container | Deptrac |
| Ruby | duck type plus shared contract examples | folder per layer | manual | Packwerk |
| Elixir | `@behaviour` | context plus module namespaces | `config`, or passed in as arguments | Boundary |
| Swift | `protocol` | SwiftPM target per layer | manual, in the app target | target dependencies (compiler-enforced) |
| C++ | abstract class or concept | CMake library per layer | manual, in `main` | CMake link dependencies |

Prefer build-level enforcement where the table offers it (crates, projects, modules, targets). A forbidden dependency then fails to compile.

## Language notes

**Go.** Standard Go project layout maps onto the shape: `cmd/<binary>/main.go` is the entry point and `internal/<capability>/{domain,application,adapters/...}` holds the rest. Declare interfaces in `application`, the consumer. Adapters return concrete types, and implicit satisfaction connects them, with `var _ application.RefundStore = (*Store)(nil)` as a compile-time check. Use `shared` sparingly because import cycles surface quickly in Go. `_test.go` files cannot be shared across packages, so shared fakes and contract suites go in `adapters/outbound/fakes` and `adapters/outbound/contract`. Run the checker on `internal`.

**Python.** Use `@dataclass(frozen=True)` for domain values and `Protocol` for ports, with fakes that implement the protocol. In FastAPI or Django, routes and views are inbound adapters. ORM models are outbound adapter code, mapped to domain types at the adapter edge.

**TypeScript.** Use `import type` for ports in `application`. Use path aliases that name the layer so boundary rules read clearly. Express, Nest and Next route handlers are inbound adapters. In Next.js, keep capability folders in `src/` outside `app/`.

**Java and Kotlin.** Keep `domain` free of Spring and JPA annotations. JPA entities live in `adapters/outbound` and map to domain types. A Spring `@Configuration` class in `bootstrap` holds the wiring.

**C#.** Use one project per layer: `Refunds.Domain`, `Refunds.Application`, `Refunds.Adapters`, and a host project that serves as bootstrap. EF Core `DbContext` belongs in adapters.

**Rust.** Use async traits at the application edge. A workspace with `domain`, `application`, `adapters` and `bin` crates gets boundaries from `Cargo.toml`. Define errors per layer and convert at the edge with `From`.

**PHP and Ruby.** In Laravel or Rails, controllers, jobs and models are adapters. Put capability folders under `src/` (PHP) or `app/<capability>/` (Rails), with Active Record or Eloquent classes only in `adapters/outbound`. Ruby has no interface keyword, so shared contract examples stand in for the port's type check.

**Elixir.** A Phoenix context is a natural `application` boundary. Controllers are inbound adapters, and Ecto schemas with `Repo` calls live in outbound adapters. Dispatch through a configured module that implements the behaviour.

**Frontend.** Use these layers only for client-side business rules, such as a pricing calculation or offline sync. Components are inbound adapters, and API clients and browser storage are outbound adapters. Presentation-only UIs take the Skip size.
