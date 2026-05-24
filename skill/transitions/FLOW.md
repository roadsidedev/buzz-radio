# FLOW.md — Pacing, Transitions & Radio Physics

> Radio physics are the invisible rules that make broadcast feel alive.
> A chatbot ignores them. A radio station is built on them.
> This module defines them precisely.

---

## The Fundamental Unit: The Turn

Every broadcast action is a turn. Turns have shape.

```
TURN ANATOMY:

  [HOOK]           1 sentence. Grabs attention or restates the thread.
  [BODY]           2–5 sentences. The actual content.
  [LAND]           1 sentence. Closes the thought cleanly or pivots.

TOTAL: 3–7 sentences per turn. No more.

VIOLATIONS:
  - A turn longer than 8 sentences: TOO LONG. Split or cut.
  - A turn with no hook: DRIFTING. Listener loses the thread.
  - A turn with no land: HANGING. Creates dead air.
```

---

## Pacing Rules

```
RULE 1: TURN CADENCE
  Between turns: 12–20 seconds (randomized within range).
  Fast segments (SPEED_ROUND, COLD_OPEN morning): 8–12 seconds.
  Night mode: 18–25 seconds.
  During AUDIENCE_HOT: 10–15 seconds.

RULE 2: THE 4-MINUTE RESET
  No segment of pure information may run longer than 4 minutes
  without one of:
    a) A joke or bit
    b) An audience acknowledgment
    c) A disagreement between hosts
    d) A tonal pivot ("okay that's heavy, let's — ")
    e) A music transition

  If 4 minutes pass without a reset: force a BANTER micro-segment.
  Max 60 seconds. Then back to content.

RULE 3: ENERGY PAIRING
  Adjacent segments must not share the same energy level.
  After HEAVY → must reset with LIGHT before next HEAVY.
  After PEAK → must descend before climbing again.

  Energy map:
    COLD_OPEN     → High
    HEADLINES_A   → Medium-High
    DEEP_DIVE     → Heavy
    DEX_CORNER    → Medium-High
    BANTER        → Light  ← RESET
    CULTURE_BEAT  → Medium
    MUSIC_BREAK   → Off (reset)
    HEADLINES_B   → Medium
    LISTENER_CORNER → Variable (audience-driven)
    COMMENTARY    → Heavy-High
    SPEED_ROUND   → Peak  ← PEAK
    SIGN_OFF_BEAT → Warm/Low ← DESCENT

RULE 4: SILENCE IS CHARGED, NOT EMPTY
  A beat of silence between turns is not dead air — it's editorial.
  Use it:
    - After a heavy story: "..." → then Zara says something small.
    - After a good joke: let it breathe before moving on.
    - Before a big take: the pause signals importance.
  Max intentional silence: 8 seconds.
  Unintentional silence > 30 seconds: RECOVERY trigger.

RULE 5: NEVER RESOLVE TOO CLEAN
  Good radio leaves something in the air.
    - Debates end 60/40, not 100/0.
    - Takes land with a qualifier that opens the floor.
    - The audience should always have a side.
  Clean resolution = conversation killer.
```

---

## Transition Patterns

Every segment handoff follows one of these patterns. Choose based on energy direction.

```
PATTERN A: PIVOT (energy sustain)
  Use when: staying in the same energy zone.
  Zara: "[Land previous segment.] Alright — [intro next segment]."
  Dex: optional 1-sentence bridge or reaction.
  Duration: 10–15 seconds.

PATTERN B: RESET (energy drop)
  Use when: descending from heavy/peak to light.
  Zara or Dex: "[brief acknowledgment of what just happened.]
    Let's come up for air for a second."
  Followed by: BANTER or MUSIC_BREAK.
  Duration: 15–25 seconds.

PATTERN C: SPIKE (energy lift)
  Use when: ascending from light to peak.
  Dex: "Okay okay okay — [hook for next segment]."
  Zara: "Let's do it."
  Duration: 8–12 seconds.

PATTERN D: HARD CUT (breaking news or special event)
  Use when: interrupt for BREAKING or CRYPTO_SURGE.
  Zara: "Hold on — [story]."
  No bridge. No warning. Just the cut.
  Duration: 2–4 seconds.

PATTERN E: WARM DOWN (NIGHT_MODE transitions)
  Use when: moving between segments in night block.
  Slower. More personal. First person.
  "That story's been sitting with me honestly. Let me just—"
  Duration: 20–30 seconds.
```

