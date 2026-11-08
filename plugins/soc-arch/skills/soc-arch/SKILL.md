---
name: soc-arch
description: Use when writing a spec or implementation plan, or building or restructuring backend code, where business rules meet external systems such as databases, third-party APIs, webhooks, message queues, email or files, in any language. Also use when asked for separation of concerns, hexagonal architecture, ports and adapters, clean structure, or a codebase that is easier to navigate.
---

# SoC Architecture

Separation of concerns, enforced by folder boundaries. Each small service or business capability gets its own folder. It borrows ports and adapters from hexagonal architecture, with one difference from the classic layout: ports sit beside the use cases in `application/` rather than in a separate top-level `ports/` folder, and use cases replace generic `services/`.

Business rules sit at the center and know nothing about the outside world. Everything external plugs in through a **port** (an interface the application owns) and an **adapter** (the code that talks to the vendor, framework or protocol). Folders name business capabilities, so a reader finds code by what it does. `src/` below means the project's source root, whatever it is called: `src`, `app`, `internal`, `lib`.

Passing tests do not show the structure is sound. The Boundary Map and the boundary check do.

## The shape

```
src/
  <capability>/          one folder per business capability: refunds/, coupons/
    domain/              rules and types
    application/         use cases, plus the ports they need
    adapters/
      inbound/           HTTP, CLI, jobs, consumers: translate, then call a use case
      outbound/          Postgres, Stripe, SMTP: implement a port
  shared/                value types used everywhere, such as Money
    adapters/            technical helpers several adapters share, such as a file lock
  bootstrap/             reads config, chooses adapters, wires them together
ARCHITECTURE.md          the codemap
```

| Layer | May import | Holds |
|---|---|---|
| domain | domain, shared, standard-library basics | Rules, entities, value types, domain errors |
| application | domain, shared | One use case per file, port interfaces |
| adapters | application, domain, shared, vendor libraries | Protocol and vendor translation |
| bootstrap | everything; nothing imports it | Config, adapter choice, wiring |

Program entry points (`main`, `__main__`, `cmd/*`) sit outside the layers and do one thing: call bootstrap.

Between capabilities, one capability calls another through its own outbound port. The adapter behind that port calls the other capability's `application` layer.

## Where does this code go?

Ask in this order and stop at the first yes.

1. Reads config or chooses an implementation? **bootstrap**
2. Mentions a status code, SQL, JSON shape, SDK, framework or wire format? **adapter**
3. Would the rule still hold if the business ran on paper? **domain**
4. Sequences steps: load, decide, act, save? **application**

Recipes for the cases that most often leak:

- **Failures:** the domain defines typed errors such as `RefundWindowExpired`. The inbound adapter maps them to status codes.
- **Time and IDs:** pass `now` into domain functions. Use cases get a clock or ID port. A rule about calendar periods names its timezone in the map.
- **Transactions:** the use case states the atomic intent through a port, such as `UnitOfWork.run(fn)` or `refunds.reserve(...)`. The adapter owns `BEGIN` and `COMMIT`. Around an external call, use three steps: save the intent in a transaction, call the system with no transaction open, then save the outcome. A crash then leaves a record that can be retried.
- **Ports:** name them for the application's need, such as `RefundGateway` or `OrderLookup`, with vendor-free types. Each use case depends on the smallest port that serves it.
- **Shared data:** each capability models only the fields it needs. Two capabilities may read one table through separate adapters.
- **Schema and migrations:** ORM models and table definitions belong to outbound adapters. Migration files stay wherever the project's migration tool expects them.
- **Webhooks and message queues:** when the work receives webhooks, consumes or publishes messages, or runs background jobs, read [references/webhooks-and-queues.md](references/webhooks-and-queues.md) before writing the map. It links a runnable example.
- **What gets a port:** anything crossing a process boundary or varying between runs. In-process collaborators are called directly.

## Steps

### 1. Choose the size

| What you observe | Size |
|---|---|
| Business rules and at least one external system | **Full** |
| Pure pass-through CRUD with no rules yet | **Thin**: `adapters/inbound` calls a repository port, wired in bootstrap. Add `domain/` with the first rule. Thin needs one adapter test against the real store and a short codemap entry, and no fake, contract suite or map tables |
| Script, prototype, pure library, or UI with no business rules | **Skip** this skill and say why |

Done when the size is stated in the spec or plan.

### 2. Survey the codebase

| What you find | What to do |
|---|---|
| Greenfield | Use the shape above |
| Existing ports-and-adapters or similar layering | Keep its folder names and record the layer mapping in the map |
| Legacy code without layers | Build the new capability in its own layered folder beside it. Legacy functions, ORM bases and sessions it needs are imported only by outbound adapters. In legacy files, only wiring lines change. Bootstrap may live inside the new capability until a second one exists |
| Framework dictates file locations (Rails, Django, Next.js) | Framework files are inbound or outbound adapters and stay thin. The layered capability code lives in its own folder |

Read [references/languages.md](references/languages.md) for the target language's layout, port form and enforcement tool.

Done when the source root is named and every existing file this work touches has a layer or is marked legacy.

### 3. Write the Boundary Map

