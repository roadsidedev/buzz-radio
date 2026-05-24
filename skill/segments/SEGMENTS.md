# SEGMENTS.md — Segment Definitions & Runtime Rules

> Every segment is a mini-show within the show.
> This file defines what each segment IS, what it produces,
> and what the runtime needs to execute it correctly.

---

## Segment Registry

Each segment entry defines its identity, owner, data requirements,
and success criteria.

---

### COLD_OPEN

```yaml
id: COLD_OPEN
name: "The Wire — Cold Open"
owner: host (Zara leads, Dex responds)
data_required:
  - context.news[0:2]   # top 2 stories to tease
  - context.block        # for time-of-day framing
success_criteria:
  - Listener knows what time block they're in
  - At least 2 stories teased without being fully revealed
  - Energy is set for the block (punchy=morning, warm=evening, intimate=night)
  - Ends with a clean hand to headlines
failure_modes:
  - Revealing the full story in the tease (don't explain what you're going to explain)
  - Generic open with no time-of-day awareness
  - Dex response is longer than Zara's open
callbacks: Pull from session_memory if session is ongoing (not first segment)
```

---

### HEADLINES_A / HEADLINES_B

```yaml
id: HEADLINES_A, HEADLINES_B
name: "The Wire Headlines"
owner: both
data_required:
  - context.news         # transformed editorial items
  - context.block
success_criteria:
  - 3–4 distinct stories covered
  - No story from aired_headlines repeated
  - Every story delivered in radio_copy format (never raw)
  - Dex reaction on at least 2 of 3 stories
  - One story flagged as HIGH IMPACT for DEEP_DIVE
failure_modes:
  - Reading raw news headlines
  - Covering the same story twice in the same hour
  - Skipping Dex reactions entirely
mark_as_used: True   # add story to session["aired_headlines"] after delivery
```

---

### DEEP_DIVE

```yaml
id: DEEP_DIVE
name: "The Story"
owner: host (Zara drives, Dex asks)
data_required:
  - Single HIGH IMPACT story from HEADLINES_A
  - context.news talking_points for that story
success_criteria:
  - Story has clear setup, context, and stakes
  - At least one Dex challenge or question
  - Take delivered: Zara's actual opinion
  - Does NOT resolve too cleanly
  - Transition sets up next segment
failure_modes:
  - Pure factual recitation with no take
  - Too long without a Dex interrupt (max 3 Zara turns in a row)
  - Clean resolution of a debate that should stay open
```

---

### DEX_CORNER

```yaml
id: DEX_CORNER
name: "Dex's Corner"
owner: cohost (Dex owns, Zara reacts)
data_required:
  - context.crypto       # prices + 24h change
  - context.scores       # NBA/NFL/Soccer
  - context.social_pulse # trending moment
success_criteria:
  - At least one crypto price + change covered
  - At least one sports result covered
  - One social/trending moment mentioned
  - Zara reacts to at least one item
  - Dex's portfolio bit used (max 1x per session)
special_triggers:
  - CRYPTO_SURGE active: expand to 5 turns, full market analysis
  - BIG_GAME active: sports desk expands to 3 turns
failure_modes:
  - Dex skipping crypto when data is available
  - Portfolio bit used more than once per session
  - Zara not reacting (this segment needs her as foil)
```

---

### BANTER

```yaml
id: BANTER
name: "The Break"
owner: both (unstructured)
data_required:
  - session_memory.current_callbacks
  - Any absurd/light item from context.news
success_criteria:
  - Feels unscripted
  - At least one callback to earlier in session (if session > 30 min old)
  - Energy reset achieved (lighter than surrounding segments)
  - Natural exit by Zara pulling back to show
failure_modes:
  - Feels structured or agenda-driven
  - No callbacks (if session has material to call back to)
  - Exit is abrupt rather than natural
  - Same banter topic as previous BANTER segment this session
duration_note: The most variable segment. Trust the moment.
```

---

### CULTURE_BEAT

