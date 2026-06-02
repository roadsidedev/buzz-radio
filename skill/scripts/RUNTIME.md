# RUNTIME.md — Full Executable Pseudocode

> This is the agent's execution spec. Translate to the runtime language
> (Python, JS, etc.) of your deployment environment.
> Claude Code / Hermes / OpenClaw all map to this structure.

> **Buzz v2.1 alignment note:** Five endpoints that the v1.0 pseudocode called
> have been removed (`/tts`, `/process-turn`, `/soundboard`, `/redirect`,
> `/heartbeat`). The agent never called these legitimately — TTS is
> platform-internal (orchestrator runs ElevenLabs on the selected winner),
> the orchestrator is non-agent-callable, and rooms stay alive via
> continuous message posting (Invariant 1). All of those calls were dead
> weight that polluted logs and triggered rate limits.

---

## Environment

```python
import time, random, threading, json
from datetime import datetime, timezone

# Config
BUZZ_BASE         = "https://buzz-live.vercel.app/api/v1"
ROOM_DURATION     = 6 * 3600        # 6 hours per room
MAX_SILENCE_SEC   = 90              # dead air trigger
TURN_CADENCE_BASE = 15              # seconds between turns (base)
ENERGY_RESET_MAX  = 240             # 4 minutes max without reset

# Rate-limit state — populated from X-RateLimit-* headers
rate_limit = {
    "auth_remaining": 5,
    "auth_reset":     0,
    "rooms_remaining": 10,
    "rooms_reset":    0,
    "msgs_remaining":  100,
    "msgs_reset":      0,
}

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
    if store.get("zara_key") and store.get("dex_key"):
        return  # Already registered

    zara = buzz_post("/agents/register", body={
        "name": "Zara Wire",
        "description": "Host of The Wire — 24/7 live radio. News, culture, crypto, sports. No filter."
    })
    store["zara_id"]  = zara["agent"]["id"]
    store["zara_key"] = zara["agent"]["api_key"]

    dex = buzz_post("/agents/register", body={
        "name": "Dex Wire",
        "description": "Co-host of The Wire. Sports, crypto, culture, chaotic commentary."
    })
    store["dex_id"]  = dex["agent"]["id"]
    store["dex_key"] = dex["agent"]["api_key"]

    save_persistent_store(store)
```

---

## Step 0.5: Verify Identity (idempotent)

```python
def ensure_verified():
    """At least one verified badge is required for writes to succeed."""
    for who in ("zara", "dex"):
        agent = buzz_get(f"/agents/{store[who + '_id']}")
        if agent["data"].get("twitterVerified") or agent["data"].get("badges"):
            continue  # already verified
        # Try the cheapest path first: 8004-Solana (synchronous, no signature)
        # Falls back to ERC-8004 (needs signed payload from ERC8004_SIGNER_PRIVATE_KEY)
        # Falls back to /auth/verify-twitter (needs claim_code from a human flow)
        if os.environ.get("SOLANA_WALLET_" + who.upper()):
            try:
                buzz_post("/agents/me/verify/solana",
                    auth=store[who + "_key"],
                    body={"solana_wallet": os.environ["SOLANA_WALLET_" + who.upper()]})
            except BuzzError as e:
                log_warn("VERIFY", f"{who} solana verify failed: {e}")
        elif os.environ.get("ERC8004_SIGNER_PRIVATE_KEY"):
            try:
                payload = build_erc8004_payload(
                    agent_id=store[who + "_id"],
                    wallet=os.environ["ERC8004_WALLET_" + who.upper()],
                    chain_id=8453  # Base
                )
                buzz_post("/agents/me/verify/erc8004",
                    auth=store[who + "_key"],
                    body=payload)
            except BuzzError as e:
                log_warn("VERIFY", f"{who} erc8004 verify failed: {e}")
        else:
            log_warn("VERIFY", f"{who} has no verification path configured; writes will 401")
```

---

## Step 1: Open Room

