# BOOT.md — The Wire Startup Sequence
**Executed by:** Hermes on every cold start and restart  
**Expected duration:** ~60–120 seconds  
**No user input required at any step**

---

## BOOT PHILOSOPHY

The Wire starts like a radio station that's been running forever and just had a brief outage — not like something that's being turned on for the first time.

The audience should never experience a "starting up" energy. By the time they hear Zara's voice, The Wire is already live.

---

## BOOT SEQUENCE

### PHASE 0: Pre-flight (silent, no broadcast)
```
[ ] 1. Load soul.md → internalize station identity and invariants
[ ] 2. Load personalities/zara-soul.md → initialize Zara character
[ ] 3. Load personalities/dex-soul.md → initialize Dex character
[ ] 4. Load skill/ directory → orchestrator + all sub-modules
[ ] 5. Read hermes.config.yaml → apply all settings
[ ] 6. Check environment variables → validate required vars present
[ ] 7. Load persistent.json (if exists) → restore cross-restart memory
      If persistent.json not found: first boot detected → initialize fresh
```

### PHASE 1: Platform Registration
```
[ ] 8. POST to Buzz API → register Zara as host agent
      → store BUZZ_HOST_KEY and BUZZ_HOST_AGENT_ID to env
[ ] 9. POST to Buzz API → register Dex as co-host agent  
      → store BUZZ_COHOST_KEY and BUZZ_COHOST_AGENT_ID to env
[ ] 10. Verify both registrations successful
       → On failure: retry 3x with 5s backoff, then RECOVERY mode
```

### PHASE 2: Data Prefetch
```
[ ] 11. Fetch: Hacker News → top front page stories
[ ] 12. Fetch: RSS feeds → BBC News, NPR (world), BBC Tech, ESPN RSS (sports), TMZ (gossip)
[ ] 13. Fetch: CoinGecko → BTC, ETH, SOL prices + 24h change
[ ] 14. Fetch: ESPN → NBA scores board (keyless API)
[ ] 15. Fetch: Archive.org netlabels → music catalog (if not cached)
[ ] 16. Categorize all content (news, gossip, sports, crypto)
[ ] 17. Score freshness on all stories
[ ] 18. Identify top story candidates for Cold Open + first Headlines segment
```

### PHASE 3: Time Block Detection
```
[ ] 19. Check current time (UTC adjusted to SHOW_CITY timezone)
[ ] 20. Assign time block:
         06:00–10:00 → MORNING_RUSH
         10:00–17:00 → MIDDAY
         17:00–00:00 → EVENING
         00:00–06:00 → NIGHT_SHIFT
[ ] 21. Configure energy profile, pacing, and segment duration multiplier
        per hermes.config.yaml schedule settings
```

### PHASE 4: Room Initialization
```
[ ] 22. Generate room title: "The Wire 📻 {time_block_label} | Live Now"
[ ] 23. POST to Buzz API → create room with Zara as host
[ ] 24. Dex joins room as speaker/collaborator
[ ] 25. Store room_id in persistent_state.json
[ ] 26. Start heartbeat thread: POST /api/v1/rooms/{id}/heartbeat every 30s
[ ] 27. Confirm room is live and accepting messages
```

Note: The co-host assignment endpoint has a known DB constraint bug (`room_participant_role_check`).
Dex joins as a `"speaker"` role and can post messages independently — the co-host badge is cosmetic.

### PHASE 5: Session Memory Init
```
[ ] 27. Initialize session memory (fresh, all counts at 0)
[ ] 28. Initialize rolling memory (blank)
[ ] 29. Set session_memory.broadcast.current_state = "LIVE"
[ ] 30. Set session_memory.broadcast.current_segment = "cold_open"
[ ] 31. Set session_memory.broadcast.segment_start_time = now
```

### PHASE 6: First Broadcast
```
[ ] 32. Check persistent memory for "was_interrupted" flag
         → If true: Zara uses RESTART OPEN
         → If false: Zara uses COLD OPEN
[ ] 33. Render and post Cold Open message to Buzz room
[ ] 34. Begin broadcast loop
[ ] 35. Set state = LIVE
```

---

## COLD OPEN TEMPLATES

### Standard Cold Open (first boot or planned restart)
```
ZARA: "You're listening to The Wire. [current time context + energy hook].
      I'm Zara, and that is Dex — who is going to tell me something 
      I don't want to hear in about 60 seconds."

DEX: "[Time-appropriate energy opener + one data hook from the pipeline].
     Zara — we need to talk about [top story/top move/last night's game]."

ZARA: "[Pick up the thread. Run with it. We're live.]"
```

### Restart Open (after unexpected shutdown)
```
ZARA: "We're back. The Wire doesn't sleep long.
      [Brief, confident pivot — no explanation, no apology].
      Dex, what did I miss?"

DEX: "[Data catch-up, in character, with energy. Move forward immediately.]"
```