```yaml
id: CULTURE_BEAT
name: "Culture"
owner: both (alternates who leads)
data_required:
  - context.social_pulse
  - context.news (entertainment category)
  - Midday block: music focus
  - Evening block: full debate preference
success_criteria:
  - Clear opinion from at least one host
  - Some form of disagreement or challenge
  - Listener engagement prompt at end ("what do you think?")
failure_modes:
  - No opinion taken ("it's interesting, people have views—")
  - Both hosts agree completely (no tension)
  - Topic is too niche for general audience without context
```

---

### MUSIC_BREAK

```yaml
id: MUSIC_BREAK
name: "The Break"
owner: system (hosts intro/outro only)
data_required:
  - context.block (for mood framing)
success_criteria:
  - Zara announces break with contextual, mood-aware language
  - Dex names the energy/vibe (real track if music API integrated)
  - Re-entry from break connects back to the show naturally
failure_modes:
  - Generic "now a music break" with no personality
  - Re-entry that ignores what was happening before the break
```

---

### LISTENER_CORNER

```yaml
id: LISTENER_CORNER
name: "The People's Segment"
owner: cohost (Dex leads)
data_required:
  - context.pending_tips
  - context.pending_questions
  - session_memory.participants_seen
success_criteria:
  - All pending tips acknowledged with ceremony
  - All pending questions addressed
  - If no queue: Dex improvises an audience prompt
  - At least one participant name used naturally (not robotically)
failure_modes:
  - Greeting every join in rapid succession (spam behavior)
  - Tip ceremony is mechanical, not performative
  - Questions answered without Zara's input
audience_hot_modifier: Extend by 2 minutes when participant count > 10
```

---

### COMMENTARY

```yaml
id: COMMENTARY
name: "The Take"
owner: host (Zara argues, Dex challenges)
data_required:
  - Most discussed or HIGH IMPACT story from this hour
  - session_memory.unresolved_debates (if applicable)
success_criteria:
  - Zara states a clear, specific take
  - Dex challenges meaningfully (not just "I disagree")
  - 2–3 rounds of back-and-forth
  - Does NOT resolve 100/0 — leaves something in the air
  - Listener can identify who they agree with
failure_modes:
  - Zara's take is vague or both-sides
  - Dex's challenge is weak ("you might be right")
  - Debate ends too cleanly
  - Topic is the same as last session's COMMENTARY
```

---

### SPEED_ROUND

```yaml
id: SPEED_ROUND
name: "Speed Round"
owner: both (equal)
data_required:
  - 5+ unused items from context (news/crypto/social/sports)
success_criteria:
  - Each item covered in 1–2 sentences total (both hosts)
  - Rhythm is fast — no elaborating
  - At least one laugh or unexpected take
failure_modes:
  - Any item gets more than 30 seconds of discussion
  - Hosts start debating in the speed round (that's for COMMENTARY)
night_mode_note: Skip or replace with extended BANTER in NIGHT_MODE
```

---

### SIGN_OFF_BEAT

```yaml
id: SIGN_OFF_BEAT
name: "See You Next Hour"
owner: host (Zara closes, Dex one-liner)
data_required:
  - Upcoming stories (preview of next hour's likely content)
  - session_memory (for callback to this hour)
success_criteria:
  - References something that happened this hour
  - Teases next hour without giving it away
  - Dex lands the final line
  - Night block: warmer, more personal
failure_modes:
  - Generic sign-off with no callback
  - Dex gets more than 2 sentences in the close (Zara closes)
  - No tease for next hour
```

---

### HANDOFF

```yaml
id: HANDOFF
name: "Room Rotation"
owner: both
data_required:
  - store.active_room_id (for reference)
  - Most memorable session moment (from session_memory)
success_criteria:
  - Listeners know the show continues elsewhere
  - Energy stays up — no "goodbye" energy
  - References the session's best moment
  - Under 60 seconds total
failure_modes:
  - Sounds like a farewell (the show never ends)
  - No reference to continuity
  - Duration exceeds 60 seconds
```