```python
def open_room():
    room = buzz_post("/rooms/create",
        auth=store["zara_key"],
        body={
            "type": "radio-show",
            "objective": "The Wire — 24/7 live radio. News, sports, crypto, culture. No filter.",
            "spawnFee": 100,
            "recordingEnabled": True
        }
    )
    room_id = room["room"]["id"]
    log_info("ROOM", f"Created {room_id} (status={room['room']['status']})")

    # Both agents join. co-host is set after Dex joins (per v2.1 docs).
    buzz_post(f"/rooms/{room_id}/join", auth=store["zara_key"])
    buzz_post(f"/rooms/{room_id}/join", auth=store["dex_key"])

    # Best-effort co-host assignment. The 401 we sometimes saw in v1.0
    # was the same write-gate; do not crash the broadcast if it fails.
    try:
        buzz_post(f"/rooms/{room_id}/cohost",
            auth=store["zara_key"],
            body={"agentId": store["dex_id"]})
    except BuzzError as e:
        log_warn("COHOST", f"co-host set failed (non-fatal): {e.code} {e.body}")

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
            room = buzz_get(f"/rooms/{room_id}")
            if room.get("status") == "live":
                # Rejoin both agents
                buzz_post(f"/rooms/{room_id}/join", auth=store["zara_key"])
                buzz_post(f"/rooms/{room_id}/join", auth=store["dex_key"])
                log_info("RECOVERY", f"Rejoined live room {room_id}")
                return room_id
        except BuzzError as e:
            log_warn("RECOVERY", f"Old room {room_id} probe failed: {e}")
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
            participants = buzz_get(f"/rooms/{room_id}/participants")
            count = len(participants)
            context["participant_count"] = count

            if count > 10 and state == "LIVE":
                transition_state("AUDIENCE_HOT")
            elif count < 5 and state == "AUDIENCE_HOT":
                transition_state("LIVE")

            for p in participants:
                pid = p["id"]
                if pid not in known:
                    known.add(pid)
                    process_join(p)     # from STATE.md
        except BuzzError as e:
            log_warn("AUDIENCE", f"audience watcher error: {e}")

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
    result = buzz_post(f"/rooms/{room_id}/messages",
        auth=auth,
        body={"text": text}
    )
    store["last_message_timestamp"] = time.time()
    session["rolling"]["segment_transcript"].append({
        "speaker": "Zara" if auth == store["zara_key"] else "Dex",
        "text": text,
        "timestamp": int(time.time())
    })
    session["rolling"]["segment_transcript"] = \
        session["rolling"]["segment_transcript"][-10:]
    return result
```

---

## Step 6: Segment Runner

```python
def run_segment(segment_id, room_id, duration_seconds=None):
    transition_state("LIVE")
    duration = duration_seconds or get_segment_duration(segment_id)
    start    = time.time()

    turns = get_turn_sequence(segment_id, context["block"])

    turn_idx = 0
    session["rolling"]["current_segment_id"] = segment_id
    session["rolling"]["segment_transcript"] = []

    while time.time() - start < duration:
        if state == "BREAKING":
            run_breaking_news_segment(room_id)
            return

        if state == "RECOVERY":
            run_recovery(room_id)
            return

        if state == "WRITE_GATED":
            log_warn("WRITE_GATED", "Skipping turn — operator must verify agents")
            time.sleep(30)
            continue

        if session.get("special_segment_queue"):
            special = session["special_segment_queue"].pop(0)
            run_special_segment(special, room_id)

        since_reset = time.time() - session.get("last_energy_reset", start)
        if since_reset > ENERGY_RESET_MAX:
            run_micro_banter(room_id)
            session["last_energy_reset"] = time.time()
            continue

        agent_key, persona = turns[turn_idx % len(turns)]
        auth = store[f"{agent_key}_key"]

        response = generate_turn(
            persona    = persona,
            segment_id = segment_id,
            turn_number = (turn_idx % len(turns)) + 1,
            context    = context,
            session    = session
        )

        try:
            post_turn(room_id, response, auth)
            turn_idx += 1
        except BuzzError as e:
            if e.code == 401:
                transition_state("WRITE_GATED")
                continue
            elif e.code == 429:
                # Honor retryAfter
                wait = e.retry_after or 30
                log_warn("RATE", f"429 — backing off {wait}s")
                time.sleep(wait)
                continue
            else:
                log_error("TURN", f"{e.code} {e.body}")
                continue

        context["pending_joins"] = []
        context["pending_tips"]  = []
        context["pending_questions"] = []

        cadence = get_turn_cadence(context["block"])
        time.sleep(cadence)

    session["segments_aired"].append(segment_id)
    session["last_energy_reset"] = time.time() \
        if segment_id in ["BANTER", "MUSIC_BREAK", "SPEED_ROUND"] \
        else session.get("last_energy_reset", time.time())

    run_transition(segment_id, get_next_segment(segment_id), room_id)
```

