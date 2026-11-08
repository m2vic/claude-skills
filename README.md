# claude-skills

Two Claude Code skills you can install and try:

- **simple-code** makes the agent write the simplest, most readable code that does the job. It cuts extra layers, abstractions and code that doesn't change the output.
- **soc-arch** gives backends a clear structure: business rules in the middle, with ports and adapters for databases, APIs, webhooks, queues and files. It includes a boundary checker script.

They can be used alone or together. Used together, `soc-arch` sets the structure and `simple-code` keeps the code inside it small and plain.

## Install

In Claude Code:

```
/plugin marketplace add m2vic/claude-skills
/plugin install simple-code@m2vic-skills
/plugin install soc-arch@m2vic-skills
```

Install one or both. Restart Claude Code if a skill doesn't show up straight away.

Without the plugin system, copy a skill folder into `~/.claude/skills/`:

```
git clone https://github.com/m2vic/claude-skills
cp -r claude-skills/plugins/simple-code/skills/simple-code ~/.claude/skills/
cp -r claude-skills/plugins/soc-arch/skills/soc-arch ~/.claude/skills/
```

## Test results

All tests used Go. Each setup was run more than once on the same task. Hidden tests checked behaviour over the code's real interface. One AI reviewer then scored the code without being told which setup wrote it. **Treat these numbers as a first signal, not proof:** the samples are small, there was one reviewer, and only one language.

### 1. `simple-code` compared with no skill

4 everyday tasks (pricing rules, a sales CSV summary, a retry helper, signup validation), 2 runs per side.

| Measure | With `simple-code` | No skill |
|---|---|---|
| Hidden tests passed | 122/122 | 122/122 |
| Code lines (sum of the 4 task averages) | **254.5** | 338 |
| Functions | **12.5** | 20 |
| Added types | **0** | 1.5 |
| Readability (1-5) | **4.50** | 3.88 |
| Ease of the next change (1-5) | **4.75** | 4.62 |
| Extra code is justified (1-5) | **4.62** | 3.38 |
| Reviewer preferred | **6 of 8** | 0 of 8 (2 ties) |

| Task | Code lines with `simple-code` | Code lines with no skill | Shorter by |
|---|---|---|---|
| Pricing | 34.5 | 42.5 | 19% |
| Sales CSV | 111.5 | 165 | 32% |
| Retry | 24.5 | 27.5 | 11% |
| Signup | 84 | 103 | 18% |
| **Total** | **254.5** | **338** | **25%** |

On prompts that invited extra features, the code was 33% shorter (316 lines against 471). On messy CSV files, for example one with a byte order mark or a capitalised header, the `simple-code` version returned an error where the no-skill version still worked.

### 2. Using the skills alone and together

2 backend tasks (refunds with a payment provider, and subscriptions with webhooks and email), 2 runs per setup.

| Measure | `simple-code` only | Both | `soc-arch` only |
|---|---|---|---|
| Hidden tests passed | 60/60 | 60/60 | 60/60 |
| Boundary check | Not applicable | 4/4 pass | 4/4 pass |
| Production code lines | **532.5** | 1,055.5 | 1,402 |
| Production Go files per task | **1.5** | 9.75 | 12.75 |
| Interfaces per task | **0** | 2.75 | 5.5 |
| Readability (1-5) | **5.00** | 4.25 | 3.00 |
| Rules kept apart from outside systems (1-5) | 2.00 | 4.75 | **5.00** |
| Big change, such as moving to Postgres (1-5) | 2.25 | 4.00 | **4.75** |
| Structure is needed (1-5) | **5.00** | 4.25 | 2.50 |
| Reviewer's first choice | 0 of 4 | 2 of 4 | 2 of 4 |

Using both kept the `soc-arch` structure with about 25% less code than `soc-arch` alone. The reviewer was asked which code they'd rather own as it grows, which favours more structure, so `simple-code` alone came last every time.

### 3. Small shop backend: both skills compared with no skills

One task: products, carts, coupons, shipping, stock, checkout through a payment provider, and data saved to a file. 2 runs per side.

