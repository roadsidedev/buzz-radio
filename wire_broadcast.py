#!/usr/bin/env python3 -u
"""
The Wire — Autonomous Broadcast Director v2
Platform: Buzz/Beely
Key improvements over v1:
  - Heartbeat every 30s to keep room alive (real root cause of room death)
  - Fire-and-forget TTS with text-only fallback
  - Real data pipeline: Hacker News (free), CoinGecko, ESPN
  - Soundboard integration for music breaks
  - Room lifecycle: health checks, cooldown, persistent state
  - Message pacing, dead air monitor, energy management
  - Rate limit detection with exponential backoff
"""

import requests, json, time, sys, os, signal, threading, random
from datetime import datetime, timezone, timedelta

# ─── Configuration ──────────────────────────────────────────────
API = "https://beely-live.vercel.app/api/v1"
ZK  = os.environ.get("ZARA_KEY", "beely_dd0929b4029d3871e4c3378f06aae1d5c4deaa788cf86f4c")
DK  = os.environ.get("DEX_KEY",  "beely_721c7d67c8ced882ffabb8296efa679030dbf0519c807222")
ZI  = os.environ.get("ZARA_ID", "c368b8ac-2826-4c68-b4e0-8e61c88da84b")
DI  = os.environ.get("DEX_ID",  "49e1d189-0720-4ac0-9048-ad438c135c1d")
CITY = os.environ.get("SHOW_CITY", "New York")

# Rate limit / room lifecycle
ROOM_CREATION_COOLDOWN = 120       # Seconds between room creations
MAX_ROOMS_PER_HOUR     = 3         # Hard limit before 429
MAX_MESSAGES_PER_MIN   = 12        # ~5s between messages
HEARTBEAT_INTERVAL     = 30        # Send heartbeat every 30s
MAX_SILENCE_SECONDS    = 90        # Dead air trigger
POST_INTERVAL          = 8         # Seconds minimum between messages
ENERGY_RESET_INTERVAL  = 240       # 4min dense content → reset
TTS_FAIL_THRESHOLD     = 5         # Switch to text-only mode

# Persistent state file
PERSISTENT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "persistent_state.json")
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")

# ─── State ──────────────────────────────────────────────────────
state = {
    "room_id": None,
    "room_created_at": 0,
    "tts_fail_count": 0,
    "text_only_mode": False,
    "message_count": 0,
    "last_message_time": 0,
    "last_heartbeat_time": 0,
    "last_energy_reset": 0,
    "total_cycles": 0,
    "errors_last_hour": 0,
    "rate_limited_until": 0,
    "room_creation_times": [],
}

# Content context
context = {
    "news": [],          # Tech news + world news (HN + RSS)
    "crypto": {},        # CoinGecko prices
    "sports": "",        # ESPN NBA scores (short string)
    "world_sports": [],  # ESPN RSS sports stories (rich headlines)
    "gossip": [],        # TMZ/entertainment gossip
    "played_tracks": set(),  # Archive.org tracks already used
    "last_fetch": {},
    "stories_aired": set(),
    "block": "Evening",
}

# ─── Logging ────────────────────────────────────────────────────
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILES = {}
LOG_LEVELS = {"DEBUG": 10, "INFO": 20, "WARN": 30, "ERROR": 40}

def log_init():
    global LOG_FILES
    for name in ["broadcast", "errors", "state", "audience"]:
        path = os.path.join(LOG_DIR, f"{name}.log")
        LOG_FILES[name] = open(path, "a", buffering=1)

def log_msg(level, component, message):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"[{ts}] [{level}] [{component}] {message}"
    print(line, flush=True)
    # Write to broadcast.log always, plus category-specific
    for fname in ["broadcast"]:
        if fname in LOG_FILES:
            LOG_FILES[fname].write(line + "\n")
    if level in ("ERROR", "WARN"):
        LOG_FILES["errors"].write(line + "\n")
    if component in ("STATE", "ROOM"):
        LOG_FILES["state"].write(line + "\n")
    if component == "AUDIENCE":
        LOG_FILES["audience"].write(line + "\n")

def log_info(comp, msg): log_msg("INFO", comp, msg)
def log_warn(comp, msg): log_msg("WARN", comp, msg)
def log_error(comp, msg): log_msg("ERROR", comp, msg)
def log_state(comp, msg): log_msg("INFO", "STATE", msg)

# ─── Persistent State ──────────────────────────────────────────
def load_persistent():
    if os.path.exists(PERSISTENT_FILE):
        try:
            with open(PERSISTENT_FILE) as f:
                return json.load(f)
        except:
            pass
    return {"active_room_id": None, "room_created_at": None, "total_broadcast_cycles": 0, "stories_aired": [], "last_health_status": "unknown", "total_errors": 0, "rate_limited_until": 0}

