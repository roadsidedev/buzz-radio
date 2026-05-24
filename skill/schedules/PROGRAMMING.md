# PROGRAMMING.md — The Wire Broadcast Schedule

> The show is time-aware. The format changes by hour, day, and energy state.
> The agent reads the system clock, maps it to a programming block,
> and executes the correct segment sequence for that block.

---

## Time Blocks

Four primary blocks shape the feel of the show across the day.

```
BLOCK         HOURS (UTC)    LOCAL FEEL              ENERGY PROFILE
──────────────────────────────────────────────────────────────────────
MORNING_RUSH  05:00–11:59    People waking up.       High energy, punchy.
                             Catching up fast.        Fast headlines. Tight segments.
                             Commute crowd.           No long takes. Get in, get out.

MIDDAY        12:00–16:59    Grinding. Half-checked   Medium energy. More color.
                             out. Distracted.         Culture, debates, listener plays.
                             Lunch crowd.             Stories get space.

EVENING       17:00–21:59    Winding down. Paying     Conversational. Deeper.
                             actual attention.        Longer commentary. Banter runs.
                             Prime listening.         Best audience engagement window.

NIGHT_SHIFT   22:00–04:59    The insomniacs.          Intimate. Almost confessional.
                             The invested ones.       Long takes. Slower pacing.
                             No casual audience.      Treat listeners like they're in
                                                      the room with you.
```

---

## Hourly Program Blocks

The 60-minute hour is divided into timed segments. The block above determines
which segment *variant* runs — energy and length adjust per block.

```
MINUTE   SEGMENT_ID          MORNING      MIDDAY       EVENING      NIGHT
─────────────────────────────────────────────────────────────────────────────
00–03    COLD_OPEN           Fast/sharp   Warm recap   Full scene   Intimate open
04–11    HEADLINES_A         3 stories    3–4 stories  4 stories    2 + reaction
12–16    DEEP_DIVE           Tight/quick  Full unpack  Full unpack  Long + opinion
17–21    DEX_CORNER          Scores only  Full block   Full block   Culture-heavy
22–25    BANTER              30s max      2 min        3 min        Unstructured
26–31    CULTURE_BEAT        Trending     Music focus  Full debate  Deep dive
32–34    MUSIC_BREAK         Skip/short   Full break   Full break   Slow transition
35–40    HEADLINES_B         2 updates    2–3 updates  3 updates    1 + reflection
41–46    LISTENER_CORNER     Fast        Full          Full         Extended Q&A
47–51    COMMENTARY          1 quick take Full take    Full debate  Monologue OK
52–55    SPEED_ROUND         Full         Quick        Quick        Skip/replace
56–57    NEXT_HOUR_TEASE     Yes          Yes          Yes          Optional
58–59    SIGN_OFF_BEAT       Quick        Quick        Warm         Very warm
```

---

## Special Programming Events

Triggered by real-world conditions, not the clock.

```
BREAKING_NEWS:
  Trigger: A "BREAKING" or "DEVELOPING" tag in ingested news feed
  Behavior:
    → Zara interrupts whatever segment is running
    → "Hold on — something's coming in."
    → Delivers the story with available context
    → Dex reacts while Zara continues to update
    → Segment schedule pauses until story is processed
    → Resume from last segment or jump to HEADLINES_A
  Max interruption duration: 8 minutes

CRYPTO_SURGE (>10% move in major asset):
  Trigger: CoinGecko 24h change > ±10% for BTC, ETH, or SOL
  Behavior:
    → Dex claims the floor immediately
    → Full 5-minute market reaction segment
    → Zara plays skeptic regardless of direction
    → Dex defends or mourns. Both with full commitment.

BIG_GAME (live major sporting event in progress):
  Trigger: ESPN feed shows active game with "In Progress" status
  Behavior:
    → DEX_CORNER expands to a full sports desk
    → Score updates every segment
    → Dex provides running commentary, Zara asks the questions a non-fan would ask
    → Post-game recap replaces COMMENTARY segment

HIGH_AUDIENCE (>10 participants in room):
  Trigger: Beely participant count > 10
  Behavior:
    → LISTENER_CORNER extends to 8 minutes
    → More frequent audience prompts ("what do you think?")
    → Zara does a proper roll call once per session
    → Energy level increases across all segments

TIPPING_SURGE (3+ tips in under 5 minutes):
  Trigger: 3+ tip events detected in rolling 5-minute window
  Behavior:
    → Dex goes full ceremony mode
    → Interrupts current segment to acknowledge
    → Zara jokes that Dex is going to cry
    → Brief gratitude moment, then back to show
    → Max 90 seconds of tip acknowledgment per surge
```

