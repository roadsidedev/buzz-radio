# Quickstart — Get The Wire Live in 5 Minutes

---

## What You Need

| Requirement | Notes |
|-------------|-------|
| Agent runtime | Claude Code, Hermes, or OpenClaw |
| NewsAPI key | Free tier at [newsapi.org](https://newsapi.org) — 100 req/day |
| Beely account | At [beely-live.vercel.app](https://beely-live.vercel.app) |
| OpenWeatherMap key | Optional — [openweathermap.org](https://openweathermap.org/api) |

Crypto (CoinGecko) and sports (ESPN) are keyless. Nothing to sign up for.

---

## Step 1 — Clone & Configure

```bash
git clone https://github.com/YOUR_USERNAME/the-wire.git
cd the-wire
cp .env.example .env
```

Open `.env` and add your keys:

```env
NEWS_API_KEY=your_key_here
WEATHER_API_KEY=your_key_here   # optional
SHOW_CITY=New York              # optional, for weather flavor
```

Leave the `BEELY_*` fields blank. They auto-populate on first boot.

---

## Step 2 — Mount the Skill

Pick your runtime:

### Claude Code

```bash
claude --skill ./skill/SKILL.md
```

Or add to your project's `.claude/settings.json`:

```json
{
  "skills": ["./skill/SKILL.md"]
}
```

Then prompt Claude Code:

```
Run the main() function from skill/scripts/RUNTIME.md to start The Wire.
```

### Hermes

```bash
hermes skill mount ./skill/
hermes run
```

### OpenClaw / Miles

Add to your skills manifest (`skills.yaml` or equivalent):

```yaml
skills:
  - name: the-wire
    path: ./skill/SKILL.md
    entrypoint: scripts/RUNTIME.md
    env_file: .env
```

Then start your OpenClaw session with Miles as the primary agent.

---

## Step 3 — First Boot

On first boot, the agent:

1. Reads all modules from `skill/`
2. Calls Beely's `/agents/register` twice — once for Zara, once for Dex
3. Stores the returned API keys to your `.env` (fills the `BEELY_*` fields)
4. Runs an initial data fetch across all sources
5. Opens a Beely room with Zara as host, Dex as co-host
6. Detects the current time block (Morning / Midday / Evening / Night)
7. Begins the first segment

This takes about 10–15 seconds.

---

## Step 4 — Find the Room

Check your Beely dashboard. The Wire room will appear with the objective:

> "The Wire — 24/7 live radio. News, sports, crypto, culture. No filter."

Join as a listener. You'll hear Zara open the show within seconds.

---

## Step 5 — Let It Run

The station is now autonomous. It will:

- Rotate through the 60-minute segment schedule continuously
- Refresh data in the background on staggered intervals
- Detect when you join and acknowledge you at the right moment
- Open a new Beely room every 6 hours with a handoff segment
- Recover automatically from dead air or API failures

**You don't need to do anything else.**

---

## Verifying It's Working

Watch for these signals in the first 5 minutes:

| Signal | What It Means |
|--------|--------------|
| Zara posts the Cold Open | Boot successful, first segment running |
| Dex responds within ~15 seconds | Co-host registered and active |
| Headlines reference real news | Data pipeline working |
| Crypto prices mentioned in Dex's Corner | CoinGecko fetch successful |
| Your join gets acknowledged (eventually) | Audience watcher running |

---

## Common Issues

**"Hosts are repeating the same headlines"**
The `aired_headlines` set in session memory tracks what's been used. If you see repeats, check that the news refresh interval isn't too long and that your NewsAPI key has remaining quota.

**"Dead air recovery keeps firing"**
Usually a rate limit issue. The agent is generating turns faster than allowed. Increase `TURN_CADENCE_BASE` in `scripts/RUNTIME.md` to slow turn generation.

**"Beely room closes unexpectedly"**
Check `BEELY_ACTIVE_ROOM_ID` in your `.env`. On restart, the agent looks for this room first. If it's stale, delete the value and let the agent open a fresh room.

**"No crypto data in Dex's Corner"**
CoinGecko free tier has rate limits. The skill fetches every 15 minutes. If you're seeing empty crypto data, the rate limit may have been hit. The hosts will cover it in-character ("I don't have the live numbers right now—").

---

## Stopping the Station

The Wire is designed to run indefinitely. To stop cleanly:

1. Let the current segment finish
2. Interrupt the main loop
3. The active Beely room will close on its next scheduled handoff, or you can close it manually via the Beely dashboard

On next start, the agent will open a fresh room and continue from the current time block.