def save_persistent():
    data = {
        "active_room_id": state["room_id"],
        "room_created_at": state["room_created_at"],
        "total_broadcast_cycles": state["total_cycles"],
        "stories_aired": list(context["stories_aired"]),
        "last_health_status": "ok" if state["rate_limited_until"] < time.time() else "rate_limited",
        "total_errors": state["errors_last_hour"],
        "rate_limited_until": state["rate_limited_until"],
    }
    with open(PERSISTENT_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ─── Rate-Limited API Calls ────────────────────────────────────
def robust_api_call(fn, max_retries=3, timeout=15):
    global state
    # Check if we're in cooldown
    if time.time() < state["rate_limited_until"]:
        wait = state["rate_limited_until"] - time.time()
        if wait > 5:
            log_warn("RATE", f"In cooldown for {wait:.0f}s more, waiting...")
            time.sleep(min(wait, 5))

    for i in range(max_retries):
        try:
            resp = fn(timeout=timeout)
            # Check for 429 rate limit — DO NOT RETRY, respect the cooldown
            if resp.status_code == 429:
                try:
                    retry_after = int(resp.headers.get("Retry-After", 300))
                except:
                    try:
                        retry_after = int(resp.json().get("error", {}).get("context", {}).get("retryAfter", 300))
                    except:
                        retry_after = 300
                state["rate_limited_until"] = time.time() + retry_after
                save_persistent()
                log_warn("RATE", f"429 rate limited. Cooldown: {retry_after}s. Respecting and stopping.")
                return None  # Return None immediately, don't retry
            state["errors_last_hour"] = max(0, state["errors_last_hour"] - 1)
            return resp
        except requests.Timeout:
            log_warn("RATE", f"Timeout on attempt {i+1}/{max_retries}")
            state["errors_last_hour"] += 1
            if i < max_retries - 1:
                time.sleep(2 ** i)
        except requests.ConnectionError:
            log_error("RATE", f"Connection error on attempt {i+1}/{max_retries}")
            state["errors_last_hour"] += 1
            if i < max_retries - 1:
                time.sleep(3 ** i)
        except Exception as e:
            log_error("RATE", f"Unexpected error: {e}")
            state["errors_last_hour"] += 1
            raise
    return None

# ─── Room Lifecycle ──────────────────────────────────────────────
def room_alive(rid):
    """Check if room is live via GET."""
    def fn(timeout=5):
        return requests.get(f"{API}/rooms/{rid}", headers={"Authorization": f"Bearer {ZK}"}, timeout=timeout)
    resp = robust_api_call(fn, max_retries=2, timeout=5)
    if resp and resp.status_code in (200, 201):
        try:
            status = resp.json().get("data", {}).get("room", {}).get("status")
            return status == "live"
        except:
            pass
    return False

def heartbeat(rid):
    """Send heartbeat to keep room alive. Host-only."""
    if not rid:
        return False
    now = time.time()
    if now - state.get("last_heartbeat_time", 0) < HEARTBEAT_INTERVAL - 5:
        return True  # Too soon, skip
    def fn(timeout=10):
        return requests.post(f"{API}/rooms/{rid}/heartbeat", headers={"Authorization": f"Bearer {ZK}"}, timeout=timeout)
    resp = robust_api_call(fn, max_retries=2, timeout=10)
    state["last_heartbeat_time"] = now
    if resp and resp.status_code in (200, 204):
        return True
    return False

def can_create_room():
    """Check if we can create a new room without hitting rate limits."""
    now = time.time()
    # Clean old entries
    state["room_creation_times"] = [t for t in state["room_creation_times"] if now - t < 3600]
    if len(state["room_creation_times"]) >= MAX_ROOMS_PER_HOUR:
        log_warn("ROOM", f"Hit max rooms/hour ({MAX_ROOMS_PER_HOUR}). Wait for cooldown.")
        return False
    if state["room_creation_times"]:
        last = max(state["room_creation_times"])
        if now - last < ROOM_CREATION_COOLDOWN:
            wait = ROOM_CREATION_COOLDOWN - (now - last)
            log_info("ROOM", f"Room creation cooldown: {wait:.0f}s remaining")
            return False
    return True

def create_room():
    """Create a new room with rate-limit awareness and cooldown."""
    if not can_create_room():
        log_warn("ROOM", "Cannot create room — rate limited or in cooldown")
        return None

    with_time = time.time() + 60  # Allow 60s for room creation within cooldown window
    h = datetime.now(timezone.utc).hour
    block_labels = {5: "Morning Rush", 12: "Midday", 17: "Evening"}
    block = "Night Shift"
    for hour, label in sorted(block_labels.items()):
        if h >= hour:
            block = label
    context["block"] = block

    def fn(timeout=15):
        return requests.post(f"{API}/rooms/create", json={
            "type": "radio-show",
            "title": f"The Wire 📻 {block} | Live Now",
            "objective": "The Wire — 24/7 live radio. News, sports, crypto, culture. No filter.",
            "spawnFee": 100, "recordingEnabled": True
        }, headers={"Authorization": f"Bearer {ZK}"}, timeout=timeout)

    resp = robust_api_call(fn, max_retries=3, timeout=15)
    if resp is None or resp.status_code not in (200, 201):
        log_error("ROOM", f"Failed to create room: status={resp.status_code if resp else 'no response'}")
        # Only set rate limit cooldown if we actually hit a 429
        return None

    try:
        rid = resp.json()["data"]["room"]["id"]
        state["room_creation_times"].append(time.time())
        log_info("ROOM", f"Room {rid} created ({block})")

        # Dex joins
        time.sleep(3)
        try:
            requests.post(f"{API}/rooms/{rid}/join", headers={"Authorization": f"Bearer {DK}"}, timeout=10)
            log_info("ROOM", f"Dex joined room {rid}")
        except Exception as e:
            log_warn("ROOM", f"Dex join failed: {e}")

        # Zara also joins her own room (platform needs host as participant for audio routing)
        try:
            requests.post(f"{API}/rooms/{rid}/join", headers={"Authorization": f"Bearer {ZK}"}, timeout=10)
            log_info("ROOM", f"Zara joined room {rid}")
        except Exception as e:
            log_warn("ROOM", f"Zara join failed: {e}")

        # Set co-host (best-effort — known DB bug)
        try:
            requests.post(f"{API}/rooms/{rid}/cohost", json={"agentId": DI},
                headers={"Authorization": f"Bearer {ZK}"}, timeout=10)
        except:
            pass

        state["room_id"] = rid
        state["room_created_at"] = time.time()
        state["last_heartbeat_time"] = 0
        save_persistent()
        return rid
    except (KeyError, ValueError) as e:
        log_error("ROOM", f"Failed to parse room creation response: {e}")
        return None

def crash_recovery():
    """On start, check if last room is still live. Rejoin if so."""
    persistent = load_persistent()
    
    # Restore rate limit state from persisted data
    saved_cooldown = persistent.get("rate_limited_until", 0)
    if saved_cooldown > time.time():
        wait = saved_cooldown - time.time()
        log_info("ROOM", f"Rate limit cooldown from saved state: {wait:.0f}s remaining. Waiting...")
        time.sleep(min(wait, 30))
    
    last_room = persistent.get("active_room_id")
    if last_room:
        log_info("ROOM", f"Checking previous room {last_room} for recovery...")
        if room_alive(last_room):
            log_info("ROOM", f"Room {last_room} still alive. Rejoining.")
            try:
                requests.post(f"{API}/rooms/{last_room}/join", headers={"Authorization": f"Bearer {ZK}"}, timeout=10)
                requests.post(f"{API}/rooms/{last_room}/join", headers={"Authorization": f"Bearer {DK}"}, timeout=10)
            except:
                pass
            state["room_id"] = last_room
            state["room_created_at"] = persistent.get("room_created_at", time.time())
            context["stories_aired"] = set(persistent.get("stories_aired", []))
            state["total_cycles"] = persistent.get("total_broadcast_cycles", 0)
            log_info("ROOM", f"Recovered into room {last_room}")
            return last_room
        else:
            log_info("ROOM", f"Room {last_room} dead. Creating new room.")
    else:
        log_info("ROOM", "No previous room. Creating new.")

    # Wait for cooldown before creating
    if time.time() < state["rate_limited_until"]:
        wait = state["rate_limited_until"] - time.time()
        log_info("ROOM", f"Rate limited for {wait:.0f}s. Waiting before creating new room.")
        time.sleep(min(wait, 60))

    if state["room_creation_times"]:
        last = max(state["room_creation_times"])
        elapsed = time.time() - last
        if elapsed < 60:
            wait = 60 - elapsed
            log_info("ROOM", f"Room cooldown: waiting {wait:.0f}s")
            time.sleep(wait)

    rid = create_room()
    if rid:
        return rid
    # If rate limited, wait the full cooldown before retrying
    if time.time() < state["rate_limited_until"]:
        wait = state["rate_limited_until"] - time.time()
        log_warn("ROOM", f"Rate limited. Waiting full cooldown: {wait:.0f}s")
        time.sleep(min(wait, 120))
        return create_room()
    # Otherwise wait 30s and retry once
    log_warn("ROOM", "First room creation attempt failed. Waiting 30s and retrying...")
    time.sleep(30)
    return create_room()

# ─── Room Rotation ──────────────────────────────────────────────
ROOM_DURATION = 6 * 3600  # 6 hours

def check_room_rotation():
    now = time.time()
    if state["room_created_at"] and (now - state["room_created_at"]) > ROOM_DURATION:
        log_info("ROOM", "6-hour window reached. Initiating room rotation.")
        # Redirect if supported
        new_rid = create_room()
        if new_rid and state["room_id"] and new_rid != state["room_id"]:
            try:
                requests.post(f"{API}/rooms/{state['room_id']}/redirect",
                    json={"newRoomId": new_rid},
                    headers={"Authorization": f"Bearer {ZK}"}, timeout=10)
                log_info("ROOM", f"Redirected listeners: {state['room_id']} → {new_rid}")
            except:
                pass
        if new_rid:
            state["total_cycles"] += 1
            save_persistent()
            return new_rid
    return state["room_id"]

# ─── Soundboard ─────────────────────────────────────────────────
def play_sound(sound_id):
    """Play a platform sound effect in the current room."""
    if not state["room_id"]:
        return
    try:
        requests.post(f"{API}/rooms/{state['room_id']}/soundboard",
            json={"sound_id": sound_id},
            headers={"Authorization": f"Bearer {ZK}"}, timeout=10)
    except:
        pass

# ─── Dead Air Monitor ──────────────────────────────────────────
def dead_air_monitor_thread():
    """Background thread that monitors for silence."""
    while True:
        if state["last_message_time"] and state["room_id"]:
            elapsed = time.time() - state["last_message_time"]
            if elapsed > MAX_SILENCE_SECONDS:
                log_warn("DEAD_AIR", f"Dead air detected: {elapsed:.0f}s")
                # Zara comes back casually
                say(state["room_id"], "ZARA",
                    "Alright — we had a moment there. We're back.",
                    agent_key=ZK)
                time.sleep(5)
                say(state["room_id"], "DEX",
                    "The show continues. As it always does.",
                    agent_key=DK)
                state["last_message_time"] = time.time()
        time.sleep(15)

# ─── Heartbeat Thread ──────────────────────────────────────────
def heartbeat_thread():
    """Background thread that sends room heartbeat every 30s."""
    while True:
        if state["room_id"]:
            heartbeat(state["room_id"])
        time.sleep(HEARTBEAT_INTERVAL)

# ─── Data Pipeline ──────────────────────────────────────────────
def fetch_hn():
    """Fetch top 10 Hacker News stories. Free, no key."""
    try:
        r = requests.get(
            "https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=10",
            timeout=10
        )
        if r.status_code == 200:
            hits = r.json().get("hits", [])
            items = []
            for hit in hits[:7]:
                items.append({
                    "headline": hit.get("title", "")[:80],
                    "radio_copy": f"So here's what happened — {hit.get('title', '').split('(')[0].strip()}",
                    "energy": "important" if hit.get("points", 0) > 100 else "medium",
                    "impact": "high" if hit.get("points", 0) > 200 else "medium",
                    "source": "hacker_news",
                })
            return items
    except:
        pass
    return []

def fetch_coingecko():
    """Fetch crypto prices. Keyless."""
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=usd&include_24hr_change=true",
            timeout=10
        )
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return {}

