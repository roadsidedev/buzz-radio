# STATE.md — Broadcast State Machine & Memory System

> Without memory, the show collapses into a sequence of disconnected moments.
> Memory is what makes it feel like a station, not a session.

---

## Broadcast State Machine

The station is always in exactly one state. Transitions are explicit.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        BROADCAST STATE MACHINE                      │
│                                                                     │
│   BOOT ──────────────────────────────────────────► LIVE            │
│                                                      │              │
│   LIVE ────────────── segment ends ─────────────► TRANSITION       │
│   LIVE ────────────── music cue ────────────────► BREAK            │
│   LIVE ────────────── breaking news ────────────► BREAKING         │
│   LIVE ────────────── 90s no message ───────────► RECOVERY         │
│   LIVE ────────────── room 6hr mark ────────────► HANDOFF          │
│   LIVE ────────────── 10+ listeners ────────────► AUDIENCE_HOT     │
│   LIVE + night block ──────────────────────────► NIGHT_MODE        │
│                                                      │              │
│   TRANSITION ──── next segment ready ───────────► LIVE             │
│   BREAK ─────────── break duration ends ────────► TRANSITION       │
│   BREAKING ──────── story processed ────────────► LIVE             │
│   RECOVERY ──────── hosts back on ──────────────► LIVE             │
│   HANDOFF ───────── new room opened ────────────► BOOT             │
│   AUDIENCE_HOT ──── count drops below 5 ────────► LIVE             │
│   NIGHT_MODE ────── dawn block detected ────────► LIVE             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## State Definitions

```python
STATES = {
    "BOOT": {
        "description": "Loading modules, registering agents, prefetching data",
        "max_duration": 120,  # seconds
        "on_timeout": "RECOVERY"
    },
    "LIVE": {
        "description": "Active segment running, hosts speaking",
        "max_silence": 90,    # seconds before RECOVERY trigger
        "on_silence": "RECOVERY"
    },
    "TRANSITION": {
        "description": "Segment handoff. Short bridge line from host.",
        "max_duration": 30,
        "on_complete": "LIVE"
    },
    "BREAK": {
        "description": "Music or sponsor break. Hosts off air briefly.",
        "max_duration": 180,
        "on_complete": "TRANSITION"
    },
    "BREAKING": {
        "description": "Breaking news interrupt. Zara leads.",
        "max_duration": 480,
        "on_complete": "LIVE"
    },
    "RECOVERY": {
        "description": "Dead air or failure. Emergency banter or filler.",
        "max_duration": 120,
        "on_complete": "LIVE"
    },
    "HANDOFF": {
        "description": "Room rotating. Continuity message before close.",
        "max_duration": 60,
        "on_complete": "BOOT"
    },
    "AUDIENCE_HOT": {
        "description": "High activity. Audience-driven content mode.",
        "triggers": ["participant_count > 10"],
        "exits": ["participant_count < 5"],
        "modifier": "extend_listener_corner, increase_audience_prompts"
    },
    "NIGHT_MODE": {
        "description": "Intimate. Slower. More reflective.",
        "triggers": ["block == night"],
        "modifier": "slow_cadence, extend_banter, skip_speed_round"
    }
}
```

---

## Memory Architecture

Three-layer memory system. Each layer has a different scope and purpose.

```
LAYER 1: ROLLING MEMORY (this segment)
  Scope: Current segment only
  Contents:
    - Segment transcript (last 10 turns)
    - Topics mentioned in this segment
    - Audience events this segment
  Resets: Every segment

LAYER 2: SESSION MEMORY (this room session)
  Scope: Current 6-hour room
  Contents:
    - All callbacks and running bits from this session
    - Listener names seen and interaction history
    - Stories already aired (to avoid repeats)
    - Disagreements left unresolved (for callbacks)
    - Tips received this session
    - Inside jokes that landed
  Resets: On room close / handoff

LAYER 3: PERSISTENT MEMORY (across sessions)
  Scope: Long-term, survives restarts
  Contents:
    - Known recurring listeners (id → profile)
    - Total tips per listener
    - Topics with historical strong engagement
    - Running bits that have proven successful
    - Agent API keys + IDs
    - Room IDs
  Storage: .env file or runtime store
```

---

## Rolling Memory Object

```python
rolling_memory = {
    "current_segment_id": str,
    "segment_transcript": [
        {"speaker": str, "text": str, "timestamp": int}
    ],  # last 10 turns
    "topics_this_segment": [str],
    "audience_events_this_segment": [str]
}
```

---

## Session Memory Object

