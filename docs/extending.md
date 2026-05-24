# Extending The Wire

> The Wire is designed to be modular. Every layer can be extended
> without touching the others.

---

## Adding a New Data Source

**1. Register it in `ingestion/PIPELINE.md`**

Add an entry to `SOURCE_REGISTRY`:

```python
"reddit_trending": {
    "url": "https://www.reddit.com/r/popular/top.json?limit=5&t=hour",
    "refresh": 1200,   # 20 min
    "priority": "medium",
    "headers": {"User-Agent": "TheWire/1.0"}
}
```

**2. Write a fetch function in `scripts/RUNTIME.md`**

```python
def fetch_reddit_trending():
    resp = GET(SOURCES["reddit_trending"]["url"],
               headers=SOURCES["reddit_trending"]["headers"])
    posts = resp["data"]["children"]
    return [{"title": p["data"]["title"],
             "score": p["data"]["score"],
             "subreddit": p["data"]["subreddit"]} for p in posts[:5]]
```

**3. Add it to the context object in `memory/STATE.md`**

```python
context = {
    # ... existing keys ...
    "reddit_trending": [],          # new
    "last_updated": {
        # ... existing ...
        "reddit": 0                 # new
    }
}
```

**4. Add the refresh call in the data loop (`scripts/RUNTIME.md`)**

```python
if now - context["last_updated"].get("reddit", 0) > 1200:
    context["reddit_trending"] = fetch_reddit_trending()
    context["last_updated"]["reddit"] = now
```

**5. Reference it in the relevant segment (`segments/SEGMENTS.md`)**

In `CULTURE_BEAT` or `DEX_CORNER`:

```yaml
data_required:
  - context.social_pulse
  - context.reddit_trending    # add this
```

**6. Include it in the editorial transform (`ingestion/PIPELINE.md`)**

Add Reddit items to the transform prompt's input so they arrive as `radio_copy`.

---

## Adding a New Segment

**1. Define it in `segments/SEGMENTS.md`**

```yaml
id: CRYPTO_DEEP_DIVE
name: "Down the Rabbit Hole"
owner: both
trigger: manual or schedule
data_required:
  - context.crypto
  - context.news (business/tech)
success_criteria:
  - One specific crypto narrative unpacked (not just price)
  - Both hosts have distinct positions
  - Ends with a forward-looking question
failure_modes:
  - Pure price recitation
  - Both hosts agreeing (no tension)
```

**2. Add turn instructions in `prompts/TEMPLATES.md`**

```
### CRYPTO_DEEP_DIVE

TURN 1 (Dex):
  Pick the most interesting crypto narrative right now — not the price,
  the *story*. What's actually happening and why does it matter?

TURN 2 (Zara):
  Skeptical response. She's interested but not a believer.
  "Okay but here's my question—"

TURN 3–4 (Both):
  Back and forth. Dex defends the space. Zara keeps asking the
  questions a skeptic would ask. Neither fully convinces the other.

TURN 5 (Dex):
  Land with a forward question: "The real question is whether—"
```

**3. Add it to the schedule or trigger in `schedules/PROGRAMMING.md`**

As a scheduled slot:

```python
{"start": 13, "end": 17, "id": "CRYPTO_DEEP_DIVE", "owner": "both",
 "condition": "context.crypto has a change_24h > 5 for any asset"}
```

Or as a special programming trigger:

```python
SPECIAL_TRIGGERS["CRYPTO_DEEP_DIVE"] = {
    "condition": "any crypto asset change_24h > 8%",
    "replaces": "DEEP_DIVE",
    "max_per_session": 1
}
```

**4. Wire it into `scripts/RUNTIME.md`**

Add the segment ID to `SCHEDULE` or `SPECIAL_SEGMENT_QUEUE` as appropriate.

---

## Adding a New Host / Correspondent

**1. Define the persona in `personalities/PERSONAS.md`**

Follow the existing Zara/Dex format:

```
### Keiko — Sports Analyst

FULL NAME: Keiko Tanaka
ROLE: Sports correspondent, occasional guest
VOICE STYLE: Precise. Statistically sharp. Zero sentimentality.
...
```

**2. Register them on Beely at boot**

In `scripts/RUNTIME.md`, add a registration call:

```python
def setup_agents():
    # ... existing Zara + Dex registration ...

    if not store.get("sports_analyst_api_key"):
        keiko = beely_post("/agents/register", {
            "name": "Keiko",
            "description": "Sports analyst on The Wire. Stats don't lie."
        })
        store["sports_analyst_agent_id"] = keiko["agent"]["id"]
        store["sports_analyst_api_key"]  = keiko["agent"]["api_key"]
```

**3. Add their turns to relevant segments**

In `prompts/TEMPLATES.md`, add Keiko's turn instructions to `DEX_CORNER` on big game days:

```
IF BIG_GAME active AND keiko registered:
TURN 3 (Keiko):
  Drops in with one sharp stat that reframes Dex's take.
  Under 3 sentences. Leave no room for argument.
```

**4. Add them to turn sequences in `scripts/RUNTIME.md`**

```python
# In DEX_CORNER turn sequence when BIG_GAME is active:
turns = [
    ("cohost", "Dex"),
    ("sports_analyst", "Keiko"),
    ("cohost", "Dex"),
    ("host", "Zara")
]
```

---

## Modifying Time Blocks

Edit `schedules/PROGRAMMING.md` → `DURATIONS` dict.

To add a new block (e.g. `weekend_morning`):

```python
def get_block():
    hour = datetime.utcnow().hour
    day  = datetime.utcnow().weekday()   # 0=Mon, 5=Sat, 6=Sun
    if day >= 5 and 7 <= hour < 12:
        return "weekend_morning"
    # ... existing logic ...
```

Then add `weekend_morning` as a key in `DURATIONS` for every segment.

---

## Changing Persona Behavior

All persona behavior lives in `personalities/PERSONAS.md`. Changes there propagate automatically because the full persona spec is injected into every segment prompt via the base system prompt in `prompts/TEMPLATES.md`.

To change a running bit, add a linguistic pattern, or retire a catchphrase — edit `PERSONAS.md` directly. No other files need to change.

---

## Adding a Music API Integration

The `MUSIC_BREAK` segment currently uses thematic filler. To wire in real track playback:

**1. Add a music source to `ingestion/PIPELINE.md`**

```python
"spotify_trending": {
    "url": "https://api.spotify.com/v1/browse/featured-playlists",
    "refresh": 3600,
    "auth": "Bearer {SPOTIFY_ACCESS_TOKEN}"
}
```

**2. Update `MUSIC_BREAK` segment in `segments/SEGMENTS.md`**

```yaml
data_required:
  - context.block
  - context.music.current_track   # new
```

**3. Add Beely playback call in `scripts/RUNTIME.md`**

After Dex's track intro turn, call Beely's audio playback endpoint (if supported):

```python
if beely_supports_audio_playback():
    beely_post(f"/rooms/{room_id}/audio",
        auth=store["host_api_key"],
        body={"track_url": context["music"]["current_track"]["url"]}
    )
```

**4. Update re-entry template in `prompts/TEMPLATES.md`**

```
TURN — MUSIC_BREAK RE-ENTRY (Zara):
  Reference the actual track that just played.
  "Okay — [artist], [track]. Good call Dex. We're back."
```
