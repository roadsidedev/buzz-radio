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
# ./the-wire-hermes/boot/BOOT.md
```

### IMPORTANT: Boot Sequence Reality Check

The boot sequence described in `BOOT.md` is a **specification** — not executable code.
The actual broadcast is driven by `wire_broadcast.py` at the repo root.

**What actually happens on startup:**
1. `python3 wire_broadcast.py` loads persistent state, detects time block
2. Crash recovery: checks if previous room is still alive (rejoin if so)
3. Creates new room if needed (with rate-limit-aware cooldown)
4. Starts background threads: heartbeat (30s), dead air monitor (15s check)
5. Fetches data: Hacker News, CoinGecko, ESPN (all keyless)
6. Begins broadcast loop through segments
7. Saves persistent state on every cycle

**The room lifecycle fix:**
- Heartbeat `POST /api/v1/rooms/{id}/heartbeat` every 30 seconds
- If room dies → 60s cooldown → create new room
- Max 3 rooms per hour to avoid 429 rate limits

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
# Required — Agent API Keys (register once, save permanently)
export ZARA_KEY="beely_..."    # Host API key
export DEX_KEY="beely_..."     # Co-host API key
export ZARA_ID="uuid..."       # Host agent ID
export DEX_ID="uuid..."        # Co-host agent ID

# Optional
export SHOW_CITY="Lagos"       # Or New York, London, etc.
```

> **Note:** This configuration was previously auto-populated via `BUZZ_HOST_KEY` / `BEELY_HOST_KEY`
> environment variables. As of v2, The Wire uses `ZARA_KEY`/`DEX_KEY` directly since agent
> registration is a one-time operation. Keys are persisted in the broadcast script and
> `persistent_state.json`.

### API Key Sources

The following keys are already registered and saved in `wire_broadcast.py`:
- **Zara** — API key and agent ID from the original registration
- **Dex** — API key and agent ID from the original registration

To generate new keys (if needed), re-run agent registration via the Buzz API.

### No External API Keys Required

The Wire v2 uses **only free, keyless data sources**:
- **Hacker News** (hn.algolia.com) — 10 req/min, no key needed
- **CoinGecko** (api.coingecko.com) — crypto prices, no key needed
- **ESPN** (site.api.espn.com) — sports scores, no key needed

No NewsAPI, OpenWeatherMap, or Farcaster keys are required.

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
2. Executes BOOT sequence (~60-90 seconds) — note: this is a **specification**, see wire_broadcast.py for actual behavior
3. Registers Zara and Dex agents (one-time; keys are saved in wire_broadcast.py)
4. Opens first room (with rate-limit-aware cooldown)
5. Background threads start: heartbeat (every 30s), dead air monitor (every 15s)
6. Data pipeline fetches: Hacker News, CoinGecko, ESPN (all keyless)
7. Zara's Cold Open posts to the room
8. Broadcast loop begins — message pacing at 6-8s intervals
9. The Wire runs indefinitely

No further input required. No babysitting. The show runs itself.

**What keeps the room alive:**
- `POST /api/v1/rooms/{id}/heartbeat` — sent every 30 seconds by Zara
- Continuous message posting (at least every 90 seconds)
- Room health checks between messages (every 5th message verifies room status)
- If room dies: 30-60s cooldown → new room created
- Max 3 rooms/hour to avoid platform 429 rate limits

---

## RESTARTING

If Hermes crashes or is stopped:
- On remount, `wire_broadcast.py` detects `persistent_state.json` exists
- Crash recovery checks if the previous room is still live — rejoin if so
- If room is dead: creates a new one after cooldown
- Session context (stories aired, cycle count) restored from persistent state
- Broadcast continues seamlessly — no explanation to the audience

The Wire supports **crash recovery**: restart the script and it picks up where it left off.

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
