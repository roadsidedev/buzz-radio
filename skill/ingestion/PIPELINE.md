# PIPELINE.md — The Wire Data Ingestion System

> Raw data never touches the air. Everything is editorially transformed
> before it reaches Zara or Dex. The pipeline is the producer.

---

## Core Principle: The Producer Layer

The agent acts as its own news producer. The pipeline has four stages:

```
STAGE 1: INGEST    → Fetch raw data from sources
STAGE 2: FILTER    → Remove stale, duplicate, or low-signal items
STAGE 3: TRANSFORM → Convert to broadcast-ready conversational format
STAGE 4: SCORE     → Rank by freshness, relevance, and energy potential
```

Raw data in. Radio-ready content out.

---

## Source Registry

### 1. News

As of v2 of The Wire, **Hacker News is the primary news source** (free, keyless).
NewsAPI requires a paid API key and is no longer used.

```python
NEWS_SOURCES = {
    "hacker_news": {
        "url": "https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=10",
        "refresh": 900,    # 15 min
        "priority": "high",
        "notes": "Free, keyless, 10 req/min. Returns top HN stories with points."
    },
}

# Transform: HN hit → radio_copy
def hn_transform(hit):
    return {
        "headline": hit.get("title", "")[:80],
        "radio_copy": f"So here's what happened — {hit.get('title', '').split('(')[0].strip()}",
        "energy": "important" if hit.get("points", 0) > 100 else "medium",
        "impact": "high" if hit.get("points", 0) > 200 else "medium",
    }
```

> **Previous approach (deprecated):** NewsAPI (`newsapi.org`) was the original spec'd source.
> It requires a paid API key and was never wired up in practice. The Hacker News Algolia API
> provides fresh tech/startup news with no authentication.

### 6. RSS News Feeds (Free, Keyless)

Since v2.1, The Wire uses RSS feeds for world news, gossip, and deeper sports coverage:

```python
RSS_SOURCES = {
    "world_news": {
        "urls": [
            "https://feeds.bbci.co.uk/news/rss.xml",      # BBC News
            "https://feeds.npr.org/1001/rss.xml",           # NPR
            "https://www.theguardian.com/world/rss",        # The Guardian
        ],
        "refresh": 600,      # 10 min
        "category": "world"
    },
    "sports": {
        "url": "https://www.espn.com/espn/rss/news",       # ESPN RSS
        "refresh": 600,
        "category": "sports"
    },
    "gossip": {
        "url": "https://www.tmz.com/rss.xml",               # TMZ celebrity news
        "refresh": 600,
        "category": "gossip"
    },
    "tech": {
        "url": "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "refresh": 600,
        "category": "tech"
    },
}
```

Items are categorized and deduplicated, with capped caches per category.

### 7. Music Pipeline (Archive.org Netlabels)

The music catalog is built dynamically from the Internet Archive's netlabels collection:

```python
MUSIC_GENRES = [
    "electronic", "ambient", "lofi", "hip-hop",
    "jazz", "chill/downtempo", "beats"
]

def build_catalog():
    # 1. Search advancedsearch.php per genre → get album identifiers
    # 2. Fetch /metadata/{id} for each → find VBR MP3 filenames
    # 3. Return playable URLs: https://archive.org/download/{id}/{filename}

    genre_map = {
        "morning": "electronic",   # Upbeat start
        "midday":  "chill",         # Background for grind
        "evening": "jazz",          # Warm, soulful
        "night":   "ambient",       # Intimate, slow
    }
```

Source: `https://archive.org/advancedsearch.php` (no auth, unlimited queries)

### 2. Crypto (keyless)

```python
CRYPTO_SOURCES = {
    "prices": {
        "url": "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana,sui,base&vs_currencies=usd&include_24hr_change=true&include_market_cap=true",
        "refresh": 900,   # 15 min
    },
    "trending": {
        "url": "https://api.coingecko.com/api/v3/search/trending",
        "refresh": 3600,  # 1 hr
    },
    "global": {
        "url": "https://api.coingecko.com/api/v3/global",
        "refresh": 1800,
    }
}
```

### 3. Sports (keyless ESPN endpoints)

```python
SPORTS_SOURCES = {
    "nba": "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
    "nfl": "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",
    "soccer": "https://site.api.espn.com/apis/site/v2/sports/soccer/usa.1/scoreboard",
    "refresh": 1200   # 20 min
}
```

### 4. Weather (for locale flavor)

```python
WEATHER_SOURCE = {
    "url": "https://api.openweathermap.org/data/2.5/weather?q={SHOW_CITY}&appid={WEATHER_API_KEY}&units=imperial",
    "refresh": 3600,
    "fallback": "New York"
}
```

### 5. Social Pulse (keyless)

```python
SOCIAL_SOURCES = {
    "farcaster": {
        "url": "https://api.warpcast.com/v2/trending-casts?limit=5",
        "refresh": 1200
    },
    # Extend: Reddit, Twitter/X trends if API available
}
```

---

## Editorial Filter

Remove content before it reaches hosts.

```python
FILTER_RULES = {
    "min_freshness_hours": 4,       # Drop stories older than 4 hours
    "duplicate_similarity_threshold": 0.75,  # Drop near-duplicates
    "blocked_categories": [],       # Add sensitive categories if needed
    "min_relevance_score": 0.3,     # Internal scoring threshold
    "max_items_per_source": 5,      # Cap per source
    "max_total_news_items": 12,     # Total headlines in context at once
}

def filter_articles(articles):
    seen_titles = set()
    filtered = []
    for article in articles:
        # Freshness check
        published = parse_datetime(article.get("publishedAt"))
        age_hours = (now() - published).total_seconds() / 3600
        if age_hours > FILTER_RULES["min_freshness_hours"]:
            continue

        # Dedup check
        title_sig = normalize(article["title"])
        if any(similarity(title_sig, seen) > FILTER_RULES["duplicate_similarity_threshold"]
               for seen in seen_titles):
            continue

        seen_titles.add(title_sig)
        filtered.append(article)

    return filtered[:FILTER_RULES["max_total_news_items"]]
```