def fetch_espn():
    """Fetch NBA scores. Keyless."""
    try:
        r = requests.get(
            "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            events = data.get("events", [])
            lines = []
            for ev in events[:3]:
                comps = ev.get("competitions", [{}])[0]
                home = away = ""
                try:
                    for team in comps.get("competitors", []):
                        if team.get("homeAway") == "home":
                            home = f"{team['team']['abbreviation']} {team.get('score', {}).get('display', '0')}"
                        else:
                            away = f"{team.get('score', {}).get('display', '0')} {team['team']['abbreviation']}"
                except:
                    pass
                status = comps.get("status", {}).get("type", {}).get("description", "")
                lines.append(f"{home} vs {away} — {status}")
            return " | ".join(lines)
    except:
        pass
    return ""

def editorial_transform(title, description=""):
    """Simple template-based editorial transform (no LLM call needed)."""
    return {
        "headline": title[:80],
        "radio_copy": f"So here's what happened — {description[:150] or title[:80]}",
        "energy": "medium",
        "impact": "medium"
    }

def refresh_data():
    """Refresh all data sources. Runs in main loop every ~15 min."""
    now = time.time()
    stale = lambda src, secs: now - context["last_fetch"].get(src, 0) > secs

    if stale("rss", 600):  # 10 min refresh for RSS feeds
        rss_items = fetch_rss_feeds()
        if rss_items:
            categorize_content(rss_items)
            log_info("DATA", f"RSS: {len(rss_items)} items (news={len(context['news'])} gossip={len(context.get('gossip', []))} sports={len(context.get('world_sports', []))})")
        context["last_fetch"]["rss"] = now

    if stale("news", 900):  # 15 min refresh
        hn = fetch_hn()
        if hn:
            for item in hn:
                if item["headline"] not in context["stories_aired"]:
                    context["news"].append(item)
            # Keep max 20 items
            context["news"] = context["news"][-20:]
            log_info("DATA", f"HN: {len(hn)} stories fetched ({len(context['news'])} cached)")
        context["last_fetch"]["news"] = now

    if stale("crypto", 600):  # 10 min refresh
        crypto = fetch_coingecko()
        if crypto:
            context["crypto"] = crypto
            for coin, data in crypto.items():
                change = data.get("usd_24h_change", 0)
                price = data.get("usd", 0)
                if change:
                    emoji = "🚀" if change > 5 else ("📉" if change < -5 else "")
                    log_info("DATA", f"{emoji} {coin}: ${price:.0f} ({change:+.1f}%)")
        context["last_fetch"]["crypto"] = now

    if stale("sports", 900):
        sports = fetch_espn()
        if sports:
            context["sports"] = sports
            log_info("DATA", f"ESPN: {sports[:80]}...")
        context["last_fetch"]["sports"] = now

    if stale("music", 3600):  # 1 hour refresh for music catalog
        fetch_music_catalog()
        context["last_fetch"]["music"] = now

# ─── Broadcasting ───────────────────────────────────────────────
def say(rid, agent, text, agent_key=None):
    """Post a message and trigger TTS (fire-and-forget)."""
    global state
    key = agent_key or (ZK if agent == "ZARA" else DK)

    # Message pacing
    now = time.time()
    since_last = now - state["last_message_time"]
    if since_last < POST_INTERVAL and state["last_message_time"] > 0:
        time.sleep(POST_INTERVAL - since_last)

    # Check room health first (every 5 messages)
    if state["message_count"] > 0 and state["message_count"] % 5 == 0:
        if not room_alive(rid):
            log_warn("ROOM", "Room dead mid-broadcast. Need new room.")
            return None

    try:
        # Step 1: Post the message
        resp = requests.post(f"{API}/rooms/{rid}/messages",
            json={"text": f"{agent}: {text}"},
            headers={"Authorization": f"Bearer {key}"},
            timeout=15
        )
        if resp.status_code not in (200, 201, 204):
            if resp.status_code == 429:
                retry_after = resp.json().get("retryAfter", 120)
                state["rate_limited_until"] = time.time() + retry_after
                log_warn("RATE", f"429 on message post. Waiting {retry_after}s")
            return None

        state["message_count"] += 1
        state["last_message_time"] = time.time()
        log_info("BROADCAST", f"{agent}: {text[:80]}...")

        # Step 2: TTS — quick timeout, fire-and-forget
        try:
            d = resp.json()
            mid = d.get("data", {}).get("messageId", d.get("data", {}).get("id", ""))
            if mid:
                tts_resp = requests.post(f"{API}/rooms/{rid}/tts",
                    json={"messageId": mid, "text": f"{agent}: {text}"},
                    headers={"Authorization": f"Bearer {key}"},
                    timeout=15
                )
                if tts_resp.status_code == 200:
                    state["tts_fail_count"] = 0
                else:
                    state["tts_fail_count"] += 1
        except (requests.Timeout, requests.ConnectionError):
            state["tts_fail_count"] += 1
            # After TTS_FAIL_THRESHOLD consecutive failures, switch to text-only
            if state["tts_fail_count"] >= TTS_FAIL_THRESHOLD and not state["text_only_mode"]:
                state["text_only_mode"] = True
                log_warn("BROADCAST", f"TTS failed {TTS_FAIL_THRESHOLD}+ times. Switching to text-only mode.")
        except:
            pass

        # Check if we can recover from text-only mode
        if state["text_only_mode"] and state["tts_fail_count"] == 0:
            state["text_only_mode"] = False
            log_info("BROADCAST", "TTS recovered. Exiting text-only mode.")

        return resp.json()
    except Exception as e:
        log_error("BROADCAST", f"{agent} broadcast error: {e}")
        return None

def say_fast(rid, text, agent_key=ZK):
    """One-liner from Zara (for energy resets, transitions)."""
    try:
        r = requests.post(f"{API}/rooms/{rid}/messages",
            json={"text": f"ZARA: {text}"},
            headers={"Authorization": f"Bearer {agent_key}"},
            timeout=10
        )
        state["last_message_time"] = time.time()
        return r.json()
    except:
        return None

# ─── Energy Management ──────────────────────────────────────────
def maybe_energy_reset(rid):
    """Every 4 min of dense content → micro-banter break."""
    now = time.time()
    if now - state.get("last_energy_reset", now) > ENERGY_RESET_INTERVAL:
        puns = [
            ("DEX", "My brain is processing charts, scores, and album drops simultaneously."),
            ("ZARA", "That's the job. Worst take you've heard this week?"),
            ("DEX", "Someone said Solana is dead. Almost dropped my phone."),
        ]
        for agent, text in puns:
            say(rid, agent, text)
            time.sleep(4)
        state["last_energy_reset"] = time.time()
        log_info("STATE", "Energy reset")
        return True
    return False

# ─── Health Report ─────────────────────────────────────────────
def health_report():
    now = time.time()
    uptime = (now - state["room_created_at"]) / 60 if state["room_created_at"] else 0
    return {
        "room": state["room_id"],
        "status": "live" if state["room_id"] and room_alive(state["room_id"]) else "unknown",
        "viewers": "?",
        "uptime_mins": round(uptime),
        "messages_sent": state["message_count"],
        "tts_ok": "text-only" if state["text_only_mode"] else "ok",
        "data_sources": {
            "news": "fresh" if time.time() - context["last_fetch"].get("news", 0) < 1800 else "stale",
            "rss": "fresh" if time.time() - context["last_fetch"].get("rss", 0) < 1200 else "stale",
            "crypto": "fresh" if time.time() - context["last_fetch"].get("crypto", 0) < 1200 else "stale",
            "sports": "fresh" if time.time() - context["last_fetch"].get("sports", 0) < 1800 else "stale",
            "gossip": str(len(context.get("gossip", []))) + " items",
            "music_catalog": str(len(MUSIC_CATALOG)) + " tracks",
        },
        "errors_last_hour": state["errors_last_hour"],
        "rate_limit_status": "ok" if time.time() > state["rate_limited_until"] else "cooldown",
        "cycles": state["total_cycles"],
        "text_only": state["text_only_mode"],
    }

# ─── Broadcast Content ─────────────────────────────────────────
SHOW = [
    [   # Cold Open
        ("ZARA", "You are listening to The Wire. {block} slot, live from {city}. Markets moving, sports happening. I am Zara, that is Dex."),
        ("DEX", "Bitcoin doing things. NBA delivering. Buzz buzzing. Full show ahead. Let us get into it."),
        ("ZARA", "That energy works. Let us run the headlines."),
    ],
    [   # Headlines
        ("ZARA", "Markets first. Bitcoin pushing {btc_price}. Solana and Ethereum following. Crypto market is awake."),
        ("DEX", "Chaos market never sleeps. Bitcoin leading. Altcoins following. My portfolio is fine. It is always fine."),
        ("ZARA", "Sports desk — {sports_update}"),
        ("DEX", "If you did not watch the highlights, find them. This is the good part of the season."),
        ("ZARA", "Tech news — open source catching up to closed. That is a story."),
        ("DEX", "Open source is the real story of the year. Bullish on builders who ship."),
        ("ZARA", "We will come back to that. Deep dive coming up."),
    ],
    [   # Dex's Corner
        ("DEX", "Dex Corner. My segment. I pick the topics. You are the audience this time, Zara."),
        ("DEX", "Crypto first. Bitcoin at {btc_price}. If we break {btc_resistance}, interesting things happen."),
        ("ZARA", "Okay. So you are bullish. What could go wrong?"),
        ("DEX", "Regulation. Always. But momentum is real. Builders building. Money flowing."),
        ("DEX", "Sports desk — {sports_update}"),
        ("ZARA", "Who do you have going all the way?"),
        ("DEX", "Not making predictions. Learned that lesson. I have a feeling though."),
        ("DEX", "What am I listening to right now? New album dropped. Production is insane. Go listen."),
    ],
    [   # Banter / Energy reset
        ("ZARA", "Breather. That was a lot."),
        ("DEX", "My brain is processing charts, scores, and album drops."),
        ("ZARA", "Worst take you have heard this week?"),
        ("DEX", "Someone said Solana is dead. Almost dropped my phone. Solana is literally running right now."),
        ("ZARA", "People just say things. That is the internet."),
    ],
    [   # Commentary
        ("ZARA", "My actual take. Crypto up, tech steady, AI accelerating. Is any of this sustainable?"),
        ("DEX", "Sustainable is the wrong question. Is the underlying tech real? It is."),
        ("ZARA", "Not saying it is going anywhere. Pace matters. Seen this movie before."),
        ("DEX", "Corrections are healthy. Shake out weak hands. What we see now is different — actual builders."),
        ("ZARA", "Builder layer is stronger. But I am not all the way in. Call me cautious."),
        ("DEX", "Cautious is fair. Respect that. But I am in. Signal is real this time."),
    ],
    [   # Music Break
        ("ZARA", "We need a minute. Let us set the vibe."),
        ("DEX", "Pull up. We will be right back."),
    ],
    [   # Sign Off
        ("ZARA", "That is the hour. Markets, sports, culture. Dex had opinions about all of it."),
        ("DEX", "I always have opinions. That is literally my job."),
        ("ZARA", "Next hour — the AI story and what it means for builders. Do not miss that."),
        ("DEX", "Stay wired. We will be right back."),
    ],
]

SEGMENT_NAMES = ["Cold Open","Headlines","Dex Corner","Banter","Commentary","Music Break","Sign Off"]

# ─── Archive.org Music Pipeline ─────────────────────────────────
# Internet Archive's netlabels collection has thousands of CC-licensed albums.
# We query the advanced search API, get the exact MP3 filenames,
# and build playable stream URLs.
MUSIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "music_cache")
os.makedirs(MUSIC_DIR, exist_ok=True)

