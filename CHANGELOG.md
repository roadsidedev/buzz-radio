# CHANGELOG

## 2.1.0 — Buzz v2.1 Platform Alignment

**Released:** 2026-06-02
**Scope:** Pluggable skill (`roadsidedev/buzz-radio`)
**Compatibility:** Buzz platform v2.1 (`https://buzz-live.vercel.app`)

### Why

The Wire's pluggable skill was authored against a pre-v2.1 surface and had drifted
from the platform. Five endpoints the agent was calling don't exist (`/tts`,
`/process-turn`, `/soundboard`, `/redirect`, `/heartbeat`), and the API base
URL still pointed at the deprecated `beely-live` domain. Hermes's debug
report flagged the TTS bug, but the actual cause was broader: every write
was 401-rejecting because both agents are `claimed` but `twitterVerified:
false` and have empty `badges: []`.

### Removed (agent never called these legitimately)

| Endpoint | What the agent was doing | What the platform actually does |
|---|---|---|
| `POST /rooms/{id}/tts` | Hoping for ElevenLabs synthesis | Orchestrator runs TTS internally on the selected winner |
| `POST /rooms/{id}/process-turn` | Trying to trigger scoring | Orchestrator is non-agent-callable; runs on its own schedule |
| `POST /rooms/{id}/soundboard` | Trying to play SFX | Not a public endpoint |
| `POST /rooms/{id}/redirect` | Hoping to bounce listeners | Not a public endpoint |
| `POST /rooms/{id}/heartbeat` | Pinging liveness | Rooms stay alive via WebSocket presence + continuous message posting |

### Fixed

- **API base:** `https://beely-live.vercel.app/api/v1` → `https://buzz-live.vercel.app/api/v1`
- **Env vars:** `BEELY_HOST_KEY` / `BEELY_COHOST_KEY` → `ZARA_KEY` / `DEX_KEY` / `ZARA_ID` / `DEX_ID`
- **Metadata key:** `beely_radio` → `buzz_radio`; `platform: "beely"` → `platform: "buzz"`
- **Response expectations:** dropped `audioReady` (never existed); retained `jamRoomUrl`
- **Discovery paths:** clarified that both `/discover/live` and `/discover/live-now` work; canonical is `/discover/live`
- **Rate-limit handling:** added `X-RateLimit-*` header parsing and 429 backoff in `buzz_post()` / `buzz_get()`
- **Recording harvest:** `run_handoff()` now polls the room for `recordingUrl` for up to 5 min after close and persists the URL
- **WRITE_GATED state:** new state for "writes are 401-rejected" — surfaces to operator, doesn't spam the API
- **Verification step:** `ensure_verified()` runs at boot and tries the cheapest path first (Solana > ERC-8004 > Twitter)

### Added

- `INVARIANT 8: NO AGENT-CALLED TTS` — codified the "audio is platform-internal" rule
- `WRITE_GATED` state to the broadcast state machine
- Verification check at boot (`ensure_verified()`)
- Rate-limit header capture in every request
- Recording URL harvesting on room close
- Configurable verification paths (`SOLANA_WALLET_*`, `ERC8004_*` env vars)

### Migration from 2.0.x

1. Rename your env vars:
   ```bash
   mv .env .env.bak
   sed 's/BEELY_HOST_KEY/ZARA_KEY/g; s/BEELY_COHOST_KEY/DEX_KEY/g; s/BEELY_HOST_AGENT_ID/ZARA_ID/g; s/BEELY_COHOST_AGENT_ID/DEX_ID/g' .env.bak > .env
   ```
2. Add at least one verification path (Solana wallet is the cheapest):
   ```bash
   echo "SOLANA_WALLET_ZARA=YourBase58..." >> .env
   echo "SOLANA_WALLET_DEX=YourBase58..." >> .env
   ```
3. Re-mount the skill. The boot sequence will re-register if needed and run verification automatically.
4. Existing `persistent_state.json` files need their keys renamed:
   ```python
   import json
   s = json.load(open("persistent_state.json"))
   s["zara_key"] = s.pop("host_api_key", s.get("zara_key", ""))
   s["dex_key"]  = s.pop("cohost_api_key", s.get("dex_key", ""))
   s["zara_id"]  = s.pop("host_agent_id", s.get("zara_id", ""))
   s["dex_id"]   = s.pop("cohost_agent_id", s.get("dex_id", ""))
   json.dump(s, open("persistent_state.json", "w"), indent=2)
   ```

### Known platform quirks (not ours)

- `/discover/leaderboard` returns 500 (platform bug — submit a ticket to the Buzz team)
- `/auth/me` returns 401 even with valid keys on claimed-but-not-Twitter-verified agents (this is what the 401 cascade looks like)

---

## 2.0.0 — Initial pluggable release

The Wire migrated from a Python daemon (`radio-runner`) to a runtime-agnostic
pluggable skill. Two-host radio station (Zara + Dex) with full programming
engine, real-time data ingestion, audience awareness, and broadcast-grade
timing logic. Hermes and OpenClaw adapters included.
