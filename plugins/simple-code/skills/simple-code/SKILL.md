---
name: simple-code
description: Write the simplest, most human-readable code that produces the required output, and strip out complicated logic, abstractions and extras that do not change that output. Use this whenever you write, extend or refactor code in any language, even if the user only says "build", "implement" or "add", and especially when they ask for code that is simple, readable, clean, maintainable, easy to understand, or not over-engineered, or complain that AI code is too complicated. Also use it when a request says "production-ready", "scalable" or "future-proof", so those goals get met with the least code rather than with extra layers.
---

# Simple Code

Two programs that give the same output are not equal: the one a person understands faster is better. Every class, helper, parameter and layer is something the next reader has to learn, so each one has to earn its place by changing what the program does.

The goal is code a new teammate can read top to bottom once, explain, and safely change.

## How to work

1. **State the job.** What goes in, what comes out, which rules and edge cases were asked for, and any quality goal or design the user named. All of these are requirements. Work from this list, not from what the code might need someday.
2. **Write the boring version first.** Plain functions, `if` statements, loops and literal data, in the order a person would describe the steps. This is the design you keep unless it fails a stated requirement.
3. **Run the delete test.** For each class, helper, parameter, constant, import, branch and `try`: remove it in your head. If every stated requirement, including quality goals, is still met, remove it for real.
4. **Test it and keep the test.** Cover every stated rule and edge case in a small, plain test file beside the code, following the project's conventions, unless the user says not to. Tests show the next reader what the rules are and make changes safe, so they are part of the job and not an extra.
5. **Report plainly.** Say what you built. If you deliberately left something out, name it in one line ("No CLI or logging, since neither was requested"), so the user can ask for it.

## What simple looks like

**Build for today's requirements.** A passing "we might add more later" is not a feature to build now. Simple code is the easiest code to extend, because there is nothing to work around. Adding a coupon should mean adding a line, not first learning a framework.

**Meet stated quality goals in the simplest way.** When a request says "production-ready", "robust", "scalable" or "enterprise-grade", ask what could really go wrong with this code in use, then handle those things directly: bad input is rejected, failures are visible, nothing is lost silently, money comes out right to the cent. These words call for that care. They do not call for layers, plugin systems or frameworks.

**Deliver a design the user asks for.** When someone asks for an architecture or a specific structure, give them one in its smallest useful form, and don't reply that it should wait. If more forms are coming, for example, the design might be shared check functions that the next form reuses, with a line on how to add one. Stop short of an engine that only imagined cases would need.

**Use the plainest construct that works**, in roughly this order:

- a value or a literal dict before a config system
- `if`/`elif` or a lookup dict before a registry, strategy, factory or plugin system
- a function before a class or a struct with methods; add one only when it holds state that several operations share
- a concrete type before an interface or generics; add those only when two real implementations or types need them today
- sequential code before goroutines and channels, unless concurrency is the requirement
- standard library and helpers already in the project before a new dependency

**Keep the flow straight.** Return early instead of nesting; more than about three levels deep usually means the flow can be flattened. Do one thing per line. Prefer a readable loop to a nested comprehension, chained ternaries, `reduce`, or a clever regex. Avoid metaprogramming, reflection and custom decorators unless the task is specifically about them.

**Let small repetition stand.** Three similar lines are often clearer than a helper with flags. Extract a function when it gives a real idea a good name or when the logic must stay in sync, not merely because two lines look alike. Do not add parameters that only one caller uses or that nobody asked for.

**Name things for a human.** Use full, ordinary words (`shipping_fee`, not `sf` or `FeeCalculationContext`). A good name removes the need for a comment.

**Comment only the why.** Note a surprising rule or constraint. Skip comments that repeat the code, section banners, and long docstrings that restate the signature.

**Handle the failures that can happen, and fail loudly.** Validate what the requirements or a real boundary (user input, network, files) demand, and return a clear error for bad input instead of producing a plausible wrong answer. If code skips or drops data, make that visible to whoever runs it, for example with a count in a log line. Do not catch an exception just to re-raise it, and do not guard against states the code cannot reach.

**Add no extras.** No CLI, logging, config, retries, caching, metrics, or type hierarchies unless they were asked for, or the job or a stated goal cannot be met without them. Code that runs unattended, for example, needs some way to report problems.

## When changing existing code

Follow the project's conventions and make the smallest change that does the job. Do not restructure neighbouring code or introduce a new pattern in passing. Keep working complicated code unless simplifying it is the task or your change requires it; if it looks removable, mention that instead.

## What simple does not mean

Never give up any of these to save lines:

- Correct behaviour, including every stated rule and edge case
- Security: input validation at trust boundaries, safe queries, no secrets in code
- Accuracy that matters: money must come out right to the cent, including half-cent cases, and a test should prove it. Use the plainest method that does this. A float with a small rounding helper that clears binary noise is fine when prices have a few decimals and a float crosses the function boundary anyway. Reach for integer cents or exact fractions such as `big.Rat` only when a stated rule needs them, or when a test shows the simpler method gets a result wrong
- Performance the task has actually asked for or a measurement has shown to matter
- An abstraction the user explicitly requested; build it, in its simplest form

Fewer lines is not the goal either. Code golf is as hard to read as over-engineering, so prefer the longer version when it is clearer. One long function that does everything is not simple: when a function mixes distinct steps such as reading, parsing and summarizing, give each step a well-named function. When a problem has real complexity, keep it, isolate it in one well-named place, and explain why in a short comment.

## Example

Task: apply a member discount, and charge 5 shipping on orders under 50.

Avoid this. It gives the same output with far more to read:

```go
type DiscountStrategy interface {
	Apply(amount float64) float64
}

type MemberDiscount struct{}

func (MemberDiscount) Apply(amount float64) float64 {
	return amount * 0.95
}

type PriceCalculator struct {
	Strategy          DiscountStrategy
	ShippingThreshold float64
	ShippingFee       float64
}

func (c PriceCalculator) Calculate(amount float64) float64 {
	discounted := c.Strategy.Apply(amount)
	if discounted < c.ShippingThreshold {
		return discounted + c.ShippingFee
	}
	return discounted
}
```

Write this:

```go
func FinalPrice(amount float64, isMember bool) float64 {
	if isMember {
		amount = amount * 0.95
	}
	if amount < 50 {
		amount = amount + 5
	}
	return amount
}
```

Adding a VIP discount later takes one more `if`, and nobody had to learn an interface and three types to do it.