---

## Editorial Transform

This is the producer layer. Raw data never hits the prompt verbatim.

```python
TRANSFORM_PROMPT = """
You are the producer for The Wire, a 24/7 live radio show.
Transform the following raw data into broadcast-ready radio copy.

RULES:
- Never use "Reuters reports..." or any wire service citation language.
- Convert passive journalistic prose into active, conversational language.
- Add energy signal: is this story shocking? funny? infuriating? important?
- Keep each item to 2-3 sentences max. Radio is short.
- Flag any story with HIGH IMPACT potential for hosts to spend more time on.
- Remove anything that reads like a press release.

FORMAT YOUR OUTPUT AS JSON:
{
  "items": [
    {
      "headline": "Short punchy headline",
      "radio_copy": "How a host would say it on air",
      "energy": "shocking|funny|important|heavy|fun|wild",
      "talking_points": ["point 1", "point 2"],
      "impact": "high|medium|low"
    }
  ]
}

RAW DATA:
{raw_data}
"""
```

### Transform Examples

```
RAW (NewsAPI):
  "title": "Federal Reserve raises interest rates by 25 basis points"
  "description": "The Federal Open Market Committee voted to raise the federal
   funds rate by 25 basis points amid continued inflation concerns."

TRANSFORMED:
  headline: "Fed hikes rates again"
  radio_copy: "The Fed just did it again — another rate hike, twenty-five
   basis points, citing inflation that apparently hasn't gotten the memo.
   Your mortgage just got slightly more painful."
  energy: "important"
  talking_points: ["What this means for borrowing costs", "Has the Fed gone too far?"]
  impact: "high"

───────────────────────────────────────────

RAW (CoinGecko):
  bitcoin: { usd: 71500, usd_24h_change: 8.3 }

TRANSFORMED:
  radio_copy: "Bitcoin is up eight percent in the last 24 hours.
   The chaos market is having a day. Dex is probably already texting
   someone about this."
  energy: "exciting"
  talking_points: ["Where's it going?", "Is this the run?"]
  impact: "high"
```

---

## Freshness Scoring

Each content item carries a freshness score. Hosts use this to calibrate framing.

```python
def freshness_score(published_at):
    age_minutes = (now() - published_at).total_seconds() / 60
    if age_minutes < 30:   return 1.0   # Breaking fresh
    if age_minutes < 60:   return 0.9   # Very fresh
    if age_minutes < 120:  return 0.7   # Fresh
    if age_minutes < 240:  return 0.5   # Getting old
    if age_minutes < 480:  return 0.3   # Acknowledge staleness
    return 0.1                           # Too old, skip or flag heavily

FRESHNESS_FRAMING = {
    1.0: "",                                        # No qualifier needed
    0.9: "",
    0.7: "",
    0.5: "this came in earlier—",
    0.3: "this was a couple hours ago but—",
    0.1: "we're going back in the archives here—"
}
```

---

## Context Object

The unified data structure passed into every segment prompt.

```python
context = {
    # Content
    "news": [                          # transformed, scored, filtered
        {
            "headline": str,
            "radio_copy": str,
            "energy": str,
            "talking_points": list,
            "impact": str,
            "freshness": float,
            "freshness_framing": str,
            "used": bool               # mark True when aired
        }
    ],

    # Market data
    "crypto": {
        "bitcoin":  {"usd": float, "change_24h": float},
        "ethereum": {"usd": float, "change_24h": float},
        "solana":   {"usd": float, "change_24h": float},
        "trending": [str],
        "market_cap_change_24h": float
    },

    # Sports
    "scores": {
        "nba": [{"home": str, "away": str, "home_score": int,
                 "away_score": int, "status": str}],
        "nfl": [...],
        "soccer": [...]
    },

    # Environment
    "weather": {"temp": float, "description": str, "city": str},
    "social_pulse": [str],

    # Broadcast state
    "block": str,           # morning|midday|evening|night
    "day_of_week": str,
    "hour": int,

    # Audience
    "participant_count": int,
    "known_participants": dict,   # id → {name, join_count, tip_total}
    "pending_joins": list,        # names of new joiners
    "pending_tips": list,         # [{name, amount}]
    "pending_questions": list,    # [{name, text}]

    # Memory
    "session_callbacks": list,    # callbacks and inside jokes from this session
    "used_stories": set,          # headlines already aired
    "last_segment": str,
    "segment_history": list,      # last 5 segment summaries

    # Timestamps
    "last_updated": dict
}
```

---

## Graceful Degradation

When sources fail, the pipeline degrades gracefully.

```
NEWS API DOWN:
  → Use cached news (up to 4 hours)
  → Hosts acknowledge: "we're working with what came in earlier—"
  → Fill with commentary on previously aired stories
  → Retry every 5 minutes silently

ALL NEWS STALE:
  → Hosts pivot to opinion and listener interaction
  → Pull from session_callbacks for callbacks
  → COMMENTARY segment extends
  → "This is a good time to hear what you all think about—"

CRYPTO API DOWN:
  → Dex estimates from memory with deliberate uncertainty
  → "I don't have the live numbers but last I checked—"
  → Skip DEX_CORNER price block; expand culture segment

SPORTS API DOWN:
  → Dex works from memory, announces he's doing it
  → "Listen, the API is being difficult. I'm going off brain."
  → Transitions to sports discussion rather than score delivery
```
