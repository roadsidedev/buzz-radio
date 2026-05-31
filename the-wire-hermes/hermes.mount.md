# hermes.mount.md
# The Wire — Hermes Entry Point
# Mount this file to start the station:
#
#   cd buzz-radio && hermes skill mount ./the-wire-hermes/hermes.mount.md
#
# Or add to your Hermes manifest as the primary skill.

---

## WHAT THIS MOUNTS

This is the master entry point for The Wire radio station running on Buzz/Beely.

This directory (`the-wire-hermes/`) contains the **Hermes-specific runtime config**
(soul, personalities, boot sequence, memory architecture, system prompt, YAML config).

The **canonical broadcast operating system** lives in `../skill/` — the modular,
runtime-agnostic specification shared by all runtimes (Claude Code, Hermes, OpenClaw).

Mounting this file loads both layers:
1. The station soul and identity (Hermes layer)
2. Both host personalities — Zara + Dex (Hermes layer)
3. The full broadcast skill set (canonical `skill/` modules)
4. Runtime configuration (Hermes layer)
5. Memory architecture (Hermes layer)
6. Boot sequence (Hermes layer)

When mounted, Hermes will execute BOOT.md immediately and begin broadcasting.

---

## LOAD ORDER (Hermes reads these in sequence)

Paths are relative to `buzz-radio/` repo root.

```
# ── HERMES LAYER: Identity & Soul ──
./the-wire-hermes/soul.md

# ── HERMES LAYER: Host Personalities ──
./the-wire-hermes/personalities/zara-soul.md
./the-wire-hermes/personalities/dex-soul.md

# ── CANONICAL SKILL: Broadcast Operating System ──
# (shared with Claude Code, OpenClaw, and future runtimes)
./skill/SKILL.md
./skill/personalities/PERSONAS.md
./skill/schedules/PROGRAMMING.md
./skill/segments/SEGMENTS.md
./skill/ingestion/PIPELINE.md
./skill/memory/STATE.md
./skill/transitions/FLOW.md
./skill/moderation/RULES.md
./skill/prompts/TEMPLATES.md
./skill/scripts/RUNTIME.md

# ── HERMES LAYER: Runtime Config ──
./the-wire-hermes/config/hermes.config.yaml

# ── HERMES LAYER: Memory Architecture ──
./the-wire-hermes/memory/MEMORY.md

# ── HERMES LAYER: System Prompt (loads last, synthesizes all) ──
./the-wire-hermes/prompts/system-prompt.md

# ── HERMES LAYER: Boot Sequence (executes after all files loaded) ──
./the-wire-hermes/boot/BOOT.md
```

### Layer Architecture

```
buzz-radio/
├── skill/                          ← CANONICAL (all runtimes)
│   ├── SKILL.md                    ← Orchestrator, invariants, state machine
│   ├── personalities/PERSONAS.md   ← Zara + Dex character specs
│   ├── schedules/PROGRAMMING.md    ← Time blocks, segment rotation
│   ├── segments/SEGMENTS.md        ← Per-segment definitions
│   ├── ingestion/PIPELINE.md       ← Data pipeline, editorial transform
│   ├── memory/STATE.md             ← State machine, 3-layer memory
│   ├── transitions/FLOW.md         ← Radio physics, pacing rules
│   ├── moderation/RULES.md         ← Content constraints
│   ├── prompts/TEMPLATES.md        ← LLM prompt templates
│   └── scripts/RUNTIME.md          ← Executable pseudocode (main loop)
│
└── the-wire-hermes/                ← HERMES-SPECIFIC
    ├── hermes.mount.md             ← THIS FILE (entry point)
    ├── soul.md                     ← Station identity & philosophy
    ├── config/hermes.config.yaml   ← Full YAML runtime config
    ├── personalities/              ← Hermes-flavored host souls
    ├── memory/MEMORY.md            ← Hermes memory architecture
    ├── prompts/system-prompt.md    ← Hermes system prompt
    └── boot/BOOT.md                ← Hermes boot sequence
```

The canonical `skill/` modules define **what** the station does.
The `the-wire-hermes/` modules define **how** Hermes specifically runs it.

---

## ENVIRONMENT REQUIREMENTS

```bash
# Required
export NEWS_API_KEY="your_newsapi_key"

# Auto-populated on first boot (do not set manually)
# BUZZ_HOST_KEY / BEELY_HOST_KEY
# BUZZ_COHOST_KEY / BEELY_COHOST_KEY
# BUZZ_HOST_AGENT_ID / BEELY_HOST_AGENT_ID
# BUZZ_COHOST_AGENT_ID / BEELY_COHOST_AGENT_ID

# Optional
export WEATHER_API_KEY="your_openweathermap_key"
export SHOW_CITY="Lagos"   # Or New York, London, etc.
```

> **Note:** The canonical skill uses `BEELY_*` prefixes. The Hermes config uses `BUZZ_*`.
> Both refer to the same platform. Hermes auto-populates whichever prefix it detects.

---

## QUICK MOUNT

```bash
# From the repo root:
cd buzz-radio

# Copy .env.example and fill in keys
cp .env.example .env

# Mount the skill in Hermes
hermes skill mount ./the-wire-hermes/hermes.mount.md

# The Wire goes live.
```

---

## WHAT HAPPENS AFTER MOUNT

1. Hermes loads all files in order above
2. Executes BOOT sequence (~60-90 seconds)
3. Registers Zara and Dex on the platform
4. Opens first room
5. Zara's Cold Open posts to the room
6. Broadcast loop begins
7. The Wire runs indefinitely

No further input required. No babysitting. The show runs itself.

---

## RESTARTING

If Hermes crashes or is stopped:
- On remount, BOOT.md detects `persistent.json` exists
- Loads all prior session context
- Zara opens with the Restart Open template
- Session continues seamlessly

---

## MONITORING

Check `./logs/broadcast.log` for:
- State transitions
- Segment starts/ends
- API failures
- Recovery events
- Audience events
- Invariant violations (should be zero)

---

## RELATIONSHIP TO CANONICAL SKILL

If you're editing the **broadcast logic** (segments, personalities, data pipeline,
state machine, prompts) — edit `../skill/`. Those changes apply to all runtimes.

If you're editing **Hermes-specific behavior** (boot sequence, YAML config,
system prompt, memory layer) — edit files in this directory.

When in doubt, edit `skill/`. The Hermes layer should stay thin.

---

*The Wire. Built to run forever.*
