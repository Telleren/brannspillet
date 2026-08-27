# Brannspillet – Codex instructions

Before making substantial changes, read PROJECT_CONTEXT.md.

## Project
Brannspillet is a Norwegian SK Brann football quiz/game project built from structured historical match data.

## Working principles
- Preserve all raw Branntall JSON files unchanged.
- Never invent or silently correct historical data.
- Distinguish raw source data, inferred data, and explicitly sourced corrections.
- Prefer stable IDs over player/team names.
- SQLite database is derived and may always be rebuilt from raw data + correction/enrichment files.
- Do not weaken database constraints just to make imports succeed.
- When encountering data inconsistencies, inspect the source data first and handle the case explicitly.
- Keep solutions understandable for a novice Python developer.
- Prefer complete, maintainable fixes over fragile one-off patches.
- Run relevant validation/audit scripts after database changes.
- Preserve natural lineup order from the original squad order; do not sort lineups by shirt number.

## Canonical data
- Raw match JSON: data/raw/
- Canonical database: data/brannspillet_v2.db
- Historical sandbox database: data/brannspillet_historical_sandbox.db
- Explicit event corrections: data/corrections.json
- Verified shirt-number enrichment: data/shirt_number_enrichments.json

## Current raw archive
- data/raw/ now contains 2,554 Branntall JSON files from 1911-06-21 through 2026-08-23.
- Pre-2000 raw backfill was scraped via crawler_backwards.py and indexed in data/matches_backfill_pre2000.csv.
- Pre-2000 raw data has known validation issues and is imported only into the historical sandbox database for now.
- build_db_v2.py defaults to the validated 2000-onward canonical v2 subset. Use --historical-sandbox for the pre-2000 sandbox.

## Important validation targets
Current expected Brann figures for the validated v2 database subset, 2000 onward:
- 965 matches
- 10,615 starts
- 2,971 substitute appearances
- 13,586 total appearances
- 93 Brann appearances reconstructed from events
- 2 explicit event corrections
- 0 historical squad-entry corrections in canonical v2
- 0 unresolved Brann appearance inconsistencies

Current expected historical sandbox figures, pre-2000:
- 1,589 matches
- 16,635 Brann starts
- 1,648 Brann substitute appearances
- 18,284 total Brann appearances
- 47 Brann appearances reconstructed from events
- 9 explicit squad-entry exclusions
- 1 Brann appearance with unknown start status
- 1,414 Hvem mangler-eligible matches with exactly 11 Brann starters

Run audit_db_v2.py after changes that affect imports/database structure.
Run audit_historical_import.py after changes that affect pre-2000 import behavior.

## Current application work
Current prototype: hvem_mangler.py
- Streak mode with three lives; the third wrong answer ends the game.
- User chooses a year range from 1963 through 2026 before starting.
- Candidate matches must have exactly 11 Brann starters in the derived database.
- Historical pre-2000 candidates come from data/brannspillet_historical_sandbox.db.
- One Brann starter hidden per lineup.
- Show a visible placeholder at the hidden starter's natural lineup position.
- Hidden player is randomly chosen from the five starters with the fewest Brann appearances in that calendar year.
- Natural lineup order comes from original squad insertion order.
- Shirt number priority:
  1. exact match data
  2. verified shirt_number_enrichments.json
  3. unambiguous same-season inference
  4. "?" if still unknown

Current static beta: docs/hvem-mangler/
- GitHub Pages-compatible static version of Hvem mangler.
- Generated puzzle data lives in docs/hvem-mangler/puzzles.json.
- Regenerate it with export_hvem_mangler_pages_data.py after changes to eligible data, hidden-player logic, or shirt-number display.
- Static beta includes a first autocomplete pass based on players from the selected year range, excluding visible starters in the current lineup.
- The static beta includes answers client-side and is meant for informal beta testing, not anti-cheat production use.

Current Tenable foundation: tenable.py
- Terminal prototype for top-10 list questions.
- Default year range is 1963 through 2026, but the script can query 1911 through 2026.
- Implemented themes: appearances, starts, substitute appearances, goals, foreign-player appearances, foreign-player goals, wins, appearances against an opponent, goals against an opponent.
- A question must have 10 visible answer slots and a configurable minimum value at 10th place.
- If 10th place is tied, any player in the cutoff tie group can fill the relevant open slot.
- Current minimum 10th-place values: appearances 50, starts 35, substitute appearances 20, goals 10, foreign-player appearances 50, foreign-player goals 10, wins 30, opponent appearances 5, opponent goals 3.
- Foreign-player themes use known non-Norwegian country_code only; unknown nationality is excluded rather than guessed.
- Three lives; the third wrong answer ends the question.
- Coach-based themes are not implemented because the current database has no coach/manager table.