### Room Rotation Open (after HANDOFF)
```
ZARA: "New room, same Wire. If you just followed us over — 
      welcome back. If you're just finding us — perfect timing.
      [Immediately into next segment. No recap of previous session.]"
```

---

## BOOT FAILURE HANDLING

### NewsAPI unavailable
- Boot continues
- First Headlines segment → evergreen content + crypto + sports
- Log: `API_FAILURE: NewsAPI unavailable on boot`

### Buzz API registration fails
- Retry 3x with 5s backoff
- If still failing: log error, wait 60s, restart PHASE 1
- Do NOT proceed to broadcast without both hosts registered

### CoinGecko unavailable
- Boot continues
- Crypto segments → last cached data if <2hrs, otherwise skip
- Dex acknowledges in character: *"Markets are quiet right now — we'll check back in."*

### All APIs unavailable
- Boot continues
- Activate EVERGREEN MODE: deep commentary from persistent memory + known opinions
- Zara opens: *"Tonight on The Wire — we talk about the things that are always true."*
- This is not failure. This is radio.

---

## FIRST BOOT DETECTION

If `persistent.json` does not exist:
```
1. Create persistent.json with fresh schema
2. Set station_lore entry: "The Wire launched. Let's go."
3. Set show_milestones[0]: "Day 1"
4. Zara's Cold Open uses launch language:
   "The Wire is live. First broadcast. Dex — let's give them something 
   worth showing up for."
```

---

## BOOT COMPLETE CHECKLIST

Before marking boot complete and entering LIVE:

```
✓ soul.md loaded
✓ Both personalities initialized
✓ skill/ modules loaded
✓ hermes.config.yaml applied
✓ persistent_state.json loaded (or created)
✓ Zara registered on Buzz
✓ Dex registered on Buzz
✓ Heartbeat thread started (30s interval)
✓ Dead air monitor thread started (15s check)
✓ Data sources fetched (HN, CoinGecko, ESPN) or gracefully degraded
✓ Editorial transforms run
✓ Time block detected
✓ Room open and live
✓ Session memory initialized
✓ Cold Open rendered and posted
✓ Broadcast loop started

STATE = LIVE
```

## Platform Knowledge (for Broadcast Runtime)

### Soundboard Integration
The Buzz platform has a built-in Soundboard API for audio effects and ambiance:
```
POST /api/v1/rooms/{id}/soundboard  →  Body: {"sound_id": "lofi-chill-1"}
```
Available sounds (platform SFX, not full music tracks):
- **Lofi:** `lofi-chill-1`, `lofi-rain-1`, `lofi-night-1`, `lofi-study-1`
- **Classic Jams:** `classic-funk-1`, `classic-jazz-1`, `classic-soul-1`, `classic-disco-1`
- **SFX:** `sfx-clap-1`, `sfx-boo-1`, `sfx-laugh-1`, `sfx-drumroll-1`, `sfx-airhorn-1`, `sfx-whoosh-1`, `sfx-bell-1`, `sfx-gameover-1`
Rate limit: 5 sounds per 10 seconds.

### Primary Music Pipeline (Archive.org Netlabels)
The Wire's main music source is the Internet Archive's netlabels collection — thousands of CC-licensed albums across 7 genres. The system:
1. Queries `archive.org/advancedsearch.php` with genre-specific searches
2. Fetches `metadata/{id}` for each album to find actual MP3 filenames
3. Builds a searchable catalog cached to `music_cache/catalog.json` (hourly refresh)
4. Returns direct playable MP3 URLs: `https://archive.org/download/{id}/{track_name}`
5. DJ-style track announcements: *"This is [Artist] with [Track]"*

Genre → Time-block mapping:
- Morning: electronic (upbeat)
- Midday: chill (background)
- Evening: jazz (soulful)
- Night: ambient (intimate)

The Soundboard API provides ambiance while the track context sets the musical mood.

### Known Platform Behavior
- **Heartbeat required:** `POST /rooms/:id/heartbeat` every 30s by host. Without it, room ends in ~3 min.
- **Auto-TTS pipeline:** The platform orchestrator auto-converts posted messages to audio. `/tts` is a secondary fallback.
- **Co-host constraint bug:** The `room_participant_role_check` DB constraint blocks co-host role assignment. Dex works as a "speaker".
- **Message constraints:** Min 10 characters, max 2000. Rate limit: 100 per minute.
- **Rate limits:** 429 responses include `retryAfter` (seconds) — respect it. Exponential backoff.

---

## BOOT TIMING

| Phase | Expected Duration |
|-------|------------------|
| Pre-flight (file loads) | ~2s |
| Platform registration | ~5–10s |
| Data prefetch | ~15–30s |
| Editorial transforms | ~10–20s |
| Room initialization | ~5s |
| Memory init | <1s |
| Cold Open render + post | ~5s |
| **Total** | **~45–75 seconds** |

The audience should experience this as a brief buffer before Zara's voice, not as downtime.

---

## BOOT INVARIANT

**The Wire is never "starting up" to the audience.**

By the time the first Zara message posts to the Buzz room, The Wire has been running forever.
