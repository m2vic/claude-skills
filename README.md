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

### 4. Inside a superpowers workflow

This test checks whether the skills still help when you already plan and build with [superpowers](https://github.com/obra/superpowers) 7.0.0. Every run followed superpowers: brainstorm a design, write a plan, then build it test-first. There were three setups, each with 2 runs per task:

- superpowers only
- superpowers + `simple-code`
- superpowers + `simple-code` + `soc-arch`

The skills were read before brainstorming, so they shaped the design and the plan as well as the code. No human answered superpowers' questions: each run made the choice itself and logged it. The tasks were the sales CSV summary from test 1 and the shop backend from test 3.

**Sales CSV summary (a small library function)**

| Measure | superpowers only | + `simple-code` | + `simple-code` + `soc-arch` |
|---|---|---|---|
| Hidden tests passed | 12/12 each | 12/12 each | 12/12 each |
| Code lines (average) | 134.5 | **111** | 145 |
| Most complex function (average) | 15.5 | **9** | **9** |
| Design and plan doc lines (average) | 155.5 | **105** | 148 |
| Time per run (average) | 3.2 min | **2.3 min** | 3.2 min |

**Shop backend**

| Measure | superpowers only | + `simple-code` | + `simple-code` + `soc-arch` |
|---|---|---|---|
| Hidden tests passed | 17/17 each | 17/17 each | 17/17 each |
| Production code lines (average) | 559.5 | **383.5** | 769 |
| Go files (average) | 7 | **3** | 21.5 |
| Boundary check | Not applicable | Not applicable | Pass, both runs |
| Design, plan and architecture doc lines (average) | 191 | **134.5** | 313 |
| Time per run (average) | **5.7 min** | 7.1 min | 9.8 min |
| Same cart checked out twice at once | Charged once | Charged once | Charged once |
| Item added while payment is running | Rejected | Rejected | Rejected |
| Huge quantity (2^63 - 1) added to a cart | **Rejected, both runs** | Accepted, both runs, and the total wraps to 500 | Accepted in 1 of 2 runs |
| Server crashes during payment | Stock returned, though the charge may have gone through | Stock stays taken, and a retry can charge again | Stock stays taken, and the cart stays locked |

**Blind review.** One AI reviewer compared each setup against superpowers only, pair by pair, without knowing which version was which. The two comparisons were scored by separate reviewers.

| Compared with superpowers only | Sales: preferred if it stays this size | Sales: preferred if it grows | Shop: preferred if it stays this size | Shop: preferred if it grows | Shop: big change, such as moving to Postgres (1-5) |
|---|---|---|---|---|---|
| + `simple-code` | **2 of 2** | **2 of 2** | 1 of 2 | 0 of 2 | 2.0 against 3.5 |
| + `simple-code` + `soc-arch` | **2 of 2** | **2 of 2** | 0 of 2 | **2 of 2** | **4.0** against 2.0 |

What this shows:

- **On a small function, both setups beat superpowers alone in every pair.** `simple-code` on its own gave the shortest code and plans. With `soc-arch` added, the runs correctly skipped the layered folders for a one-file library, but the code was a little longer than superpowers alone.
- **On the shop, it's a trade-off between today and later.** Adding `simple-code` alone gave the smallest shop, but the hardest one to move to a database. Adding both gave the shop the reviewer preferred for growth in both runs, at the cost of about 37% more code, more than twice the docs and the slowest runs. For a shop that stays this size, the reviewer preferred superpowers alone in both runs.
- **Neither skill fixes the crash-during-payment problem.** Each setup fails in a different way.
- **The `simple-code` runs dropped an input-limit check.** 3 of the 4 shop runs that used `simple-code` accepted a quantity so large that the cart total wrapped around. Both superpowers-only runs caught it during their own review.

**After fixing those two gaps.** `simple-code` now has two more rules: check numbers from a request against their limit before doing arithmetic with them, and decide what a restart does in the middle of a change that calls something external. The second rule says to keep a half-finished order blocked and visible, not to undo it or reopen it. Then I reran the shop 2 more times with each setup that uses `simple-code`. superpowers only was not rerun, because the fix does not touch it.

| Shop, after the fix | superpowers only (unchanged) | + `simple-code` | + `simple-code` + `soc-arch` |
|---|---|---|---|
| Hidden tests passed | 17/17 each | 17/17 each | 17/17 each |
| Production code lines (average) | 559.5 | **394** (was 383.5) | 825 (was 769) |
| Go files (average) | 7 | **3.5** | 21 |
| Boundary check | Not applicable | Not applicable | Pass, both runs |
| Time per run (average) | **5.7 min** | 8.4 min (was 7.1) | 9.7 min (was 9.8) |
| Huge quantity (2^63 - 1) added to a cart | Rejected, both runs | **Rejected, both runs** | **Rejected, both runs** |
| Server crashes during payment | Stock returned, though the charge may have gone through | **Order stays pending and the cart stays locked, both runs. Startup logs how many are pending** | **Same, both runs** |
| Same cart checked out twice / item added during payment | Charged once / rejected | Charged once / rejected | Charged once / rejected |

Both gaps are closed in all 4 new runs, and each run wrote its own test for both of them. It cost about 10 extra lines with `simple-code` alone. One run with both skills added its own error code, `checkout_in_progress`, for a cart whose payment is still in progress; the task did not define one. 

**Blind review after the fix.** The new shop runs were compared with the same superpowers-only runs, again by two separate reviewers who did not know which version was which:

| Compared with superpowers only | Shop: preferred if it stays this size | Shop: preferred if it grows | Shop: big change (1-5) |
|---|---|---|---|
| + `simple-code` | **2 of 2** (was 1 of 2) | 1 of 2 (was 0 of 2) | 2.5 against 3.5 |
| + `simple-code` + `soc-arch` | **2 of 2** (was 0 of 2) | **2 of 2** (was 2 of 2) | **4.0** against 2.0 |

- **Small shop:** with `simple-code` alone, the reviewer called it the quickest to read in both pairs (readability 5 against 4 in each).
- **Both skills:** the reviewer found a confirmed bug in each superpowers-only shop and none of the same weight in the both-skills shops.

Treat the "stays this size" result for both skills with care. My first attempt at this review gave the reviewer copies with the `cmd/server` folder missing on both sides, which was my mistake. On those copies, a different reviewer preferred superpowers alone for a small shop in both pairs. The "if it grows" answer was the same both times. One reviewer per comparison is noisy.

**Larger rerun: 5 shops per setup, 3 reviewers per comparison.** Because two pairs and one reviewer gave unstable answers, I built 3 more shops with each setup, so each setup has 5. Then 3 separate blind reviewers judged all 5 pairs for each comparison, with A and B shuffled separately for each reviewer. That gives 15 verdicts per question. This supersedes the two smaller review tables above.

| Shop, 5 runs per setup | superpowers only | + `simple-code` | + `simple-code` + `soc-arch` |
|---|---|---|---|
| Hidden tests passed | 17/17 each | 17/17 each | 17/17 each |
| Production code lines (average) | 550 | **396** | 848 |
| Go files (average) | 6.4 | **3.4** | 20.6 |
| Time per run (average) | **5.8 min** | 7.5 min | 10.2 min |
| Huge quantity accepted (total wraps around) | 1 of 5 runs | **0 of 5** | **0 of 5** |
| Server crashes during payment | 5 of 5 return the stock and reopen the cart, so a retry can charge twice | **5 of 5 keep the order pending and the cart locked** | **5 of 5 keep the order pending and the cart locked** |

| Compared with superpowers only (15 verdicts each) | Preferred if it stays this size | Preferred if it grows | Readability (1-5) | Big change (1-5) |
|---|---|---|---|---|
| + `simple-code` | **9 of 15** | 0 of 15 | **4.1** against 3.8 | 2.0 against 3.7 |
| + `simple-code` + `soc-arch` | 6 of 15 | **15 of 15** | 3.5 against 3.9 | **3.7** against 2.0 |

What this shows:

- **If the shop will grow, use both skills.** All 15 verdicts preferred it, and all 3 reviewers agreed on every pair.
- **For a shop that stays small, `simple-code` alone has a modest edge.** It won 9 of 15, with the best readability and the least code. Reviewers often disagreed on the same pair, so this lead is smaller than it looks.
- **For a small shop, both skills is not the better pick.** It won 6 of 15, and only in the 2 pairs where the superpowers-only shop had a serious bug (a quantity overflow in one, a global lock held while reading request bodies in the other). In the other 3 pairs, all 3 reviewers preferred superpowers alone.
- **`simple-code` alone is the hardest to grow.** It never won "if it grows", because its single package lets HTTP handlers change the data directly.
- **Bugs that remain in some runs of every setup:** reading a request body while holding the global lock, keeping a change in memory after the save to disk failed, and crashing when a product is missing from the data file.

## Known gaps

- Neither skill says how it relates to the other. When both are on, agents have so far treated `soc-arch` as the chosen design and applied `simple-code` inside it.
- `simple-code` sometimes trims `soc-arch` steps, such as a clock port and its adapter test.
- Crash recovery and limits on huge numbers were missing before the rules above were added; with the fix they held in 4 of 4 runs. Other safety checks nobody asked for may still be trimmed.
- Results come from a small number of runs in Go only.

## License

MIT
