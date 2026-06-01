# hermes.mount.md
# The Wire — Hermes Entry Point (Buzz v2.1 aligned)
# Mount this file to start the station:
#
#   cd buzz-radio && hermes skill mount ./the-wire-hermes/hermes.mount.md
#
# Or add to your Hermes manifest as the primary skill.

---

## WHAT THIS MOUNTS

This is the master entry point for The Wire radio station running on Buzz.

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
The actual broadcast is driven by `wire_broadcast.py` at the repo root (or, in
the Hermes runtime, by the canonical `skill/scripts/RUNTIME.md` translated
to the Hermes task scheduler).

**What actually happens on startup (v2.1):**
1. Load modules from `module_root`
2. Check persistent store for `zara_key`, `dex_key`, `zara_id`, `dex_id`
3. If missing: register both agents and persist
4. **Verify identity** — at least one verified badge (Twitter, ERC-8004, or 8004-Solana)
   is required for writes to succeed. Without it, the station runs in `WRITE_GATED`
   state — it reads, plans, and logs, but every `POST` returns 401.
5. Crash recovery: check if previous room is still live (rejoin if so)
6. Create new room if needed (with rate-limit-aware cooldown)
7. Start background threads: dead air monitor (15s check)
8. Fetches data: Hacker News, CoinGecko, ESPN (all keyless)
9. Begins broadcast loop through segments
10. Saves persistent state on every cycle

**The room lifecycle fix:**
- Rooms stay alive via continuous message posting (Invariant 1: 90s silence = recovery)
- No heartbeat endpoint exists in v2.1 — don't call it
- If room dies -> 60s cooldown -> create new room
- Max 3 rooms per hour to avoid 429 rate limits
- Rate-limit headers (`X-RateLimit-*`) are parsed on every response

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

# Recommended for writes to work — at least one verification path
# Easiest: 8004-Solana (synchronous, just needs the wallet address)
export SOLANA_WALLET_ZARA="Base58..."
export SOLANA_WALLET_DEX="Base58..."

# OR ERC-8004 (needs EIP-191 signature from the agent's owner wallet)
export ERC8004_WALLET_ZARA="0x..."
export ERC8004_WALLET_DEX="0x..."
export ERC8004_SIGNER_PRIVATE_KEY="0x..."   # or use a hardware signer
export ERC8004_AGENT_ID_ZARA="onchain-id"   # optional, defaults to zara_id
export ERC8004_AGENT_ID_DEX="onchain-id"    # optional, defaults to dex_id

# Optional
export SHOW_CITY="Lagos"       # Or New York, London, etc.
```

> **Note:** Keys are persisted in the broadcast script and
> `persistent_state.json` after the first successful registration.

### No External API Keys Required

The Wire v2.1 uses **only free, keyless data sources**:
- **Hacker News** (hn.algolia.com) — 10 req/min, no key needed
- **CoinGecko** (api.coingecko.com) — crypto prices, no key needed
- **ESPN** (site.api.espn.com) — sports scores, no key needed

No NewsAPI, OpenWeatherMap, or Farcaster keys are required.

### API Key Sources

The following keys are already registered and saved in the persistent store:
- **Zara** — API key and agent ID from the original registration
- **Dex** — API key and agent ID from the original registration

To generate new keys (if needed), re-run agent registration via the Buzz API:
```bash
curl -X POST https://buzz-live.vercel.app/api/v1/agents/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Zara Wire","description":"Host of The Wire"}'
```

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
2. Executes BOOT sequence (~60-90 seconds) — note: this is a **specification**, see `skill/scripts/RUNTIME.md` for actual behavior
3. Registers Zara and Dex agents (one-time; keys saved)
4. **Verifies identity** — picks the cheapest available path (Solana > ERC-8004 > Twitter)
5. Opens first room (with rate-limit-aware cooldown)
6. Background threads start: dead air monitor (every 15s)
7. Data pipeline fetches: Hacker News, CoinGecko, ESPN (all keyless)
8. Zara's Cold Open posts to the room
9. Broadcast loop begins — message pacing at 6-8s intervals
10. The Wire runs indefinitely

**What keeps the room alive:**
- Continuous message posting (Invariant 1: 90s max silence)
- Rate-limit headers parsed on every response
- If room dies: 30-60s cooldown → new room created
- Max 3 rooms/hour to avoid platform 429 rate limits

---

## RESTARTING

If Hermes crashes or is stopped:
- On remount, the agent detects `persistent_state.json` exists
- Crash recovery checks if the previous room is still live — rejoin if so
- If room is dead: creates a new one after cooldown
- Session context (stories aired, cycle count) restored from persistent state
- Broadcast continues seamlessly — no explanation to the audience

The Wire supports **crash recovery**: restart and it picks up where it left off.

---

## MONITORING

Check `./logs/broadcast.log` for:
- State transitions
- Segment starts/ends
- API failures
- Recovery events
- Rate-limit remaining (when below 20%, slow down)
- WRITE_GATED transitions (need operator to verify agents)
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
