# 📻 The Wire — Autonomous Radio Broadcast System

> A self-operating 24/7 live radio station. Not an AI podcast. Not a chatbot with a schedule.
> A persistent broadcast network — with two hosts, a full programming engine, real-time data ingestion, and broadcast-grade timing logic.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform: Beely](https://img.shields.io/badge/Platform-Beely-blue)](https://beely-live.vercel.app)
[![Compatible: Claude Code](https://img.shields.io/badge/Runtime-Claude%20Code-blueviolet)]()
[![Compatible: Hermes](https://img.shields.io/badge/Runtime-Hermes-orange)]()
[![Compatible: OpenClaw](https://img.shields.io/badge/Runtime-OpenClaw-green)]()

---

## What This Is

The Wire is a plug-and-play **broadcast operating system** packaged as a SKILL.md for any capable agent runtime. Drop it into Claude Code, Hermes, or OpenClaw — the station runs itself.

Two AI hosts. A full programming schedule. Real-time news, crypto, sports, and culture. Audience awareness. Tip handling. 24/7, non-stop.

**Hosts:**
- **Zara** — Host. Sharp, warm, opinionated. Drives every segment.
- **Dex** — Co-host. Skeptical hype man. Owns sports, crypto, culture. Terrible puns. No regrets.

---

## Features

- **Two-host personality system** with full character specs, chemistry rules, running bits, and interruption protocols
- **Time-aware programming** — four daily blocks (Morning Rush, Midday, Evening, Night Shift) with different energy profiles and segment durations
- **60-minute rotating segment schedule** — Cold Open → Headlines → Deep Dive → Dex's Corner → Banter → Culture → Music Break → Second Headlines → Listener Corner → Commentary → Speed Round → Sign-off
- **Real-time data pipeline** — News (NewsAPI), Crypto (CoinGecko, keyless), Sports (ESPN, keyless), Weather, Social (Farcaster)
- **Editorial transform layer** — raw data is never broadcast. Everything is converted to radio-grade conversational copy before it reaches a host
- **Broadcast state machine** — 8 named states (BOOT, LIVE, TRANSITION, BREAK, BREAKING, RECOVERY, HANDOFF, AUDIENCE_HOT, NIGHT_MODE) with explicit transitions
- **Three-layer memory** — rolling (segment), session (6hr room), persistent (cross-restart)
- **Audience awareness** — join detection, tip ceremony, question queuing, VIP listener tracking
- **Special programming triggers** — Breaking news interrupt, Crypto surge, Big game day, High audience mode
- **Radio physics module** — pacing rules, energy arc, 4-minute reset law, interruption protocols, comedic timing, dead air recovery
- **Graceful degradation** — API failures handled in-character. The show never stops.
- **6-hour room rotation** — Beely room lifecycle managed automatically with continuity handoffs

---

## Project Structure

```
buzz-radio/
│
├── README.md                       ← This file
├── LICENSE                         ← MIT
├── .env.example                    ← Environment variable template
├── .gitignore
│
├── skill/                          ← CANONICAL BROADCAST OS (all runtimes)
│   ├── SKILL.md                    ← Orchestrator + boot sequence + invariants
│   ├── personalities/
│   │   └── PERSONAS.md             ← Zara + Dex full character specs + chemistry rules
│   ├── schedules/
│   │   └── PROGRAMMING.md          ← Time blocks, hourly segments, special triggers, energy arcs
│   ├── segments/
│   │   └── SEGMENTS.md             ← Per-segment goals, data needs, success/failure criteria
│   ├── ingestion/
│   │   └── PIPELINE.md             ← Data sources, editorial filter, transform layer, freshness scoring
│   ├── memory/
│   │   └── STATE.md                ← Broadcast state machine, 3-layer memory, callback engine
│   ├── transitions/
│   │   └── FLOW.md                 ← Radio physics, pacing rules, transition patterns, dead air recovery
│   ├── moderation/
│   │   └── RULES.md                ← Content constraints, audience handling, editorial standards
│   ├── prompts/
│   │   └── TEMPLATES.md            ← LLM prompt templates for every segment type
│   └── scripts/
│       └── RUNTIME.md              ← Full executable pseudocode — the main loop
│
├── the-wire-hermes/                ← HERMES-SPECIFIC RUNTIME
│   ├── hermes.mount.md             ← Hermes entry point (mount this to start)
│   ├── soul.md                     ← Station identity & philosophy
│   ├── config/
│   │   └── hermes.config.yaml      ← Full YAML runtime config (model routing, timing, state machine)
│   ├── personalities/
│   │   ├── zara-soul.md            ← Zara's Hermes-flavored character spec
│   │   └── dex-soul.md             ← Dex's Hermes-flavored character spec
│   ├── memory/
│   │   └── MEMORY.md               ← Hermes 3-layer memory architecture
│   ├── prompts/
│   │   └── system-prompt.md        ← Hermes system prompt (synthesizes all modules)
│   └── boot/
│       └── BOOT.md                 ← Hermes cold-start / restart sequence
│
├── docs/
│   ├── architecture.md             ← System architecture deep-dive
│   ├── quickstart.md               ← Get the station live in 5 minutes
│   ├── extending.md                ← How to add new segments, hosts, data sources
│   └── hermes-integration.md       ← How Hermes connects to the canonical skill
│
└── examples/
    ├── segment-transcript.md       ← Example of a full HEADLINES segment output
    └── context-object.json         ← Example context object passed to segment prompts
```

### Two-Layer Architecture

| Layer | Location | Purpose |
|-------|----------|---------|
| **Canonical Skill** | `skill/` | Runtime-agnostic broadcast operating system. Defines WHAT the station does. Shared by Claude Code, Hermes, OpenClaw, and any future runtime. |
| **Hermes Runtime** | `the-wire-hermes/` | Hermes-specific config. Defines HOW Hermes runs the station (boot, config, memory, system prompt). |

**Edit `skill/`** when changing broadcast logic (segments, personalities, data pipeline, prompts).
**Edit `the-wire-hermes/`** when changing Hermes-specific behavior (boot, YAML config, system prompt).

---

## Quick Start

### Prerequisites

- An agent runtime: Claude Code, Hermes, or OpenClaw
- A [NewsAPI](https://newsapi.org) key (free tier works)
- Optional: [OpenWeatherMap](https://openweathermap.org/api) key

Crypto (CoinGecko) and Sports (ESPN) are **keyless** — no signup required.

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/the-wire.git
cd the-wire
```

### 2. Set up environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
NEWS_API_KEY=your_newsapi_key_here
WEATHER_API_KEY=your_openweathermap_key_here   # optional
SHOW_CITY=New York                              # optional
```

Beely credentials (`BEELY_HOST_KEY`, `BEELY_COHOST_KEY`, agent IDs) are **auto-populated on first boot** — don't set them manually.

### 3. Mount the skill

**Claude Code** (uses canonical skill directly):
```bash
claude --skill ./skill/SKILL.md
```

**Hermes** (uses the-wire-hermes entry point, which loads canonical skill + Hermes config):
```bash
hermes skill mount ./the-wire-hermes/hermes.mount.md
```

**OpenClaw / Miles:**
Add to your skills manifest, then call `main()` from `skill/scripts/RUNTIME.md`.

### 4. The Wire goes live

On first boot, the agent will:
1. Register Zara and Dex on Beely (takes ~5 seconds)
2. Fetch initial data from all sources
3. Detect the current time block
4. Open a Beely room with Zara as host, Dex as co-host
5. Begin broadcasting

Check your Beely dashboard to find the live room. The station does not stop.

---

## Runtime Invariants

These are non-negotiable. The agent enforces them at all times.

| # | Invariant |
|---|-----------|
| 1 | **Silence = Failure.** Max 90 seconds without a message. Dead air triggers recovery immediately. |
| 2 | **Never dump raw data.** All ingested content is editorially transformed before broadcast. |
| 3 | **Energy is always managed.** Every 4 minutes of dense content → mandatory reset. |
| 4 | **Audience acknowledgment is earned.** Not every join gets greeted. Max 1 greeting per 3 minutes. |
| 5 | **Hosts never break character.** No "As an AI", no "I don't have access to". Radio always sounds live. |
| 6 | **The show has opinions.** Vague, both-sides commentary is not radio. Take a position. |
| 7 | **Chemistry over content.** The relationship between Zara and Dex is the product. |

---

## Data Sources

| Source | What | API Key | Refresh |
|--------|------|---------|---------|
| [NewsAPI](https://newsapi.org) | Top headlines, tech, sports, entertainment, business | Required (free) | 30 min |
| [CoinGecko](https://coingecko.com) | Crypto prices, 24h change, trending | None | 15 min |
| [ESPN (unofficial)](https://site.api.espn.com) | NBA, NFL, Soccer scores | None | 20 min |
| [OpenWeatherMap](https://openweathermap.org) | Weather for locale flavor | Optional (free) | 60 min |
| [Farcaster](https://warpcast.com) | Social pulse, trending casts | None | 20 min |

---

## Adding New Data Sources

See `docs/extending.md`. The short version:

1. Add a new entry to `SOURCE_REGISTRY` in `ingestion/PIPELINE.md`
2. Write a transform rule that converts raw output to the `radio_copy` format
3. Add the data key to the `context` object in `memory/STATE.md`
4. Reference it in the relevant segment in `segments/SEGMENTS.md`

---

## Adding a New Host / Correspondent

See `docs/extending.md`. The personas module (`personalities/PERSONAS.md`) has placeholder specs for future correspondents including Keiko (sports), Ray (culture), and an Anchor Voice for cold news reads.

---

## Modifying the Schedule

Edit `schedules/PROGRAMMING.md`. The schedule is a structured table — adjust segment durations per block, add special programming triggers, or modify the weekly variation rules.

---

## Contributing

PRs welcome. Specifically looking for:

- Additional data source integrations (Reddit trends, YouTube, X/Twitter)
- Music API integration (for real track playback via Beely)
- Additional host personas (sports analyst, culture correspondent)
- Runtime-specific implementation files (actual Python/JS from the pseudocode)
- Segment additions (e.g. interview format, call-in simulation)

---

## License

MIT — use it, fork it, build on it.

---

## Built On

- [Beely](https://beely-live.vercel.app) — AI-first live audio platform
- [NewsAPI](https://newsapi.org) — News ingestion
- [CoinGecko](https://coingecko.com) — Crypto data
- Compatible with Claude Code, Hermes, OpenClaw, and any agent runtime that can read SKILL.md

---

*The Wire. Built to run forever.*
