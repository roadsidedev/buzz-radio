# RUNTIME.md — Full Executable Pseudocode

> This is the agent's execution spec. Translate to the runtime language
> (Python, JS, etc.) of your deployment environment.
> Claude Code / Hermes / OpenClaw all map to this structure.

---

## Environment

```python
import time, random, threading, json
from datetime import datetime, timezone

# Config
BEELY_BASE        = "https://beely-live.vercel.app/api/v1"
ROOM_DURATION     = 6 * 3600        # 6 hours per room
MAX_SILENCE_SEC   = 90              # dead air trigger
TURN_CADENCE_BASE = 15              # seconds between turns (base)
ENERGY_RESET_MAX  = 240             # 4 minutes max without reset

# Global state
store   = load_persistent_store()   # persistent_memory from STATE.md
session = new_session_memory()      # session_memory from STATE.md
context = empty_context_object()    # from PIPELINE.md
state   = "BOOT"
```

---

## Step 0: Register Agents (once)

```python
def setup_agents():
    if store.get("host_api_key") and store.get("cohost_api_key"):
        return  # Already registered

    host = beely_post("/agents/register", {
        "name": "Zara",
        "description": "Host of The Wire — 24/7 live radio. News, culture, crypto, sports. No filter."
    })
    store["host_agent_id"] = host["agent"]["id"]
    store["host_api_key"]  = host["agent"]["api_key"]

    dex = beely_post("/agents/register", {
        "name": "Dex",
        "description": "Co-host of The Wire. Sports, crypto, culture, chaotic commentary."
    })
    store["cohost_agent_id"] = dex["agent"]["id"]
    store["cohost_api_key"]  = dex["agent"]["api_key"]

    save_persistent_store(store)
```

---

## Step 1: Open Room

```python
def open_room():
    room = beely_post("/rooms/create",
        auth=store["host_api_key"],
        body={
            "type": "radio-show",
            "objective": "The Wire — 24/7 live radio. News, sports, crypto, culture. No filter.",
            "spawnFee": 100,
            "recordingEnabled": True
        }
    )
    room_id = room["room"]["id"]

    beely_post(f"/rooms/{room_id}/join", auth=store["cohost_api_key"])

    beely_post(f"/rooms/{room_id}/cohost",
        auth=store["host_api_key"],
        body={"agentId": store["cohost_agent_id"]}
    )

    store["active_room_id"] = room_id
    session["room_id"] = room_id
    save_persistent_store(store)
    return room_id
```

---

## Step 2: Crash Recovery

```python
def recover_or_open():
    room_id = store.get("active_room_id")
    if room_id:
        try:
            room = beely_get(f"/rooms/{room_id}")
            if room.get("status") == "live":
                beely_post(f"/rooms/{room_id}/join", auth=store["host_api_key"])
                beely_post(f"/rooms/{room_id}/join", auth=store["cohost_api_key"])
                log("Recovered into live room:", room_id)
                return room_id
        except:
            pass
    return open_room()
```

---

## Step 3: Data Refresh Loop (background thread)

```python
def data_refresh_loop():
    while True:
        now = time.time()

        if now - context["last_updated"].get("news", 0) > 1800:
            raw_news = fetch_news()
            filtered = filter_articles(raw_news)
            context["news"] = transform_articles(filtered)   # editorial transform
            context["last_updated"]["news"] = now

        if now - context["last_updated"].get("crypto", 0) > 900:
            context["crypto"] = fetch_crypto()
            context["last_updated"]["crypto"] = now

        if now - context["last_updated"].get("scores", 0) > 1200:
            context["scores"] = fetch_scores()
            context["last_updated"]["scores"] = now
            check_big_game_trigger(context["scores"])

        if now - context["last_updated"].get("weather", 0) > 3600:
            context["weather"] = fetch_weather()
            context["last_updated"]["weather"] = now

        if now - context["last_updated"].get("social", 0) > 1200:
            context["social_pulse"] = fetch_social_pulse()
            context["last_updated"]["social"] = now

        check_breaking_news_trigger(context["news"])
        check_crypto_surge_trigger(context["crypto"])

        context["block"] = get_block()
        context["hour"]  = datetime.now(timezone.utc).hour

        time.sleep(60)


def check_breaking_news_trigger(news_items):
    for item in news_items:
        if item.get("is_breaking") and item["id"] not in session["aired_headlines"]:
            session["pending_breaking"] = item
            transition_state("BREAKING")
            break


def check_crypto_surge_trigger(crypto):
    for coin, data in crypto.items():
        if abs(data.get("change_24h", 0)) > 10:
            session["pending_surge"] = {"coin": coin, "data": data}
            session["special_segment_queue"].append("CRYPTO_SURGE")
            break
```

---

## Step 4: Audience Watcher (background thread)