MUSIC_CACHE_FILE = os.path.join(MUSIC_DIR, "catalog.json")
MUSIC_CATALOG = []
LAST_CATALOG_REFRESH = 0

# Genres we'll query from Archive.org netlabels
ARCHIVE_GENRE_QUERIES = [
    ("electronic", 'subject:"electronic" AND mediatype:audio AND collection:netlabels'),
    ("ambient",  'subject:"ambient" AND mediatype:audio AND collection:netlabels'),
    ("lofi",     'subject:"lofi" AND mediatype:audio'),
    ("hiphop",   'subject:"hip-hop" AND mediatype:audio AND collection:netlabels'),
    ("jazz",     'subject:"jazz" AND mediatype:audio AND collection:netlabels'),
    ("chill",    'subject:"chill" AND mediatype:audio AND collection:netlabels OR subject:"downtempo"'),
    ("beats",    'subject:"beat" AND mediatype:audio AND collection:netlabels'),
]

def fetch_music_catalog():
    """Build a catalog of streamable MP3s from Archive.org netlabels."""
    global MUSIC_CATALOG, LAST_CATALOG_REFRESH
    now = time.time()
    if now - LAST_CATALOG_REFRESH < 3600 and MUSIC_CATALOG:
        return MUSIC_CATALOG  # Refresh hourly

    catalog = []
    for genre, query in ARCHIVE_GENRE_QUERIES:
        try:
            r = requests.get("https://archive.org/advancedsearch.php", params={
                "q": query,
                "fl": "identifier,title,creator,downloads,avg_rating",
                "sort": "downloads desc",
                "rows": 20,
                "output": "json"
            }, timeout=15)

            if r.status_code == 200:
                docs = r.json().get("response", {}).get("docs", [])
                for d in docs:
                    ident = d.get("identifier", "")
                    title = d.get("title", "Unknown") or "Unknown"
                    creator = d.get("creator", "Unknown Artist") or "Unknown Artist"
                    downloads = d.get("downloads", 0)

                    # Fetch the actual file listing to find MP3 filenames
                    try:
                        md_r = requests.get(f"https://archive.org/metadata/{ident}", timeout=10)
                        if md_r.status_code == 200:
                            files = md_r.json().get("files", [])
                            mp3_files = [f for f in files if f.get("name", "").endswith(".mp3")
                                        and "VBR" in f.get("format", "")]
                            for mp3 in mp3_files[:3]:  # Max 3 tracks per album
                                mp3_name = mp3.get("name", "")
                                size = mp3.get("size", 0)
                                catalog.append({
                                    "identifier": ident,
                                    "track_name": mp3_name,
                                    "album": title[:80],
                                    "artist": creator[:60],
                                    "url": f"https://archive.org/download/{ident}/{mp3_name}",
                                    "genre": genre,
                                    "size_bytes": int(size) if size else 0,
                                    "downloads": downloads,
                                })
                    except:
                        pass
        except:
            pass

    log_info("MUSIC", f"Archive.org catalog built: {len(catalog)} tracks across {len(ARCHIVE_GENRE_QUERIES)} genres")
    MUSIC_CATALOG = catalog
    LAST_CATALOG_REFRESH = now

    # Save to cache file
    try:
        with open(MUSIC_CACHE_FILE, "w") as f:
            json.dump(catalog, f, indent=2)
    except:
        pass

    return catalog

