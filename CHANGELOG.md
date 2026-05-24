# Changelog

All notable changes to The Wire will be documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [2.0.0] — 2026-05-17

### Added
- Full modular architecture — skill split into 10 dedicated modules
- `personalities/PERSONAS.md` — complete character specs for Zara and Dex including chemistry rules, running bits, interruption protocols, and linguistic patterns
- `schedules/PROGRAMMING.md` — four time blocks (Morning Rush, Midday, Evening, Night Shift) with energy profiles, weekly variation, and special programming triggers
- `segments/SEGMENTS.md` — per-segment definitions with data requirements, success criteria, and failure modes
- `ingestion/PIPELINE.md` — four-stage editorial pipeline (Ingest → Filter → Transform → Score) with freshness scoring and graceful degradation
- `memory/STATE.md` — broadcast state machine with 8 named states and three-layer memory architecture (rolling, session, persistent)
- `transitions/FLOW.md` — radio physics: turn anatomy, 4-minute reset law, energy pairing rules, five named transition patterns, interruption protocols, comedic timing rules
- `moderation/RULES.md` — content boundaries, audience handling constraints, editorial standards
- `prompts/TEMPLATES.md` — turn-by-turn LLM prompt instructions for all 12 segment types plus emergency templates
- `scripts/RUNTIME.md` — full executable pseudocode covering all 9 boot/execution steps
- Special programming triggers: BREAKING_NEWS, CRYPTO_SURGE, BIG_GAME, HIGH_AUDIENCE, TIPPING_SURGE
- Callback engine for cross-segment continuity
- Three-layer audience awareness: join detection, tip ceremony, question queuing
- VIP listener tracking across sessions
- 6-hour room rotation with continuity handoff segments
- Dead air monitor with automatic recovery
- GitHub Actions CI workflow for skill structure validation
- Issue templates (bug report, feature request)
- `docs/architecture.md`, `docs/quickstart.md`, `docs/extending.md`
- `examples/segment-transcript.md`, `examples/context-object.json`

### Changed
- Complete rewrite from v1 monolithic SKILL.md to modular broadcast OS

---

## [1.0.0] — 2026-05-17

### Added
- Initial monolithic SKILL.md with Zara and Dex personas
- Basic 60-minute segment schedule
- NewsAPI, CoinGecko, ESPN, OpenWeatherMap, Farcaster integrations
- Room lifecycle management with 6-hour rotation
- Basic audience awareness (join events, tips, questions)
- Dead air prevention (90-second trigger)
- Claude Code, Hermes, OpenClaw adapter notes
