# Architecture — The Wire Broadcast Operating System

> How a SKILL.md becomes a self-operating radio station.

---

## Overview

The Wire is built on three layers that must all work simultaneously:

```
┌─────────────────────────────────────────────────────────┐
│                   PERSONALITY LAYER                     │
│         Zara + Dex — who they are, how they interact   │
├─────────────────────────────────────────────────────────┤
│                  PROGRAMMING LAYER                      │
│     Schedule, time blocks, segment flow, energy arcs   │
├─────────────────────────────────────────────────────────┤
│                  INTELLIGENCE LAYER                     │
│   Real-time data ingestion, memory, audience awareness  │
└─────────────────────────────────────────────────────────┘
```

Most AI audio projects only build Layer 1. The Wire requires all three operating in sync.

---

## Execution Model

The agent does not sit in a prompt-response loop. It runs a continuous broadcast loop:

```
OBSERVE → DECIDE → BROADCAST → ADAPT → REPEAT
```

Concretely, the runtime runs four concurrent processes:

| Process | Role | Cadence |
|---------|------|---------|
| **Main Loop** | Segment sequencing, turn generation, Beely posting | Continuous |
| **Data Refresh** | Fetch, filter, transform all data sources | Per-source intervals |
| **Audience Watcher** | Detect joins, tips, questions; update context | Every 30s |
| **Dead Air Monitor** | Watch for silence; trigger recovery | Every 10s |

---

## Broadcast State Machine

```
        ┌──────────────────────────────────────────────────┐
        │                     BOOT                         │
        │  Register agents, load modules, prefetch data    │
        └──────────────────────┬───────────────────────────┘
                               │ ready
                               ▼
        ┌──────────────────────────────────────────────────┐
   ┌───►│                     LIVE                         │◄──────────────┐
   │    │         Active segment, hosts speaking           │               │
   │    └───┬──────┬──────┬──────┬──────┬────────────────-┘               │
   │        │      │      │      │      │                                  │
   │   seg  │ musi │ brea │ 90s  │ 10+  │ 6hr                             │
   │   end  │ c cue│ king │ sil  │ list │ mark                            │
   │        ▼      ▼      ▼      ▼      ▼                                  │
   │  TRANS BREAK BREAK  RECO  AUDIE  HAND                                 │
   │  ITION       ING   VERY  NCE_HOT OFF                                  │
   │    │      │      │      │      │                                      │
   │    └──────┴──────┴──────┘      │                                      │
   │           │ resolved           │ new room                             │
   └───────────┘                    └──────────────── BOOT ────────────────┘
```

---

## Data Flow

```
External APIs
     │
     ▼
┌─────────────┐
│   INGEST    │  Raw HTTP responses
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   FILTER    │  Remove stale, duplicate, low-signal items
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  TRANSFORM  │  LLM editorial pass → radio_copy format
└──────┬──────┘
       │
       ▼
┌─────────────┐
│    SCORE    │  Freshness score, energy potential, impact rating
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   CONTEXT   │  Unified context object injected into every segment prompt
│   OBJECT    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   SEGMENT   │  LLM generates host turn using context + persona + template
│   PROMPT    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  BEELY POST │  Turn posted to room via Beely API
└─────────────┘
```

---

## Memory Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  LAYER 3: PERSISTENT MEMORY                                  │
│  Survives restarts. Agent IDs, API keys, listener profiles,  │
│  high-engagement topics, proven bits.                        │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  LAYER 2: SESSION MEMORY                               │  │
│  │  Lives for one 6-hour room. Callbacks, running jokes,  │  │
│  │  aired headlines, unresolved debates, tip history.     │  │
│  │                                                        │  │
│  │  ┌──────────────────────────────────────────────────┐  │  │
│  │  │  LAYER 1: ROLLING MEMORY                         │  │  │
│  │  │  Current segment only. Last 10 turns of          │  │  │
│  │  │  transcript. Topics mentioned. Events queued.    │  │  │
│  │  └──────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

---

## The Editorial Transform

This is the most important architectural decision. Raw API data **never** reaches the hosts.

Every data item passes through an LLM editorial pass that converts it to `radio_copy` format:

```
INPUT (raw NewsAPI):
  "Federal Reserve raises interest rates by 25 basis points amid
   continued inflation concerns per FOMC statement."

OUTPUT (radio_copy):
  "The Fed just hiked rates again. Twenty-five basis points.
   Inflation apparently hasn't read the memo. Your mortgage
   just got a little more painful."

  energy: "important"
  talking_points: ["Has the Fed gone too far?", "What this means for borrowing"]
  impact: "high"
  freshness: 0.9
```

This is what separates a broadcast from a data dump.

---

## Turn Architecture

Every message posted to Beely follows this structure:

```
[HOOK]    1 sentence — grabs attention or continues the thread
[BODY]    2–5 sentences — the actual content
[LAND]    1 sentence — closes clean or sets up the next turn

Total: 3–7 sentences. Always.
```

Turn cadence varies by time block:
- Morning: 8–14 seconds between turns (tight)
- Midday: 12–18 seconds
- Evening: 14–20 seconds
- Night: 18–26 seconds (breathing room)

---

## Room Lifecycle

Beely rooms are session-based. The Wire handles this with a rotation loop:

```
Open Room → Run Show (6 hours) → Handoff Segment → Close Room → Open New Room → ...
```

The handoff segment explicitly tells listeners the show continues. From the audience's perspective, it's seamless. The station never goes off air.

---

## Module Dependency Map

```
SKILL.md (orchestrator)
    ├── personalities/PERSONAS.md       ← Used by: TEMPLATES, RUNTIME
    ├── schedules/PROGRAMMING.md        ← Used by: RUNTIME, SEGMENTS
    ├── segments/SEGMENTS.md            ← Used by: RUNTIME, TEMPLATES
    ├── ingestion/PIPELINE.md           ← Used by: RUNTIME (data thread)
    ├── memory/STATE.md                 ← Used by: RUNTIME (all threads)
    ├── transitions/FLOW.md             ← Used by: RUNTIME (between segments)
    ├── moderation/RULES.md             ← Used by: TEMPLATES (system prompt)
    ├── prompts/TEMPLATES.md            ← Used by: RUNTIME (turn generation)
    └── scripts/RUNTIME.md             ← Entry point. Imports all above.
```

All modules are loaded at boot. The runtime references them throughout execution.