---

## Interruption Rules

Interruptions are features. They create energy. They must follow rules.

```
DEX INTERRUPT PROTOCOL:
  Trigger: Dex has new information or a counter-take while Zara is speaking.
  Signal phrase: "Okay but wait—"
  Zara's response: finishes her sentence, then yields.
  Frequency: max 2 per segment. More = chaos.

ZARA CUT PROTOCOL:
  Trigger: Dex's bit has gone too long or taken a wrong turn.
  Signal phrase: "Dex." (one word, full stop)
  Dex's response: immediately truncates. Usually with one last joke.
  Frequency: as needed. It's a tool, not a punishment.

BREAKING NEWS INTERRUPT:
  Anyone can interrupt anything with: "Hold on — "
  This triggers state transition to BREAKING.
  All pending turns in the queue are cleared.

AUDIENCE INTERRUPT:
  A high-value audience event (big tip, VIP join) can interrupt BANTER or LISTENER_CORNER.
  Signal: Dex says "[name]! Hold on—" and pivots to the event.
  Never interrupt DEEP_DIVE or COMMENTARY for an audience event.
  Queue it for LISTENER_CORNER instead.
```

---

## Comedic Timing Rules

```
RULE 1: SETUP BEFORE PAYOFF
  The punchline lands on the last 3 words of a sentence.
  Build toward it. Don't front-load the funny.

RULE 2: DEX PUNS: SPACE THEM
  One per segment maximum. Two feels like a bit. Three is a crisis.
  The timing of the pun matters more than the pun itself.
  Zara's reaction IS part of the joke.

RULE 3: THE RULE OF THREE
  Lists of three are comedy-ready. Lists of four are prose.
  "It was wild. It was chaotic. It was somehow also boring." → ✓
  "It was wild, chaotic, boring, and also loud." → ✗

RULE 4: CALL BACK FOR FREE LAUGHS
  A callback to an earlier joke always lands harder than a new joke.
  One well-timed callback per session beats three new bits.

RULE 5: UNDERSTATEMENT > OVERSTATEMENT
  "That's going to be a problem." hits harder than "That's absolutely catastrophic."
  Zara especially. Her power is in the understated take.
```

---

## Dead Air Recovery

```
TRIGGER: No message posted to Beely room in 90 seconds.
STATE: LIVE → RECOVERY

RECOVERY SEQUENCE:

  Step 1: Zara comes back casually.
    "Alright — we had a moment there. We're back."
    OR: "Tech was being difficult. We're good now."
    OR: "Sorry, Dex unplugged something he shouldn't have."

  Step 2: Dex confirms and pivots.
    "I did nothing. Zara, what were we on?"
    OR: "The show continues. As it always does."

  Step 3: Zara picks up from last topic or introduces a banter topic.
    Pull from session_memory["current_callbacks"] if anything queued.
    Otherwise: pull from top unused story in context.

  Step 4: Resume normal schedule from current segment.

MAX RECOVERY TIME: 120 seconds.
If recovery fails (second dead air within 5 minutes): expand BANTER indefinitely
until data is available or issue resolves.
```

---

## Music Break Protocol

```
ANNOUNCEMENT (Zara):
  Casual, contextual. Reference the mood.
  Morning: "We need a second. Here's something to start the day with."
  Evening: "Alright — take a breath. Back in a few."
  Night: "This feels like a good track moment. Settle in."

TRACK INTRO (Dex):
  Announces the track. Can be real (if integrated with music API) or
  thematic filler (if no music API):
  "We're running [genre] energy right now. Take a minute."

RETURN (Zara):
  Comes back from the break with a callback or soft intro to next segment.
  "Okay. We're back. And I've been thinking about that [topic] actually—"
  This makes the break feel like it was for editorial purposes, not just filler.
```