Write this before any task list. During `superpowers:brainstorming` it goes in the design doc. During `superpowers:writing-plans` it replaces the free-form File Structure and goes under **Global Constraints**, because implementers see only their own task. With no spec or plan, put it in `ARCHITECTURE.md`.

```markdown
## Boundary Map
Size: Full
Layer folders: domain, application, adapters/inbound, adapters/outbound, bootstrap

| Capability | Use case | Rules (domain) | Ports needed |
|---|---|---|---|
| refunds | request_refund | 30-day window, refundable status, amount cap | OrderLookup, RefundStore, RefundGateway, Notifier, Clock |
| refunds | retry_failed_refunds | none | RefundStore, RefundGateway, Notifier |

| Port | Adapter | Touches | Fake for tests |
|---|---|---|---|
| RefundGateway | adapters/outbound/http_refund_gateway | payment provider | FakeRefundGateway |
| RefundStore | adapters/outbound/sqlite_refund_store | `refunds` table (PENDING, COMPLETED, FAILED) | InMemoryRefundStore |

| Entry point | Inbound adapter | Calls |
|---|---|---|
| POST /orders/{id}/refunds | adapters/inbound/http_refunds | request_refund |
| nightly job | adapters/inbound/cli_retry | retry_failed_refunds |
```

Done when every requirement appears in a row, every rule has one home, and every external system has a port.

### 4. Order the tasks inside-out

Each task stays within one layer of one capability, except where noted.

1. Skeleton: folders, a boundary check that runs in CI, and `ARCHITECTURE.md`
2. Domain rules: plain values, no fakes
3. Use cases and ports, with in-memory fakes
4. Outbound adapters, with contract tests
5. Inbound adapters
6. Bootstrap, plus one end-to-end test across all layers

Every task's **Interfaces** block names its ports exactly. Every task ends by running the boundary check alongside its tests.

Done when each task's files all sit in the layer that task names.

### 5. Test each layer at its own seam

| Layer | Test with |
|---|---|
| domain | Plain values, in milliseconds, with no mocks |
| application | In-memory fakes behind the real ports |
| outbound adapter, port that holds state or moves money | One contract suite, run against both the fake and the real adapter |
| outbound adapter, other ports (clock, notifier, read-only lookup) | One direct test of the adapter |
| inbound adapter | Input to use case call, result or error to response |
| whole system | A small number of end-to-end tests through bootstrap |

Fakes implement the same port as the real adapter and live with the tests, or in a test-support package where the language needs one to share them.

**Under a deadline**, build fewer capabilities and use cases. The map, the domain tests, the boundary check and the fakes for the use cases you build stay in. End-to-end coverage may shrink to one happy path.

### 6. Enforce the boundaries

Use the language's boundary tool if the project already has one. Otherwise copy [scripts/check_boundaries.py](scripts/check_boundaries.py) into the repo and run it with Python 3:

```bash
python3 scripts/check_boundaries.py src
```

Pass the project's source root. The script reads imports in most languages, exits non-zero on a violation, and also fails when it finds no layer folders. It needs Python 3 at development time only. Optional `.soc-arch.json` settings, including folder-name mappings for existing layouts, are described at the top of the script.

An implementer whose code does not fit the map updates the map in the plan and reports the change, then puts the code where the updated map says.

Done when the check passes and runs automatically: in CI, in a pre-commit hook, or, where neither exists, as a test in the project's suite.

### 7. Write the codemap

`ARCHITECTURE.md` tells an agent where to start reading. Add a pointer to it in `AGENTS.md` or `CLAUDE.md`.

```markdown
# Architecture
SoC architecture: one folder per capability. Dependencies point inward. Check: `python3 scripts/check_boundaries.py src`

## Capabilities
- refunds: customer refunds. Use cases: request_refund, retry_failed_refunds

## Find it fast
- A business rule: `src/<capability>/domain/`
- What a feature does, step by step: `src/<capability>/application/<use_case>`
- An endpoint or job: `src/<capability>/adapters/inbound/`
- A vendor or database: `src/<capability>/adapters/outbound/`
- Which adapter is live: `src/bootstrap/`

## Ports
| Port | Live adapter | Fake |
```

Done when every capability, use case and port in the map appears here.

## Naming for navigation

- Capability: business noun (`refunds`), never a technical role.
- Use case: verb phrase, one per file (`request_refund`).
- Port: the role it plays (`RefundGateway`).
- Adapter: technology plus port (`StripeRefundGateway`).
- Modules named `utils`, `helpers`, `common`, `manager` or `service` become precise names in the layer that owns the code.

## Review checklist

Run this before calling the work complete. Each failure names its fix.

- [ ] Boundary check passes. Fix: move the import outward, behind a port.
- [ ] Domain tests start no database, server or network. Fix: move I/O out of the rule.
- [ ] Inbound adapters hold no rules: each parses, calls one use case and formats. Fix: move the logic inward.
- [ ] Adapters are constructed only in bootstrap. Fix: inject them.
- [ ] Every port has the tests step 5 assigns it. Fix: add them.
- [ ] `ARCHITECTURE.md` matches the code. Fix: update it.
