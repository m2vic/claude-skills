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

## What testing showed so far

These are small tests on Go tasks, with hidden behaviour tests and one blind AI reviewer, so treat the numbers as a first signal rather than proof.

**simple-code, compared with no skill**
- On 4 everyday Go tasks, the code was about 25% shorter (254.5 against 338 lines in total), and every hidden test passed on both sides.
- A blind reviewer preferred the code with the skill in 6 of 8 pairs, called 2 a tie, and preferred the code without it in none.
- On messy CSV input, the code with the skill was sometimes stricter, for example rejecting a file that starts with a byte order mark.

**Both skills together, on backend services**
- Every hidden test passed (60 of 60), with about 25% less production code than `soc-arch` alone.
- It was still about twice the size of `simple-code` alone.
- On a small shop backend, the reviewer preferred no skills if the shop stays small, and both skills if it grows a lot, in both runs. The code was 26% bigger with both skills.
- One both-skills run could charge the same cart twice when two checkouts arrived at the same moment. Whatever you use, test concurrency and crash recovery yourself.

## Known gaps

- Neither skill says how it relates to the other. When both are on, agents have so far treated `soc-arch` as the chosen design and applied `simple-code` inside it.
- `simple-code` sometimes trims `soc-arch` steps, such as a clock port and its adapter test.
- Results come from a small number of runs in Go only.

## License

MIT