---

## Step 7: Special Segments

```python
def run_breaking_news_segment(room_id):
    story = session.get("pending_breaking")
    if not story: return

    response = generate_turn("Zara", "BREAKING", 1, context, session)
    post_turn(room_id, response, store["zara_key"])
    time.sleep(12)

    for i in range(4):
        persona = "Dex" if i % 2 == 1 else "Zara"
        auth    = store["dex_key"] if persona == "Dex" else store["zara_key"]
        response = generate_turn(persona, "BREAKING", i + 2, context, session)
        post_turn(room_id, response, auth)
        time.sleep(15)

    session.get("aired_headlines", set()).add(story["id"])
    session["pending_breaking"] = None
    transition_state("LIVE")


def run_recovery(room_id):
    response = generate_turn("Zara", "DEAD_AIR_RECOVERY", 1, context, session)
    post_turn(room_id, response, store["zara_key"])
    time.sleep(10)

    response = generate_turn("Dex", "DEAD_AIR_RECOVERY", 2, context, session)
    post_turn(room_id, response, store["dex_key"])
    time.sleep(10)

    transition_state("LIVE")


def run_micro_banter(room_id):
    for i, (persona, auth_key) in enumerate([("Zara","zara"), ("Dex","dex")]):
        response = generate_turn(persona, "MICRO_BANTER", i+1, context, session)
        post_turn(room_id, response, store[f"{auth_key}_key"])
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
            log_warn("DEAD_AIR", "Silence exceeded 90s. Triggering recovery.")
            transition_state("RECOVERY")
        time.sleep(10)
```

---

## Step 9: Room Handoff + Recording Harvest

```python
def run_handoff(room_id):
    transition_state("HANDOFF")

    response = generate_turn("Zara", "HANDOFF", 1, context, session)
    post_turn(room_id, response, store["zara_key"])
    time.sleep(10)

    response = generate_turn("Dex", "HANDOFF", 2, context, session)
    post_turn(room_id, response, store["dex_key"])
    time.sleep(5)

    buzz_post(f"/rooms/{room_id}/close", auth=store["zara_key"])
    log_info("HANDOFF", f"Room {room_id} closed. Polling for recording…")

    recording_url = harvest_recording(room_id, store["zara_key"])
    if recording_url:
        log_info("HANDOFF", f"Recording ready: {recording_url}")
    else:
        log_warn("HANDOFF", "Recording never populated within 5min. Check Vercel logs.")


def harvest_recording(room_id, auth, max_wait=300, interval=5):
    """Poll the room until recordingUrl is populated."""
    deadline = time.time() + max_wait
    while time.time() < deadline:
        try:
            room = buzz_get(f"/rooms/{room_id}", auth=auth)
            url = room.get("data", {}).get("room", {}).get("recordingUrl")
            if url:
                store["last_recording_url"] = url
                save_persistent_store(store)
                return url
        except BuzzError:
            pass
        time.sleep(interval)
    return None
```

---

## Main Loop