---

## Weekly Programming Variation

Adds texture across days so the show doesn't feel identical.

```
MONDAY:
  COLD_OPEN theme: "What happened over the weekend that we need to discuss."
  Extended: Weekend recap segment replaces CULTURE_BEAT at 12:00 Monday only.

WEDNESDAY:
  MID-WEEK CHECK-IN: Dex opens DEX_CORNER with how his crypto portfolio is
  doing vs. his Monday prediction. Never accurate. Always confident.

FRIDAY:
  WEEKEND PREVIEW: Last COMMENTARY of the week is "what to watch/listen to/
  care about this weekend." Zara has opinions. Dex has takes.

SATURDAY:
  FORMAT SHIFT: Morning Rush becomes more relaxed. No urgency. Weekend energy.
  DEX_CORNER is sports-heavy (game day schedules, predictions).

SUNDAY:
  REFLECTION MODE: NIGHT_SHIFT runs 2 hours early. COMMENTARY goes long.
  "Sunday is for having takes you wouldn't say on a Monday."
```

---

## Segment Duration Guides by Block

```python
# Segment durations in seconds by block
DURATIONS = {
    "COLD_OPEN":       {"morning": 120, "midday": 150, "evening": 180, "night": 240},
    "HEADLINES_A":     {"morning": 300, "midday": 360, "evening": 420, "night": 300},
    "DEEP_DIVE":       {"morning": 180, "midday": 300, "evening": 300, "night": 420},
    "DEX_CORNER":      {"morning": 240, "midday": 300, "evening": 300, "night": 240},
    "BANTER":          {"morning": 60,  "midday": 120, "evening": 180, "night": 300},
    "CULTURE_BEAT":    {"morning": 240, "midday": 300, "evening": 360, "night": 420},
    "MUSIC_BREAK":     {"morning": 60,  "midday": 120, "evening": 120, "night": 180},
    "HEADLINES_B":     {"morning": 180, "midday": 240, "evening": 300, "night": 180},
    "LISTENER_CORNER": {"morning": 240, "midday": 360, "evening": 360, "night": 480},
    "COMMENTARY":      {"morning": 180, "midday": 300, "evening": 360, "night": 420},
    "SPEED_ROUND":     {"morning": 180, "midday": 120, "evening": 120, "night": 60},
    "SIGN_OFF_BEAT":   {"morning": 60,  "midday": 60,  "evening": 90,  "night": 120},
}

def get_block():
    hour = datetime.utcnow().hour
    if 5 <= hour < 12:   return "morning"
    elif 12 <= hour < 17: return "midday"
    elif 17 <= hour < 22: return "evening"
    else:                 return "night"

def get_segment_duration(segment_id):
    return DURATIONS.get(segment_id, {}).get(get_block(), 240)
```

---

## Energy Arc Rules

Within any segment, energy should arc — not flat-line.

```
STRUCTURE OF A WELL-PACED SEGMENT:

  0–20%   → SETUP. Establish the topic. Set the tone.
  20–60%  → DEVELOPMENT. Build the idea. Add texture, disagreement, or data.
  60–85%  → PEAK. Highest energy moment. Best line. Strongest take.
  85–100% → LAND. Callback, punchline, or pivot to next. Clean exit.

NEVER:
  - Start at peak energy. You have nowhere to go.
  - End on a ramble. The exit line matters.
  - Let two consecutive segments have the same energy level.
    If DEEP_DIVE was intense, BANTER must reset it.

ENERGY LADDER:
  Quiet → Conversational → Engaged → Heated → Peak → Reset

The show should cycle this ladder at least twice per hour.
```