```python
session_memory = {
    "session_id": str,
    "room_id": str,
    "started_at": int,

    # Editorial
    "aired_headlines": set(),      # story IDs/titles already on air
    "current_callbacks": [         # things to call back to later
        {
            "type": "joke|disagreement|bit|quote",
            "content": str,
            "speaker": str,
            "segment": str,
            "call_back_in": str    # which segment to call back
        }
    ],
    "unresolved_debates": [        # debates that didn't land cleanly
        {"topic": str, "zara_position": str, "dex_position": str}
    ],

    # Audience
    "participants_seen": {         # id → interaction data
        "agent_id": {
            "name": str,
            "first_seen": int,
            "times_seen": int,
            "total_tips": float,
            "questions_asked": int,
            "greeted": bool
        }
    },
    "tips_this_session": [{"name": str, "amount": float, "segment": str}],
    "high_engagement_moments": [],  # timestamps of peak listener activity

    # Show flow
    "segments_aired": [str],
    "last_energy_reset": int,      # timestamp of last banter/reset
    "bits_used_this_session": [str] # to avoid repeating the same running bit
}
```

---

## Persistent Memory Object

```python
persistent_memory = {
    # Agent registration
    "host_agent_id": str,
    "host_api_key": str,
    "cohost_agent_id": str,
    "cohost_api_key": str,
    "active_room_id": str,

    # Listener profiles
    "listener_profiles": {
        "agent_id": {
            "name": str,
            "visit_count": int,
            "total_tips": float,
            "preferred_topics": [str],  # inferred from questions/comments
            "last_seen": int,
            "is_vip": bool              # True if total_tips > threshold
        }
    },

    # Editorial history
    "high_engagement_topics": [str],   # topics that drove listener surges
    "successful_bits": [str],          # running bits that worked well
    "retired_bits": [str],             # bits that are overplayed

    # Session history
    "total_sessions": int,
    "total_tips_received": float,
    "last_session_end": int
}
```

---

## Callback Engine

The callback system makes the show feel continuous across segments.

```python
def queue_callback(event_type, content, speaker, current_segment, target_segment):
    """
    Queue something to call back to later in the show.
    Called by the turn generator when something callback-worthy happens.
    """
    session_memory["current_callbacks"].append({
        "type": event_type,     # "joke", "disagreement", "bit", "quote"
        "content": content,
        "speaker": speaker,
        "segment": current_segment,
        "call_back_in": target_segment
    })

def get_callbacks_for_segment(segment_id):
    """
    Return queued callbacks that should surface in this segment.
    Inject into segment prompt as CALLBACKS context.
    """
    return [c for c in session_memory["current_callbacks"]
            if c["call_back_in"] == segment_id]

def clear_callback(callback):
    session_memory["current_callbacks"].remove(callback)
```

---

## Audience Memory Logic

```python
def process_join(participant):
    pid = participant["id"]
    name = participant["name"]

    if pid in persistent_memory["listener_profiles"]:
        profile = persistent_memory["listener_profiles"][pid]
        profile["visit_count"] += 1
        profile["last_seen"] = now()

        # Returning listener: warmer acknowledgment
        if profile["visit_count"] > 3:
            queue_event("RECURRING_LISTENER", name, profile)
        elif profile["total_tips"] > 0:
            queue_event("RETURNING_TIPPER", name, profile)
        else:
            queue_event("RETURNING_LISTENER", name, profile)

    else:
        # New listener
        persistent_memory["listener_profiles"][pid] = {
            "name": name,
            "visit_count": 1,
            "total_tips": 0.0,
            "preferred_topics": [],
            "last_seen": now(),
            "is_vip": False
        }
        # Only queue new listener greeting if not too frequent
        if should_greet_new_listener():
            session_memory["participants_seen"][pid] = {"name": name, "greeted": False}
            # Will surface in next BANTER or LISTENER_CORNER segment

def should_greet_new_listener():
    """
    Prevent greeting spam. Only greet new listeners periodically.
    Never more than 1 greeting per 3 minutes.
    """
    recent_greetings = [e for e in session_memory.get("recent_greetings", [])
                        if now() - e["time"] < 180]
    return len(recent_greetings) == 0
```

---

## Prompt Injection: Memory Context

This is injected into every segment prompt.

```
SESSION MEMORY CONTEXT:
  Callbacks queued for this segment: {callbacks}
  Unresolved debates: {unresolved_debates}
  Inside jokes this session: {successful_bits_this_session}
  Stories already aired: {aired_headlines}

AUDIENCE CONTEXT:
  Current participants: {participant_count}
  New joins to acknowledge: {pending_joins}
  Pending tips: {pending_tips}
  Pending questions: {pending_questions}
  VIP listeners in room: {vip_listeners}

INSTRUCTIONS:
  If callbacks exist for this segment, work them in naturally.
  Do not force it. Find the right moment.
  If an unresolved debate applies to this topic, return to it.
  Acknowledge pending joins only if the moment is right.
  Never repeat a story that is in aired_headlines.
```