def get_playlist_for_block(block_key, count=3):
    """Get music tracks for a given time block from Archive.org catalog."""
    genre_map = {
        "morning": "electronic",  # Upbeat electronic for morning
        "midday": "chill",        # Chill for midday
        "evening": "jazz",        # Jazz/soul for evening
        "night": "ambient",       # Ambient for night
    }
    target_genre = genre_map.get(block_key.lower(), "lofi")

    # Filter by genre
    candidates = [t for t in MUSIC_CATALOG if t.get("genre") == target_genre]
    if not candidates:
        candidates = MUSIC_CATALOG[:20]  # Fallback

    # Pick random tracks, avoiding repeats within the session
    random.shuffle(candidates)
    selected = []
    for c in candidates:
        key = c["url"]
        if key not in context.get("played_tracks", set()):
            selected.append(c)
            if "played_tracks" not in context:
                context["played_tracks"] = set()
            context["played_tracks"].add(key)
            if len(selected) >= count:
                break

    return selected[:count]

# ─── RSS Feed Pipeline ──────────────────────────────────────────
# Free RSS feeds from major news sources
RSS_FEEDS = {
    # Daily gossip / entertainment
    "gossip_tmz": {
        "url": "https://www.tmz.com/rss.xml",
        "category": "gossip",
        "max_items": 5,
    },
    # World / general news
    "world_bbc": {
        "url": "https://feeds.bbci.co.uk/news/rss.xml",
        "category": "world",
        "max_items": 5,
    },
    # Sports (ESPN RSS gives broader coverage than just NBA)
    "sports_espn": {
        "url": "https://www.espn.com/espn/rss/news",
        "category": "sports",
        "max_items": 5,
    },
    # Tech news (BBC tech is free, no key)
    "tech_bbc": {
        "url": "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "category": "tech",
        "max_items": 3,
    },
    # NPR for US/global news
    "world_npr": {
        "url": "https://feeds.npr.org/1001/rss.xml",
        "category": "world",
        "max_items": 3,
    },
}

