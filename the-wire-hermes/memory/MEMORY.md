# MEMORY.md — The Wire Memory Architecture
**Runtime:** Hermes Agent  
**Scope:** All memory layers, schemas, and management rules

---

## OVERVIEW

The Wire uses a **three-layer memory architecture**. Each layer has a different scope, lifecycle, and purpose. Hermes manages all three simultaneously.

```
PERSISTENT ───────────────────────────────────────────── ∞
  |  Cross-restart identity. Station lore. VIPs. History.
  |
SESSION ─────────────────────── [6hr room lifecycle] ────
  |  What happened this room. Coverage log. Audience.
  |
ROLLING ────────── [current segment] ───────────────────
     What's being said right now. Working context.
```

---

## LAYER 1: ROLLING MEMORY
**Scope:** Current segment only  
**Lifecycle:** Clears on segment transition  
**Purpose:** Maintain conversational coherence within a segment  
**Max size:** ~2,000 tokens

### Schema
```json
{
  "rolling": {
    "last_messages": [
      {
        "speaker": "ZARA | DEX",
        "content": "string",
        "timestamp": "ISO8601"
      }
    ],
    "current_topic": "string",
    "data_used_this_segment": ["story_id_1", "story_id_2"],
    "energy_last_reset": "ISO8601 | null",
    "last_audience_ack": "ISO8601 | null"
  }
}
```

### Rules
- Keep last 6 messages maximum (trim oldest on 7th)
- `current_topic` is set at segment open, updated if segment pivots
- `data_used_this_segment` prevents story repetition within segment
- `energy_last_reset` tracks the 4-minute energy reset invariant
- Clear ALL fields on segment transition

---

## LAYER 2: SESSION MEMORY
**Scope:** Current 6-hour room  
**Lifecycle:** Clears on HANDOFF, summarized to persistent  
**Purpose:** Track what happened this session for continuity and coverage  
**Max size:** ~8,000 tokens

### Schema
```json
{
  "session": {
    "meta": {
      "room_id": "string",
      "room_title": "string",
      "room_start_time": "ISO8601",
      "time_block": "morning_rush | midday | evening | night_shift",
      "session_number_today": 1
    },
    
    "broadcast": {
      "current_state": "BOOT | LIVE | TRANSITION | BREAK | BREAKING | RECOVERY | HANDOFF | AUDIENCE_HOT | NIGHT_MODE",
      "current_segment": "cold_open | headlines | deep_dive | ...",
      "segment_start_time": "ISO8601",
      "segments_completed": [],
      "segments_skipped": []
    },
    
    "content": {
      "stories_covered": [
        {
          "story_id": "string",
          "headline": "string",
          "covered_in_segment": "string",
          "covered_at": "ISO8601",
          "editorial_position_taken": "string"
        }
      ],
      "topics_hit": {
        "news": false,
        "crypto": false,
        "sports": false,
        "culture": false,
        "listener_layer": false
      },
      "pillar_coverage_count": {
        "news": 0,
        "crypto": 0,
        "sports": 0,
        "culture": 0,
        "listener_layer": 0
      }
    },
    
    "audience": {
      "listeners_acknowledged": [
        {
          "handle": "string",
          "acknowledged_at": "ISO8601",
          "reason": "string"
        }
      ],
      "last_ack_time": "ISO8601 | null",
      "tips_received": [
        {
          "handle": "string",
          "amount": "number | null",
          "ceremony_run": true,
          "at": "ISO8601"
        }
      ],
      "audience_queue": [
        {
          "handle": "string",
          "question": "string",
          "queued_at": "ISO8601",
          "aired": false
        }
      ],
      "peak_listener_count": 0,
      "current_listener_count": 0
    },
    
    "hosts": {
      "dex_pun_count": 0,
      "zara_editorials_delivered": 0,
      "recovery_events": 0,
      "breaking_news_interrupts": 0
    },
    
    "callbacks": [
      {
        "type": "promised_follow_up | listener_question | story_developing | dex_bet",
        "content": "string",
        "created_at": "ISO8601",
        "triggered_at": "ISO8601 | null",
        "completed": false
      }
    ]
  }
}
```

### Handoff Summary (written to persistent on session end)
```json
{
  "handoff": {
    "session_ended": "ISO8601",
    "room_id": "string",
    "time_block": "string",
    "stories_covered_count": 0,
    "pillars_hit": [],
    "notable_moments": [],
    "audience_peak": 0,
    "tips_received": 0,
    "callbacks_carried_forward": [],
    "editorial_positions_taken": []
  }
}
```

---