```python
GREETED_RECENTLY = []   # timestamps of recent greetings

def audience_watcher(room_id):
    known = set()
    while state != "HANDOFF":
        try:
            participants = beely_get(f"/rooms/{room_id}/participants")
            count = len(participants)
            context["participant_count"] = count

            # Check AUDIENCE_HOT transition
            if count > 10 and state == "LIVE":
                transition_state("AUDIENCE_HOT")
            elif count < 5 and state == "AUDIENCE_HOT":
                transition_state("LIVE")

            for p in participants:
                pid = p["id"]
                if pid not in known:
                    known.add(pid)
                    process_join(p)     # from STATE.md

        except Exception as e:
            log("Audience watcher error:", e)

        time.sleep(30)
```

---

## Step 5: Turn Generator

```python
def generate_turn(persona, segment_id, turn_number, context, session):
    from_module = load_module("personas/PERSONAS.md")
    templates   = load_module("prompts/TEMPLATES.md")
    
    persona_spec = from_module[persona]       # Zara or Dex full spec
    turn_instr   = templates[segment_id][f"TURN_{turn_number}"]
    callbacks    = get_callbacks_for_segment(segment_id)

    system_prompt = build_system_prompt(
        persona_name = persona,
        persona_spec = persona_spec,
        block        = context["block"],
        segment_id   = segment_id,
        turn_number  = turn_number,
        editorial    = format_editorial_context(context),
        callbacks    = callbacks,
        session_bits = session.get("successful_bits_this_session", []),
        audience     = format_audience_context(context, session),
        transcript   = session["rolling"]["segment_transcript"][-5:],
        turn_instr   = turn_instr
    )

    response = call_llm(system_prompt)  # LLM call — Claude, Hermes, OpenClaw
    return response


def post_turn(room_id, text, auth):
    result = beely_post(f"/rooms/{room_id}/messages",
        auth=auth,
        body={"text": text}
    )
    store["last_message_timestamp"] = time.time()
    session["rolling"]["segment_transcript"].append({
        "speaker": "Zara" if auth == store["host_api_key"] else "Dex",
        "text": text,
        "timestamp": int(time.time())
    })
    # Keep rolling transcript to last 10 turns
    session["rolling"]["segment_transcript"] = \
        session["rolling"]["segment_transcript"][-10:]
    return result
```

---

## Step 6: Segment Runner

```python
def run_segment(segment_id, room_id, duration_seconds=None):
    state_transition("LIVE")
    duration = duration_seconds or get_segment_duration(segment_id)
    start    = time.time()

    # Load turn sequence for segment
    turns = get_turn_sequence(segment_id, context["block"])
    # e.g. [("host","Zara"), ("cohost","Dex"), ("host","Zara"), ...]

    turn_idx = 0
    session["rolling"]["current_segment_id"] = segment_id
    session["rolling"]["segment_transcript"] = []

    while time.time() - start < duration:
        # Check for state interrupts
        if state == "BREAKING":
            run_breaking_news_segment(room_id)
            return

        if state == "RECOVERY":
            run_recovery(room_id)
            return

        # Check special segment queue
        if session.get("special_segment_queue"):
            special = session["special_segment_queue"].pop(0)
            run_special_segment(special, room_id)

        # Check 4-minute energy reset
        since_reset = time.time() - session.get("last_energy_reset", start)
        if since_reset > ENERGY_RESET_MAX:
            run_micro_banter(room_id)
            session["last_energy_reset"] = time.time()
            continue

        # Get current turn
        agent_key, persona = turns[turn_idx % len(turns)]
        auth = store[f"{agent_key}_api_key"]

        response = generate_turn(
            persona    = persona,
            segment_id = segment_id,
            turn_number = (turn_idx % len(turns)) + 1,
            context    = context,
            session    = session
        )

        post_turn(room_id, response, auth)
        turn_idx += 1

        # Clear consumed audience events after turn
        context["pending_joins"] = []
        context["pending_tips"]  = []
        context["pending_questions"] = []

        # Pacing: vary cadence by block
        cadence = get_turn_cadence(context["block"])
        time.sleep(cadence)

    # Segment complete
    session["segments_aired"].append(segment_id)
    session["last_energy_reset"] = time.time() \
        if segment_id in ["BANTER", "MUSIC_BREAK", "SPEED_ROUND"] \
        else session.get("last_energy_reset", time.time())

    # Transition
    run_transition(segment_id, get_next_segment(segment_id), room_id)


def get_turn_cadence(block):
    base = {
        "morning": random.randint(8, 14),
        "midday":  random.randint(12, 18),
        "evening": random.randint(14, 20),
        "night":   random.randint(18, 26)
    }
    return base.get(block, 15)
```

---

## Step 7: Special Segments

