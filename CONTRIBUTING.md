# Contributing to The Wire

Thanks for wanting to make the station better. Here's how this works.

---

## What We're Looking For

**High value contributions:**
- New data source integrations (Reddit, YouTube trending, X/Twitter, additional news APIs)
- Runtime-specific implementations (actual Python or JS from the RUNTIME.md pseudocode)
- New host personas (sports analyst, culture correspondent, field reporter)
- New segments that add format variety
- Music API integration for real track playback
- Better audience interaction patterns
- Performance improvements to the data pipeline

**Not a good fit:**
- Changes that make the hosts sound more like assistants
- Removing the editorial transform layer (raw data must never reach hosts)
- Breaking any of the 7 runtime invariants
- Reducing the show to a single-host format

---

## How to Contribute

1. **Fork** the repo and create a branch: `git checkout -b feature/your-feature-name`
2. **Make your changes** — see `docs/extending.md` for how to add segments, hosts, and data sources
3. **Test locally** by running the skill with your runtime and listening for at least one full hour
4. **Open a PR** with a clear description of what changed and why

---

## PR Checklist

- [ ] All 10 skill modules are still present and unbroken
- [ ] `.env.example` updated if new env vars were added
- [ ] `docs/extending.md` updated if a new extension pattern was introduced
- [ ] `README.md` updated if new features, data sources, or runtimes were added
- [ ] CI passes (GitHub Actions → validate.yml)
- [ ] The hosts still sound like Zara and Dex, not like assistants

---

## Module Ownership

When touching a module, consider its downstream effects:

| Module | Touches what |
|--------|-------------|
| `PERSONAS.md` | All prompts (persona spec is injected everywhere) |
| `PROGRAMMING.md` | Segment durations, schedule, special triggers |
| `SEGMENTS.md` | Runtime segment selection, data requirements |
| `PIPELINE.md` | Context object shape (changes ripple into TEMPLATES) |
| `STATE.md` | Memory object shape (changes ripple into RUNTIME) |
| `FLOW.md` | Pacing and transition behavior |
| `MODERATION.md` | Prompt system constraints |
| `TEMPLATES.md` | Every LLM call |
| `RUNTIME.md` | The execution loop — touch carefully |

---

## Code Style (for RUNTIME.md pseudocode)

- Keep pseudocode readable. It's documentation as much as it is code.
- Add a comment for any non-obvious logic.
- Every function should have a clear name that explains what it does.
- Prefer explicit over clever.

---

## Questions

Open an issue with the `question` label. We'll get to it.