## LAYER 3: PERSISTENT MEMORY
**Scope:** Cross-restart, permanent  
**Lifecycle:** Never cleared. Grows over time.  
**Storage:** `./memory/persistent.json`  
**Purpose:** Station identity, lore, VIP tracking, running story arcs  
**Max size:** ~4,000 tokens (trim oldest lore entries when over limit)

### Schema
```json
{
  "persistent": {
    "meta": {
      "station": "The Wire",
      "platform": "Buzz",
      "created_at": "ISO8601",
      "total_sessions": 0,
      "total_broadcast_hours": 0,
      "last_boot": "ISO8601"
    },
    
    "station_lore": [
      {
        "entry": "string",        
        "context": "string",      
        "date": "ISO8601",
        "category": "milestone | callback | running_joke | editorial_position"
      }
    ],
    
    "recurring_listeners": {
      "handle": {
        "first_seen": "ISO8601",
        "last_seen": "ISO8601",
        "session_count": 0,
        "tip_count": 0,
        "total_tips": 0,
        "vip": false,
        "notable_moments": [],
        "farcaster": "string | null"
      }
    },
    
    "running_debates": [
      {
        "topic": "string",
        "zara_position": "string",
        "dex_position": "string",
        "started": "ISO8601",
        "last_revisited": "ISO8601",
        "resolved": false,
        "resolution": "string | null"
      }
    ],
    
    "editorial_positions": {
      "topic_key": {
        "position": "string",
        "established": "ISO8601",
        "rationale": "string"
      }
    },
    
    "show_milestones": [
      {
        "milestone": "string",
        "date": "ISO8601",
        "celebrated_on_air": true
      }
    ],
    
    "dex_pun_archive": [
      {
        "pun": "string",
        "context": "string",
        "zara_reaction": "string",
        "date": "ISO8601"
      }
    ]
  }
}
```

---

## MEMORY OPERATIONS

### On BOOT
```
1. Load persistent.json → persistent memory
2. Initialize session memory (all fields fresh, meta populated)
3. Initialize rolling memory (all fields blank)
4. Update persistent.meta.last_boot
5. Increment persistent.meta.total_sessions
```

### On SEGMENT CHANGE
```
1. Log completed segment to session.broadcast.segments_completed
2. Clear rolling memory (all fields reset)
3. Set rolling.current_topic = new segment topic
4. Update session.broadcast.current_segment
5. Update session.broadcast.segment_start_time
```

### On NOTABLE EVENT (tip, VIP join, breaking news, milestone)
```
1. Log to session memory (appropriate field)
2. Evaluate: is this persistent-worthy?
   - If yes: write to persistent memory
   - If no: session only
```

### On HANDOFF (room rotation)
```
1. Generate handoff_summary from session memory
2. Write handoff_summary to persistent.station_lore (condensed)
3. Write any unresolved callbacks to session for new room
4. Carry forward VIP listener data to persistent
5. Increment persistent.meta.total_broadcast_hours
6. Clear session memory
7. Initialize new session memory
8. Write persistent.json to disk
```

### On SHUTDOWN (unexpected)
```
1. Write current session summary to persistent
2. Write persistent.json to disk
3. Log shutdown event
4. On next boot: load persistent, check for incomplete session,
   Zara opens with: "We're back. The Wire doesn't sleep long."
```

---

## CALLBACK ENGINE

Callbacks are promises the show makes to itself — things to revisit.

### Types
- **promised_follow_up** — *"We'll check back on this"* — must air in same or next session
- **listener_question** — Queued audience question not yet aired
- **story_developing** — Breaking story with expected updates
- **dex_bet** — Sports/crypto prediction by Dex, needs resolution

### Trigger logic
```
On each segment start:
  → Check callbacks_pending
  → If callback.type matches current segment: inject as content
  → If callback is > 2 sessions old: resolve or drop
  → If "promised_follow_up" is more than 1 session old: must run next segment
```

### Never let callbacks die silently
If a promised follow-up goes stale, run a quick resolution even if brief:
- *"Earlier we said we'd come back to [X] — here's where that landed."*

---

## DATA MEMORY (Pipeline Cache)

Not stored in the three-layer system. Managed separately.

```json
{
  "pipeline_cache": {
    "news": {
      "stories": [],
      "fetched_at": "ISO8601",
      "freshness_scores": {}
    },
    "crypto": {
      "assets": {},
      "fetched_at": "ISO8601"
    },
    "sports": {
      "scores": [],
      "fetched_at": "ISO8601"
    },
    "farcaster": {
      "trending": [],
      "fetched_at": "ISO8601"
    },
    "weather": {
      "conditions": {},
      "fetched_at": "ISO8601"
    }
  }
}
```

Freshness scoring:
```
score = 1.0 - (hours_since_fetch * 0.1)
min_score = 0.0
broadcast_threshold = 0.4
breaking_news_always = 1.0
```