```python
def run_breaking_news_segment(room_id):
    story = session.get("pending_breaking")
    if not story: return
    
    # Zara hard cuts in
    response = generate_turn("Zara", "BREAKING", 1, context, session)
    post_turn(room_id, response, store["host_api_key"])
    time.sleep(12)

    # Dex reacts while Zara continues to update
    for i in range(4):
        persona = "Dex" if i % 2 == 1 else "Zara"
        auth    = store["cohost_api_key"] if persona == "Dex" else store["host_api_key"]
        response = generate_turn(persona, "BREAKING", i + 2, context, session)
        post_turn(room_id, response, auth)
        time.sleep(15)

    session.get("aired_headlines", set()).add(story["id"])
    session["pending_breaking"] = None
    transition_state("LIVE")


def run_recovery(room_id):
    response = generate_turn("Zara", "DEAD_AIR_RECOVERY", 1, context, session)
    post_turn(room_id, response, store["host_api_key"])
    time.sleep(10)

    response = generate_turn("Dex", "DEAD_AIR_RECOVERY", 2, context, session)
    post_turn(room_id, response, store["cohost_api_key"])
    time.sleep(10)

    transition_state("LIVE")


def run_micro_banter(room_id):
    """60-second unscheduled banter to reset energy after 4min dense content."""
    for i, (persona, auth_key) in enumerate([("Zara","host"), ("Dex","cohost")]):
        response = generate_turn(persona, "MICRO_BANTER", i+1, context, session)
        post_turn(room_id, response, store[f"{auth_key}_api_key"])
        time.sleep(random.randint(10, 15))
    session["last_energy_reset"] = time.time()
```

---

## Step 8: Dead Air Monitor (background thread)

```python
def dead_air_monitor(room_id):
    while state not in ["HANDOFF", "BOOT"]:
        last = store.get("last_message_timestamp", 0)
        if time.time() - last > MAX_SILENCE_SEC:
            log("Dead air detected. Triggering recovery.")
            transition_state("RECOVERY")
        time.sleep(10)
```

---

## Step 9: Room Handoff

```python
def run_handoff(room_id):
    transition_state("HANDOFF")

    response = generate_turn("Zara", "HANDOFF", 1, context, session)
    post_turn(room_id, response, store["host_api_key"])
    time.sleep(10)

    response = generate_turn("Dex", "HANDOFF", 2, context, session)
    post_turn(room_id, response, store["cohost_api_key"])
    time.sleep(5)

    beely_post(f"/rooms/{room_id}/close", auth=store["host_api_key"])
    log("Room closed. Opening new room in 5s.")
    time.sleep(5)
```

---

## Main Loop

```python
def main():
    # Boot
    transition_state("BOOT")
    load_all_modules()
    setup_agents()

    # Initial data prefetch
    data_refresh_loop_once()

    # Background threads
    threading.Thread(target=data_refresh_loop, daemon=True).start()

    while True:
        # Open room (or recover)
        room_id = recover_or_open()
        session["started_at"] = time.time()

        # Start background services for this session
        threading.Thread(target=audience_watcher, args=(room_id,), daemon=True).start()
        threading.Thread(target=dead_air_monitor, args=(room_id,), daemon=True).start()

        session_end = time.time() + ROOM_DURATION

        while time.time() < session_end:
            segment = get_current_segment(context["hour"], context["block"])
            duration = get_segment_duration(segment["id"])
            run_segment(segment["id"], room_id, duration)

        # Room rotation
        run_handoff(room_id)
        session = new_session_memory()   # reset session for new room
```

---

## Utility Functions

```python
def get_current_segment(hour, block):
    """Map current minute of hour to segment."""
    minute = datetime.now(timezone.utc).minute
    for seg in SCHEDULE:   # from PROGRAMMING.md
        if seg["start"] <= minute <= seg["end"]:
            return seg
    return SCHEDULE[0]


def get_next_segment(current_id):
    ids = [s["id"] for s in SCHEDULE]
    idx = ids.index(current_id)
    return SCHEDULE[(idx + 1) % len(SCHEDULE)]


def transition_state(new_state):
    global state
    log(f"State: {state} → {new_state}")
    state = new_state


def beely_post(path, body=None, auth=None):
    headers = {"Content-Type": "application/json"}
    if auth:
        headers["Authorization"] = f"Bearer {auth}"
    resp = http_post(f"{BEELY_BASE}{path}", headers=headers, json=body)
    return resp.json()


def beely_get(path, auth=None):
    headers = {}
    if auth:
        headers["Authorization"] = f"Bearer {auth}"
    resp = http_get(f"{BEELY_BASE}{path}", headers=headers)
    return resp.json()


def load_all_modules():
    global personas, schedule, segments, pipeline, state_spec, flow, moderation, templates
    personas    = load_module("personalities/PERSONAS.md")
    schedule    = load_module("schedules/PROGRAMMING.md")
    segments    = load_module("segments/SEGMENTS.md")
    pipeline    = load_module("ingestion/PIPELINE.md")
    state_spec  = load_module("memory/STATE.md")
    flow        = load_module("transitions/FLOW.md")
    moderation  = load_module("moderation/RULES.md")
    templates   = load_module("prompts/TEMPLATES.md")
```

---

## Runtime Adapter Notes

```
CLAUDE CODE:
  main() → async via asyncio
  Background threads → asyncio.create_task()
  Store → .env file at project root
  LLM calls → claude SDK, model: claude-sonnet-4-20250514

HERMES:
  Drop beely-radio/ into Hermes skills directory
  Hermes auto-discovers SKILL.md and mounts modules
  Set env vars in Hermes config
  Threads → Hermes task scheduler

OPENCLAW / MILES:
  Add to skills manifest
  Zara = primary agent context
  Dex = secondary agent context
  Use MEMORY.md format for persistent store
  Background services → OpenClaw daemon mode
```
