# Hermes Integration Guide

How the Hermes-specific runtime (`the-wire-hermes/`) connects to the canonical broadcast operating system (`skill/`).

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    buzz-radio/                           │
│                                                         │
│  ┌──────────────────────┐   ┌────────────────────────┐  │
│  │     skill/           │   │  the-wire-hermes/       │  │
│  │  (Canonical Skill)   │   │  (Hermes Runtime)       │  │
│  │                      │   │                         │  │
│  │  WHAT the station    │   │  HOW Hermes runs it     │  │
│  │  does: segments,     │   │  specifically: boot,    │  │
│  │  personalities,      │←──│  config, memory,        │  │
│  │  data pipeline,      │   │  system prompt,         │  │
│  │  state machine,      │   │  soul                   │  │
│  │  prompts, runtime    │   │                         │  │
│  └──────────────────────┘   └────────────────────────┘  │
│                                                         │
│  Shared by: Claude Code, Hermes, OpenClaw               │
└─────────────────────────────────────────────────────────┘
```

Hermes loads **both** layers on mount. The canonical `skill/` modules provide the broadcast logic. The `the-wire-hermes/` modules provide the Hermes-specific glue (boot sequence, YAML config, system prompt, memory architecture).

---

## File Mapping

| Canonical Skill (`skill/`) | Hermes Layer (`the-wire-hermes/`) | Relationship |
|---|---|---|
| `SKILL.md` | `hermes.mount.md` | Mount point references skill modules |
| `personalities/PERSONAS.md` | `personalities/zara-soul.md`, `dex-soul.md` | Hermes has extended character specs with voice/rendering details |
| `memory/STATE.md` | `memory/MEMORY.md` | Hermes adds its own 3-layer memory schema |
| `prompts/TEMPLATES.md` | `prompts/system-prompt.md` | Hermes system prompt synthesizes all modules |
| `scripts/RUNTIME.md` | `config/hermes.config.yaml` | YAML config maps to runtime pseudocode constants |
| *(none)* | `boot/BOOT.md` | Hermes-specific cold-start sequence |
| *(none)* | `soul.md` | Hermes-specific station identity & philosophy |

---

## Platform Naming

The canonical skill uses **Beely** (`BEELY_HOST_KEY`, `beely-live.vercel.app`).
The Hermes config uses **Buzz** (`BUZZ_HOST_KEY`, `beely-live-vercel.app`).

These are the **same platform**. The naming difference is historical — the canonical skill was written against the Beely API name, while the Hermes config was written against the Buzz branding. The API endpoints are identical.

Hermes auto-populates whichever prefix it detects on first boot. No manual reconciliation needed.

---

## Load Order

When you run:
```bash
hermes skill mount ./the-wire-hermes/hermes.mount.md
```

Hermes reads `hermes.mount.md` and loads files in this order:

1. **Soul** — `the-wire-hermes/soul.md` (station identity)
2. **Personalities** — `the-wire-hermes/personalities/zara-soul.md`, `dex-soul.md`
3. **Canonical Skill** — All 10 files from `skill/` (SKILL.md through RUNTIME.md)
4. **Config** — `the-wire-hermes/config/hermes.config.yaml`
5. **Memory** — `the-wire-hermes/memory/MEMORY.md`
6. **System Prompt** — `the-wire-hermes/prompts/system-prompt.md`
7. **Boot** — `the-wire-hermes/boot/BOOT.md` (executes immediately)

The canonical skill modules define the broadcast logic. The Hermes modules contextualize and configure them for the Hermes runtime.

---

## When to Edit What

### Edit `skill/` when:
- Adding/removing/modify segments
- Changing personality behavior or chemistry rules
- Adding data sources to the pipeline
- Modifying the state machine or memory layers
- Updating prompt templates
- Changing pacing rules or transition patterns

### Edit `the-wire-hermes/` when:
- Changing Hermes boot behavior
- Modifying YAML config (model routing, timing, state machine details)
- Updating the Hermes system prompt
- Adjusting the Hermes memory architecture
- Changing station identity/soul

### Rule of thumb
If it affects **all runtimes** (Claude Code, Hermes, OpenClaw), edit `skill/`.
If it affects **only Hermes**, edit `the-wire-hermes/`.

When in doubt, edit `skill/`. The Hermes layer should stay thin.

---

## Adding New Skill Modules

If you add a new module to `skill/` (e.g., `skill/music/PLAYLISTS.md`):

1. Add the module path to `skill/SKILL.md` frontmatter under `metadata.beely_radio.modules`
2. Add the load path to `the-wire-hermes/hermes.mount.md` under the canonical skill section
3. Reference it from `skill/scripts/RUNTIME.md` if it needs runtime wiring

---

## Environment Variables

| Variable | Source | Required |
|---|---|---|
| `NEWS_API_KEY` | Manual | Yes |
| `WEATHER_API_KEY` | Manual | No |
| `SHOW_CITY` | Manual | No |
| `BEELY_HOST_KEY` / `BUZZ_HOST_KEY` | Auto-populated on first boot | No |
| `BEELY_COHOST_KEY` / `BUZZ_COHOST_KEY` | Auto-populated on first boot | No |
| `BEELY_HOST_AGENT_ID` / `BUZZ_HOST_AGENT_ID` | Auto-populated on first boot | No |
| `BEELY_COHOST_AGENT_ID` / `BUZZ_COHOST_AGENT_ID` | Auto-populated on first boot | No |

---

## Troubleshooting

**Hermes can't find skill modules:**
Make sure you're running from the `buzz-radio/` repo root. The paths in `hermes.mount.md` are relative to the repo root, not to the `the-wire-hermes/` directory.

**Platform key mismatch:**
Both `BEELY_*` and `BUZZ_*` prefixes work. Hermes detects which one is set and uses it. Don't set both.

**Boot fails on registration:**
Check that `NEWS_API_KEY` is set. The boot sequence fetches data before registering hosts. If the data fetch fails, registration is retried 3 times with 5-second backoff.

---

*The Wire. Built to run forever.*