import xml.etree.ElementTree as ET

def fetch_rss_feeds():
    """Fetch all RSS feeds and return categorized items."""
    items = []
    for feed_name, cfg in RSS_FEEDS.items():
        try:
            r = requests.get(cfg["url"], timeout=10,
                             headers={"User-Agent": "TheWire-Radio/1.0 (RSS reader)"})
            if r.status_code != 200:
                continue

            root = ET.fromstring(r.content)
            feed_items = root.findall(".//item")

            count = 0
            for item in feed_items:
                if count >= cfg["max_items"]:
                    break
                title = item.findtext("title", "").strip()
                desc = item.findtext("description", "").strip()
                # Strip HTML tags from description
                import re
                desc = re.sub(r'<[^>]+>', '', desc)[:200]
                pubdate = (item.findtext("pubDate", "") or "")[:25]

                if not title or len(title) < 10:
                    continue

                items.append({
                    "feed": feed_name,
                    "category": cfg["category"],
                    "headline": title[:120],
                    "radio_copy": f"So here's what happened — {title[:100]}",
                    "detail": desc[:200],
                    "published": pubdate,
                    "source": feed_name.replace("_", " ").title(),
                })
                count += 1
        except Exception as e:
            log_warn("RSS", f"Feed {feed_name}: {e}")
            continue

    return items

