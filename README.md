# claude-skills

Two Claude Code skills:

- **simple-code** makes the agent write the simplest readable code that does the job, without extra layers or abstractions.
- **soc-arch** gives backends a clear structure: business rules in the middle, with ports and adapters for databases, APIs and files. It includes a script that checks imports stay within their layers.

## Install

```
/plugin marketplace add m2vic/claude-skills
/plugin install simple-code@m2vic-skills
/plugin install soc-arch@m2vic-skills
```

Or copy the skill folders into `~/.claude/skills/`:

```
git clone https://github.com/m2vic/claude-skills
cp -r claude-skills/plugins/simple-code/skills/simple-code ~/.claude/skills/
cp -r claude-skills/plugins/soc-arch/skills/soc-arch ~/.claude/skills/
```

## Which to use

- **Small project that will stay small:** `simple-code` alone.
- **Backend that will grow:** both skills. `soc-arch` sets the structure, and `simple-code` keeps the code inside it plain.

## Test results

**Setup.** An agent built a small shop backend in Go (carts, coupons, checkout with a payment provider, concurrent requests). It followed the [superpowers](https://github.com/obra/superpowers) 7.0.0 workflow: design, plan, then test-first code. There were 3 setups with 5 runs each. For each comparison, 3 AI reviewers judged every pair without knowing which setup wrote which version.

| | superpowers only | + `simple-code` | + `simple-code` + `soc-arch` |
|---|---|---|---|
| Hidden tests passed (17) | all runs | all runs | all runs |
| Code lines (average) | 550 | **396** | 848 |
| Go files (average) | 6.4 | **3.4** | 20.6 |
| Time per run (average) | **5.8 min** | 7.5 min | 10.2 min |
| Huge quantity makes the cart total wrap around | 1 of 5 runs | **0 of 5** | **0 of 5** |
| Crash during payment: unsafe recovery, so a retry can charge twice | 5 of 5 runs | **0 of 5** | **0 of 5** |

The last two rows come from extra tests run on every shop, outside the hidden tests.

**Blind review against superpowers only (15 verdicts each).** The first two columns show how often each setup was preferred.

| | If the shop stays this size | If the shop grows | Readability (1-5) | Moving to Postgres (1-5) |
|---|---|---|---|---|
| + `simple-code` | **9 of 15** | 0 of 15 | **4.1** vs 3.8 | 2.0 vs 3.7 |
| + `simple-code` + `soc-arch` | 6 of 15 | **15 of 15** | 3.5 vs 3.9 | **3.7** vs 2.0 |

- **Both skills is the clear choice for a backend that will grow.** All 15 verdicts preferred it.
- **For a small shop, `simple-code` alone has a modest edge.** It had the least code and the best readability, but reviewers often disagreed on the same pair.
- **For a small shop, both skills is too much.** It won only the 2 pairs where the superpowers-only shop had a serious bug.

## Known gaps

- **Bugs every setup still left in some runs:**
  - reading a request body while holding the global lock
  - keeping a change in memory after the save to disk failed
  - crashing when a product is missing from the data file
- **Limited evidence:** one task, Go only, AI reviewers only.

## License

MIT