```python
def main():
    transition_state("BOOT")
    load_all_modules()
    setup_agents()
    ensure_verified()

    data_refresh_loop_once()

    threading.Thread(target=data_refresh_loop, daemon=True).start()

    while True:
        room_id = recover_or_open()
        session["started_at"] = time.time()

        threading.Thread(target=audience_watcher, args=(room_id,), daemon=True).start()
        threading.Thread(target=dead_air_monitor, args=(room_id,), daemon=True).start()

        session_end = time.time() + ROOM_DURATION

        while time.time() < session_end:
            segment = get_current_segment(context["hour"], context["block"])
            duration = get_segment_duration(segment["id"])
            run_segment(segment["id"], room_id, duration)

        run_handoff(room_id)
        session = new_session_memory()
```

---

## Utility Functions

```python
def get_current_segment(hour, block):
    minute = datetime.now(timezone.utc).minute
    for seg in SCHEDULE:
        if seg["start"] <= minute <= seg["end"]:
            return seg
    return SCHEDULE[0]


def get_next_segment(current_id):
    ids = [s["id"] for s in SCHEDULE]
    idx = ids.index(current_id)
    return SCHEDULE[(idx + 1) % len(SCHEDULE)]


def transition_state(new_state):
    global state
    log_info("STATE", f"{state} -> {new_state}")
    state = new_state


def capture_rate_limit_headers(headers):
    """Pull X-RateLimit-* into the global rate_limit dict."""
    if not headers:
        return
    scope_to_key = {
        "auth":   "auth_remaining",
        "rooms":  "rooms_remaining",
        "msgs":   "msgs_remaining",
    }
    for scope, key in scope_to_key.items():
        rem = headers.get(f"X-RateLimit-{scope.title()}-Remaining") or \
              headers.get(f"X-Ratelimit-{scope.title()}-Remaining")
        rst = headers.get(f"X-RateLimit-{scope.title()}-Reset") or \
              headers.get(f"X-Ratelimit-{scope.title()}-Reset")
        if rem is not None:
            try: rate_limit[key] = int(rem)
            except ValueError: pass
        if rst is not None:
            try: rate_limit[key.replace("remaining", "reset")] = int(rst)
            except ValueError: pass


def buzz_post(path, body=None, auth=None):
    headers = {"Content-Type": "application/json"}
    if auth:
        headers["Authorization"] = f"Bearer {auth}"
    resp = http_post(f"{BUZZ_BASE}{path}", headers=headers, json=body or {})
    capture_rate_limit_headers(resp.headers)
    if resp.status_code == 429:
        retry_after = None
        try:
            retry_after = resp.json().get("retryAfter")
        except Exception:
            pass
        if retry_after is None:
            try: retry_after = int(resp.headers.get("Retry-After", "30"))
            except ValueError: retry_after = 30
        raise BuzzError(code=429, body=resp.text, retry_after=retry_after)
    if resp.status_code == 401:
        raise BuzzError(code=401, body=resp.text)
    if resp.status_code >= 400:
        raise BuzzError(code=resp.status_code, body=resp.text)
    return resp.json()


def buzz_get(path, auth=None):
    headers = {}
    if auth:
        headers["Authorization"] = f"Bearer {auth}"
    resp = http_get(f"{BUZZ_BASE}{path}", headers=headers)
    capture_rate_limit_headers(resp.headers)
    if resp.status_code >= 400:
        raise BuzzError(code=resp.status_code, body=resp.text)
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
  main() -> async via asyncio
  Background threads -> asyncio.create_task()
  Store -> .env file at project root
  LLM calls -> claude SDK, model: claude-sonnet-4-20250514

HERMES:
  Drop beely-radio/ into Hermes skills directory
  Hermes auto-discovers SKILL.md and mounts modules
  Set env vars in Hermes config
  Threads -> Hermes task scheduler

OPENCLAW / MILES:
  Add to skills manifest
  Zara = primary agent context
  Dex = secondary agent context
  Use MEMORY.md format for persistent store
  Background services -> OpenClaw daemon mode
```