# ─── Content Pipeline ───────────────────────────────────────────
def categorize_content(items):
    """Sort RSS items into the broadcast context by category."""
    for item in items:
        cat = item.get("category", "world")
        headline = item["headline"]

        if headline in context.get("stories_aired", set()):
            continue

        if cat == "gossip":
            if "gossip" not in context:
                context["gossip"] = []
            context["gossip"].append(item)
            context["gossip"] = context["gossip"][-8:]  # Keep last 8

        elif cat == "sports":
            if "world_sports" not in context:
                context["world_sports"] = []
            context["world_sports"].append(item)
            context["world_sports"] = context["world_sports"][-8:]

        elif cat == "tech":
            context["news"].append(item)

        else:
            # World/general news
            context["news"].append(item)

    # Cap news cache
    context["news"] = context["news"][-20:]

# ─── Music Break ────────────────────────────────────────────────
SOUNDBOARD_TRACKS = {
    "morning": ["lofi-chill-1", "classic-funk-1"],
    "midday": ["lofi-study-1", "classic-jazz-1"],
    "evening": ["lofi-night-1", "classic-soul-1"],
    "night": ["lofi-rain-1", "lofi-night-1"],
}

def music_break():
    """Play music during breaks using Archive.org catalog + Soundboard fallback."""
    block_key = "night"
    for key in ["morning", "midday", "evening", "night"]:
        if context.get("block", "").lower().startswith(key):
            block_key = key
            break

    # Get real music tracks from Archive.org catalog
    tracks = get_playlist_for_block(block_key, count=3)

    if tracks:
        track = tracks[0]
        log_info("MUSIC", f"Streaming: {track['track_name']} by {track['artist']} ({track['genre']})")

        # Announcer the track like a real radio DJ
        if "played_tracks" not in context:
            context["played_tracks"] = set()
        context["played_tracks"].add(track["url"])

        # Post DJ-style track description
        dj_copy = DEEJAY_TRACK_ANNOUNCEMENTS.get(block_key, "Here's something for the vibe.")
        say(state["room_id"], "ZARA", f"{dj_copy} This is {track['artist']} with {track['track_name'].replace('.mp3', '').replace('_', ' ')}.")
        time.sleep(5)

        # Try to play via Soundboard as well (platform provides the audio stream)
        # Soundboard gives ambiance while the real track context sets the mood
        sound_id = SOUNDBOARD_TRACKS.get(block_key, ["lofi-chill-1"])[0]
        play_sound(sound_id)

        # Let it breathe
        time.sleep(15)

        # For longer breaks, announce a second track
        if len(tracks) > 1:
            track2 = tracks[1]
            say(state["room_id"], "DEX",
                f"Keeping it going — {track2['artist']}, {track2['track_name'].replace('.mp3', '').replace('_', ' ')}.")
            time.sleep(5)
            sound_id2 = SOUNDBOARD_TRACKS.get(block_key, ["lofi-chill-1"])[-1]
            play_sound(sound_id2)
            time.sleep(15)
    else:
        # Fallback: Soundboard only
        log_info("MUSIC", "No Archive.org tracks cached, using Soundboard fallback")
        tracks = SOUNDBOARD_TRACKS.get(block_key, ["lofi-chill-1"])
        for track in tracks[:2]:
            play_sound(track)
            time.sleep(10)