| Measure | Both skills | No skills |
|---|---|---|
| Hidden tests passed | 17/17 | 17/17 |
| Production code lines | 740 | **589** |
| Production Go files | 16.5 | **6.5** |
| Test lines | **566** | 172 |
| Readability (1-5) | 4.0 | 4.0 |
| Rules kept apart from outside systems (1-5) | **5.0** | 3.5 |
| Big change, such as moving to Postgres (1-5) | **4.0** | 2.5 |
| Preferred if the shop stays this size | 0 of 2 | **2 of 2** |
| Preferred if the shop grows a lot | **2 of 2** | 0 of 2 |

| Check | Both, run 1 | Both, run 2 | None, run 1 | None, run 2 |
|---|---|---|---|---|
| Same cart checked out twice at once | Charged once | **Charged twice** | Charged once | Charged once |
| Item added while payment is running | Rejected | **Accepted** | Rejected | Rejected |
| Server crashes during payment | **Cart stuck, stock lost** | **Stock lost** | Order failed, stock returned | Order failed, stock returned |

Neither skill makes code safe under concurrency or crashes. Whatever you use, test those yourself.

### 4. Inside a superpowers workflow: superpowers + `simple-code` compared with superpowers alone

Each run followed [superpowers](https://github.com/obra/superpowers) 7.0.0: brainstorm a design, write a plan, then build it test-first. The `simple-code` runs read the skill before brainstorming and applied it to the design, the plan and the code. There were 2 tasks, the sales CSV summary and the shop backend from test 3, with 2 runs per side. No human answered superpowers' questions: each run made the choice itself and logged it.

| Measure | Sales: superpowers + `simple-code` | Sales: superpowers only | Shop: superpowers + `simple-code` | Shop: superpowers only |
|---|---|---|---|---|
| Hidden tests passed | 12/12 each | 12/12 each | 17/17 each | 17/17 each |
| Code lines (average) | **111** | 134.5 | **383.5** | 559.5 |
| Go files (average) | 1 | 1 | **3** | 7 |
| Most complex function (average) | **9** | 15.5 | 12 | 12 |
| Design and plan doc lines (average) | **105** | 155.5 | **134.5** | 191 |
| Readability (1-5) | **5.0** | 3.5 | 4.0 | 4.0 |
| Small change (1-5) | **5.0** | 4.0 | 3.5 | **4.0** |
| Big change, such as moving to a database (1-5) | **4.0** | 2.5 | 2.0 | **3.5** |
| Design and plan docs are useful (1-5) | **4.0** | 3.5 | 3.5 | **4.5** |
| Preferred if it stays this size | **2 of 2** | 0 of 2 | 1 of 2 | 1 of 2 |
| Preferred if it grows a lot | **2 of 2** | 0 of 2 | 0 of 2 | **2 of 2** |
| Time per run (average) | 2.3 min | 3.2 min | 7.1 min | 5.7 min |

| Shop check | + `simple-code`, run 1 | + `simple-code`, run 2 | superpowers only, run 1 | superpowers only, run 2 |
|---|---|---|---|---|
| Same cart checked out twice at once | Charged once | Charged once | Charged once | Charged once |
| Item added while payment is running | Rejected | Rejected | Rejected | Rejected |
| Server crashes during payment | **Stock stays taken** | **Stock stays taken** | Stock returned | Stock returned |

With `simple-code`, the code was 17% shorter on the sales task and 31% shorter on the shop, and the design and plan were about 30% shorter. Every hidden test passed on both sides, and none of the four shops sold more than the stock or charged twice. On the small sales task the reviewer preferred the `simple-code` version every time. On the shop, the superpowers-only versions were easier to grow, because they split storage, rules and HTTP into separate packages.

Neither side recovers from a crash during payment safely. The `simple-code` runs leave the stock taken, and a retry can charge the customer again. The superpowers-only runs give the stock back even though the charge may have gone through. The reviewer also found that one `simple-code` shop could freeze the whole server if someone removed a product from the data file by hand while it was still in a cart.

## Known gaps

- Neither skill says how it relates to the other. When both are on, agents have so far treated `soc-arch` as the chosen design and applied `simple-code` inside it.
- `simple-code` sometimes trims `soc-arch` steps, such as a clock port and its adapter test.
- `simple-code` can leave out crash recovery nobody asked for. Both shop runs inside superpowers left stock stuck after a crash during payment.
- Results come from a small number of runs in Go only.

## License

MIT