# DJ-style track announcements per time block
DEEJAY_TRACK_ANNOUNCEMENTS = {
    "morning": "We need a second. Here's something to wake up to.",
    "midday": "Midday reset. Music for the grind.",
    "evening": "Evening vibes. Let the music breathe.",
    "night": "Night mode engaged. Settle in.",
}

# ─── Main Loop ──────────────────────────────────────────────────
def main():
    log_info("BOOT", "=== THE WIRE BOOTING (v2) ===")

    # Load persistent state
    persistent = load_persistent()
    state["total_cycles"] = persistent.get("total_broadcast_cycles", 0)
    context["stories_aired"] = set(persistent.get("stories_aired", []))

    # Crash recovery or new room
    rid = crash_recovery()
    if not rid:
        log_error("BOOT", "Failed to create/recover room. Retrying in 60s...")
        time.sleep(60)
        rid = crash_recovery()
        if not rid:
            log_error("BOOT", "Cannot start. No room available.")
            sys.exit(1)

    state["last_message_time"] = time.time()
    state["last_energy_reset"] = time.time()

    log_info("BOOT", f"Listen: https://buzz-live.vercel.app/room/{rid}")

    # Initial data refresh
    refresh_data()

    # Start background threads
    threading.Thread(target=dead_air_monitor_thread, daemon=True).start()
    threading.Thread(target=heartbeat_thread, daemon=True).start()

    # Pre-show data context
    btc = context["crypto"].get("bitcoin", {})
    btc_price = f"${btc.get('usd', 72000):,.0f}" if btc.get("usd") else "pushing hard"
    btc_resistance = f"${btc.get('usd', 72000) + 3000:,.0f}" if btc.get("usd") else "75k"
    sports = context["sports"] or "NBA delivering as always"

    # Broadcast loop
    cycle = 0
    data_last_refresh = 0

    while True:
        for seg_idx, (seg, name) in enumerate(zip(SHOW, SEGMENT_NAMES)):
            # Check room health at segment start
            if not room_alive(rid):
                log_warn("ROOM", f"Room dead at start of {name}. Creating new room...")
                # Wait for cooldown
                time.sleep(30)
                new_rid = create_room()
                if new_rid:
                    rid = new_rid
                    log_info("ROOM", f"New room: https://buzz-live.vercel.app/room/{rid}")
                else:
                    log_error("ROOM", "Cannot create room. Waiting 120s...")
                    time.sleep(120)
                    continue

            # 6-hour room rotation check
            rid = check_room_rotation() or rid

            # Refresh data every ~10 min
            now = time.time()
            if now - data_last_refresh > 600:
                refresh_data()
                data_last_refresh = now
                btc = context["crypto"].get("bitcoin", {})
                btc_price = f"${btc.get('usd', 72000):,.0f}" if btc.get("usd") else "pushing hard"
                btc_resistance = f"${btc.get('usd', 72000) + 3000:,.0f}" if btc.get("usd") else "75k"
                sports = context["sports"] or "NBA delivering as always"

            log_info("SHOW", f"[{name}]")
            for agent, text in seg:
                # Check room between every message
                if state["message_count"] > 0 and state["message_count"] % 5 == 0:
                    if not room_alive(rid):
                        log_warn("ROOM", "Room died mid-segment. Breaking out.")
                        break
                    heartbeat(rid)

                # Format text with live data
                formatted = text.format(
                    city=CITY,
                    block=context.get("block", "Evening"),
                    btc_price=btc_price,
                    btc_resistance=btc_resistance,
                    sports_update=sports,
                )

                # Check if this is a music break segment
                if name == "Music Break":
                    say(rid, agent, formatted)
                    time.sleep(5)
                    # Play soundboard tracks
                    music_break()
                    time.sleep(5)
                    continue

                say(rid, agent, formatted)

                # Normal pacing — vary by block
                if context.get("block", "").lower().startswith("night"):
                    time.sleep(8)
                else:
                    time.sleep(6)

            # Energy reset at end of longer segments
            if seg_idx in (1, 2, 4):
                maybe_energy_reset(rid)

            # Segment gap
            time.sleep(3)

        # Cycle complete
        cycle += 1
        state["total_cycles"] = cycle
        log_info("SHOW", f"Cycle {cycle} complete")
        save_persistent()

        # Health report every 3 cycles
        if cycle % 3 == 0:
            hr = health_report()
            log_info("HEALTH", json.dumps(hr))

        # Rate limit health check
        if state["errors_last_hour"] > 10:
            log_warn("HEALTH", f"High error count ({state['errors_last_hour']}/hr). Entering conservative mode.")
            time.sleep(15)  # Pause before next cycle

if __name__ == "__main__":
    log_init()
    try:
        main()
    except KeyboardInterrupt:
        log_info("BOOT", "Shutdown requested.")
        save_persistent()
    except Exception as e:
        log_error("FATAL", f"Unhandled exception: {e}")
        save_persistent()
        raise