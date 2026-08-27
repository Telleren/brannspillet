# Brannspillet – Project Context

_Last updated: 2026-08-27_

This file is the canonical handoff/context document for continued development of **Brannspillet** in Codex / VS Code.

Before making substantial changes, read this entire file together with `AGENTS.md` if present.

---

# 1. Project overview

**Brannspillet** is a Norwegian football quiz/game project focused primarily on **Sportsklubben Brann** and, potentially later, Norwegian football more broadly.

The project grew out of an idea for a landing page / app containing several daily or recurring football games inspired by products such as Wordle, Connections, Football 501, 30-0 / 38-0, FootEX Pointless, Tenable, Guess the Career, etc.

The key strategic decision is:

> Do not build a quiz site that requires manually writing a new quiz every day.  
> Build a strong football database that can automatically generate valid games.

The project is currently in a local Python + SQLite prototype phase.

The user is a beginner/intermediate Python user and prefers concrete, maintainable solutions with full replacement files when practical. Avoid unnecessary framework complexity unless it materially improves the project.

---

# 2. Current game ideas

Several game concepts were discussed. The most relevant are:

## 2.1 Hvem mangler?

Current active prototype.

Mechanic:
- Show a historical Brann starting XI.
- Remove exactly one starter.
- User guesses the missing player.
- Current prototype uses streak mode.
- Rounds currently get progressively older as a crude difficulty proxy.

Important design intent:
- Starting XI order should look like a natural football lineup.
- Do **not** sort players by shirt number.
- Preserve the original squad ordering from Branntall because testing showed this corresponds to natural positional order, e.g. right back → centre back → centre back → left back.

Current prototype file:
- `hvem_mangler.py`

## 2.2 Rødtrøyen

Football-Wordle-style game:
- Automatically select one Brann player per day.
- Guesses compared using attributes such as nationality, position, birth year, debut, appearances, goals, etc.

Not yet implemented.

## 2.3 Tenable / Top 10

Database-generated ranking questions:
- top scorers
- most appearances
- most games against a club
- etc.

Current foundation prototype:
- `tenable.py`
- terminal-only
- three lives
- explicit SQL-backed top-10 themes
- filters out thin lists with a configurable minimum value at 10th place
- accepts any player in a tie group that crosses 10th place
- random playable question support

Current minimum 10th-place values:
- appearances: 50
- starts: 35
- substitute appearances: 20
- goals: 10
- foreign-player appearances: 50
- foreign-player goals: 10
- wins: 30
- appearances against opponent: 5
- goals against opponent: 3

Foreign-player Tenable definition:
- `players.country_code IS NOT NULL`
- `players.country_code != 'NO'`
- unknown nationality is excluded rather than guessed

Currently implemented themes:
- most Brann appearances
- most Brann starts
- most Brann substitute appearances
- most Brann goals
- most Brann appearances by foreign players
- most Brann goals by foreign players
- most Brann wins appeared in
- most Brann appearances against a selected opponent
- most Brann goals against a selected opponent

Coach/manager themes are not implemented yet because the current SQLite schema does not include coach data.

## 2.4 Fotball Sudoku / Grid

3x3 intersection grid generated from database criteria.

Needs:
- sufficiently rich player/team/career data
- validator ensuring every cell has enough possible answers

Not yet implemented.

## 2.5 Før eller etter?

Chronology game based on dated Brann events.

Would require a separate manually curated / enriched timeline dataset.

Not yet implemented.

## 2.6 Connections

Good game idea, but likely needs heavy manual curation.

Recommended as occasional / weekly special rather than a core daily auto-generated game.

---

# 3. Primary data source: Branntall

Main source:
- `branntall.no`

Technical discovery:
- Branntall is built with Gatsby + Sanity.
- Gatsby exposes structured `page-data.json` endpoints.
- Sanity project ID observed: `i7f14d81`
- dataset: `production`

Important discovery:
- Match pages expose a full current match object under:

```python
data["result"]["data"]["model"]
```

The page JSON also contains `prev` and `next` full match objects.

**Never import `prev` and `next` as additional matches.**

Only:

```python
data["result"]["data"]["model"]
```

is the actual page match.

---

# 4. Branntall match URL / crawl model

Known match page pattern:

```text
/{YYYY}/{MM}/{DD}/{homeSlug}-{awaySlug}/
```

Example:

```text
/2012/05/10/floro-brann/
```

Page-data endpoint:

```text
https://branntall.no/page-data/{path}/page-data.json
```

Important finding:
- A match object's `next` field contains enough data to construct the next chronological route.
- `next` traverses across league, cup and European matches.
- This made it possible to enumerate the full match history one request per match.

Initial crawl start:

```text
/2000/04/09/brann-viking/
```

Natural data cutoff chosen:
- 1 January 2000 onward.

Current dataset ends at:

```text
2026-08-23 Fyllingen–Brann 0-4
```

Current local date at the time of this context:
- 2026-08-26

---

# 5. Raw data archive

Raw Branntall JSON files are stored under:

```text
data/raw/
```

Current count:

```text
2,554 JSON files
```

Period:

```text
1911-06-21 through 2026-08-23
```

The current validated v2 database still imports only the 2000-onward subset:

```text
2000-04-09 through 2026-08-23
965 matches
```

Pre-2000 raw data was backfilled on 2026-08-27 and is now imported into a separate historical sandbox database. It is still not integrated into the canonical v2 database.

Critical principle:

> Raw Branntall JSON must remain unchanged.

All corrections, normalization, inference and enrichment must happen in:
- parser/import code
- correction files
- enrichment files
- derived SQLite database

Do not manually patch raw JSON files.

This is a foundational project rule.

---

# 6. Crawler

Main crawler:

```text
crawler.py
```

Important properties:
- polite request delay: 1 second
- retry logic
- restartable
- checkpointing
- writes raw JSON files
- maintains CSV index
- user agent identifies Brannspillet research project
- follows the chronological `next` chain
- detects already downloaded data

Current index:

```text
data/matches.csv
```

Index fields include:

```text
date
home_team
away_team
score
competition
season
path
match_id
filename
```

Current crawl result:

```text
Kamper totalt: 965
Nye kamper in final full crawl: 758
```

Earlier crawl already had 207 matches through 2005.

Backwards pre-2000 crawler:

```text
crawler_backwards.py
```

Purpose:
- follows the chronological `prev` chain from the earliest local 2000 match
- starts from the previous Branntall match before `2000-04-09 Brann-Viking`
- stores only actual page `model` matches, never `prev`/`next` as additional matches
- writes raw JSON to `data/raw/`
- does not overwrite existing raw files
- maintains a separate backfill index

Backfill index:

```text
data/matches_backfill_pre2000.csv
```

Backfill validation report:

```text
data/validation_backfill_pre2000.csv
```

Backfill result:

```text
New pre-2000 matches: 1,589
Period: 1911-06-21 through 1999-10-30
First match in backfill chain: 1999-10-30 Brann-Rosenborg 0-2
Oldest match reached: 1911-06-21 Brann-Bergens Sportsklub 8-0
Crawler stopped because Branntall returned no previous match.
```

---

# 7. Raw-data validation

Validator:

```text
validate.py
```

Full validation report:

```text
data/full_validation.csv
```

Current full raw dataset validation after pre-2000 backfill:

```text
JSON-filer:             2554
Gyldige kampobjekter:   2554
Unike kamp-ID-er:       2554
Troppsoppføringer:      35855
Registrerte startere:   27252
Kamphendelser:          22472

ERROR:                   2
WARNING:                 286
```

The previous 965-match, 0-error/2-warning validation target now applies specifically to the 2000-onward v2 database subset, not the entire raw archive.

Backfill validation summary:

```text
Issues: 286
ERROR:    2
WARNING: 284
```

Main observed pre-2000 issue categories:
- many incomplete Brann lineups, especially early/pre-war matches, including matches with 0-10 registered starters
- five backfilled matches with 12 registered Brann starters
- one backfilled match with 13 registered Brann starters
- 62 goals missing scorer
- 40 substitutions missing `subOff`
- 6 substitutions missing `subOn`
- 2 real events missing team ID
- 2 duplicate Brann squad-player errors

The duplicate Brann squad-player errors are:

```text
1979-09-09 Start-Brann: Ingvald Huseklepp duplicated in Brann squad
1937-06-21 Brann-Årstad: Leif Magnus Eriksen duplicated in Brann squad
```

Important invariant for the current validated v2 database subset:

```text
965 matches × 11 Brann starters = 10,615
```

Every one of the 965 imported 2000-onward matches has exactly 11 registered Brann starters.

This is especially important for `Hvem mangler?`.

---

# 8. Event types observed

Across the full 2,554-match raw archive:

```text
None                              17
assist                           916
goal                            8068
ownGoal                          158
penaltyGoal                      508
penaltyMiss                       80
rc                               182
shootoutGoal                     166
shootoutMiss                      46
subApp                          8790
yc                              3541
```

The `None` events were inspected.

They include markers such as:

```json
{
  "type": {
    "name": "Straffekonk",
    "countAs": null
  }
}
```

These are not player events and do not need team/player IDs.

The validator was updated accordingly.

---

# 9. Known raw-data irregularities

Several source-data inconsistencies were discovered and intentionally handled.

## 9.1 Penalty goals sometimes store scorer in `player`

Some Branntall penalty-goal events have:

```python
event["scoredBy"] == None
event["player"] == actual_scorer
```

Therefore scorer normalization must use:

```python
scorer = event.get("scoredBy") or event.get("player")
```

for goal-type events.

Examples included:
- Niklas Sandberg
- Philip Zinckernagel
- Amahl Pellegrino
- Sammy Skytte

Do not regress this logic.

## 9.2 Alternative team ID in Arna-Bjørnar–Brann 2019

Match:

```text
2019-05-01 Arna-Bjørnar–Brann 1-6
```

The match object identifies Arna-Bjørnar with:

```text
aba28db1-8589-4f92-b93c-e5813e00e84c
```

but several Arna-Bjørnar events use:

```text
40cd0e6c-274c-5f6e-9f63-e214a05c258f
```

The importer therefore includes general event-team normalization.

If event team ID is not equal to home or away team:
- inspect players referenced by the event
- compare those player IDs with home/away squad player IDs
- if all evidence points to one side, normalize to that match team ID
- otherwise use `NULL`
- never blindly disable foreign keys

Function introduced:

```python
resolve_event_team_id(...)
```

Keep this general, not hardcoded to Arna-Bjørnar.

## 9.3 Duplicate Fyllingen squad entry

Match:

```text
2026-08-23 Fyllingen–Brann 0-4
```

Fyllingen player:

```text
Kasper Birkeland
ID: 34c92573-c7a8-4b78-b515-5f4756adcc6c
shirt: 23
role: null
```

appears twice identically in the raw squad.

Importer behavior:
- identical duplicate squad rows may be ignored
- conflicting duplicate squad rows must raise an error rather than guessing

Implemented in `insert_squad()`.

---

# 10. Missing bench-list problem

Major database audit finding:

The raw Branntall `homeSquad` / `awaySquad` lists are sometimes incomplete, especially historically.

Initial SQLite v1 had:

```text
Brann appearances: 13,493
```

Audit independently reconstructed appearances from:

```text
starters UNION subOn events
```

Expected:

```text
13,586
```

Difference:

```text
93 missing Brann substitute appearances
```

Distribution:

```text
2000: 10
2001: 62
2002: 10
2004: 6
2005: 3
2024: 1
2025: 1
```

This is mostly an early historical data issue.

Modern examples:

### Ruben Kristiansen, 2024

Match:

```text
2024-06-01 HamKam–Brann 1-2
```

Event:
- 75' Ruben Kristiansen subOn
- later receives yellow card
- but missing from Branntall squad list

Therefore event clearly documents a real appearance.

### Eggert Aron Gudmundsson, 2025

Match:

```text
2025-06-30 Brann–Sandefjord 1-0
```

Event:
- 60' Eggert Aron Gudmundsson subOn for Mads Sande
- missing from squad list

Again, event is authoritative evidence of appearance.

---

# 11. Appearance model v2

Canonical meaning of an appearance row:

> A player has a row when the project has documented information about that player's match status.

It is **not** limited to players present in Branntall's squad array.

Current `appearances` model includes:

```text
match_id
team_id
player_id
shirt_number
squad_index
role_id
role_abbr
role_sort
starting
appeared
unused_substitute
listed_in_squad
entered_minute
exited_minute
```

Important semantics:

```text
listed_in_squad = 1
```

means player was explicitly present in Branntall's squad array.

```text
listed_in_squad = 0
```

means appearance/status was reconstructed from match events.

```text
squad_index
```

stores the zero-based position of the player in Branntall's original squad array when `listed_in_squad = 1`. Event-reconstructed rows have `squad_index = NULL`.

Starting supports:

```text
1    documented starter
0    documented non-starter
NULL unknown start status
```

After explicit corrections and event reconstruction, current Brann dataset has:

```text
0 Brann appearances with unknown start status
```

---

# 12. Explicit event corrections

Correction file:

```text
data/corrections.json
```

Raw files remain unchanged.

Current explicit corrections count:

```text
2
```

## 12.1 Bodø/Glimt–Brann 2005

Raw Branntall event incorrectly said:

```text
Tom Sanne IN
Knut Walde OUT
```

Official NFF data showed:

```text
Tom Sanne IN
Martin Knudsen OUT
```

The correction layer replaces the erroneous `subOff` player.

Do not add Knut Walde as an extra reconstructed appearance.

## 12.2 Fredrikstad–Brann 2011

Raw Branntall event said:

```text
Christian Kalvenes IN
Ukjent Ukjent OUT
```

Correct:

```text
Zsolt Korcsmár OUT
```

NFF data confirmed this.

Important:
- "Ukjent Ukjent" should never become a real player appearance.
- placeholder players should be ignored by appearance reconstruction.

## 12.3 Historical squad-entry exclusions

The same correction file now also contains:

```text
squad_entry_exclusions
```

These are not attempts to identify missing historical players. They are explicit import rules for raw squad rows where Branntall lists the same player more than once in the same team squad for the same match.

Current count:

```text
9
```

Behavior:
- raw JSON remains unchanged
- the later duplicate squad entry is excluded from derived `appearances`
- the exclusion is recorded in SQLite table `data_squad_corrections`
- each configured exclusion must apply exactly once
- if excluding a duplicate leaves Brann with fewer than 11 starters, that remains an audit finding rather than being guessed away

Pre-2000 duplicate squad entries currently covered:

```text
1914-09-13 Stavanger-Brann: Birger Lunde, Stavanger
1937-06-21 Brann-Arstad: Leif Magnus Eriksen, Brann
1952-05-18 Valerenga-Brann: Asbjorn Andersen, Valerenga
1963-08-18 Brann-Skeid: Bjorn Elvenes, Skeid
1970-08-30 Brann-Lyn: Svein Bjorn Olsen, Lyn
1973-10-24 Brann-Glentoran: Warren Feeney, Glentoran
1979-09-09 Start-Brann: Ingvald Huseklepp, Brann
1997-09-21 Brann-Sogndal: Ole Hjelmhaug, Sogndal
1998-07-05 Sogndal-Brann: Ole Hjelmhaug, Sogndal
```

---

# 13. Correction provenance

SQLite v2 includes:

```text
data_corrections
data_squad_corrections
```

`data_corrections` records event corrections:
- correction ID
- match
- source filename
- event index
- minute
- event type
- changed field
- original player ID/name
- replacement player ID/name
- source label
- source reference
- reason

`data_squad_corrections` records squad-entry exclusions:
- correction ID
- match
- source filename
- squad name
- team
- player
- squad index
- action
- source label/reference
- reason

Each configured correction or squad-entry exclusion must apply:

```text
exactly once
```

If a correction applies zero or multiple times, database build must fail.

Reason:
- source data may change
- stale correction files must not silently stop working

---

# 14. SQLite database

Original database v1:

```text
data/brannspillet_v1.db
```

Current validated v2:

```text
data/brannspillet_v2.db
```

A copy may also exist as:

```text
data/brannspillet.db
```

depending on whether v2 has been promoted to canonical filename.

For current prototypes, code explicitly points at:

```text
data/brannspillet_v2.db
```

Do not assume `brannspillet.db` is current unless checked.

Main build script:

```text
build_db_v2.py
```

Current behavior:
- imports only raw files dated `2000-01-01` or later
- this protects the validated v2 database while pre-2000 raw issues are being inspected
- supports explicit date-range/output arguments for sandbox builds

Default canonical build:

```powershell
python build_db_v2.py
```

Historical sandbox build:

```powershell
python build_db_v2.py --historical-sandbox
```

Historical sandbox output:

```text
data/brannspillet_historical_sandbox.db
```

The default build must continue to protect canonical v2 by importing only the 2000-onward subset unless the project intentionally promotes historical data later.

Earlier script:
- `build_db.py`

---

# 15. SQLite schema

Core tables:

```text
players
teams
competitions
grounds
matches
appearances
events
data_corrections
data_squad_corrections
```

## players

Relevant fields:

```text
id
name
full_name
slug
birthdate
birthplace
country_code
```

Use stable Branntall `_id`; names are display fields.

## teams

Relevant fields:

```text
id
name
abbr
full_name
slug
country_code
```

## competitions

Relevant fields:

```text
id
name
abbr
slug
sort
level
official
count_as
parent_id
```

## grounds

Relevant fields:

```text
id
name
full_name
slug
country_code
latitude
longitude
```

## matches

Relevant fields:

```text
id
branntall_id
date
time
season_id
season_name
competition_id
round fields
leg
ground_id
home_team_id
away_team_id
score
home_score
away_score
aggregate_score
shootout_score
attendance
source_filename
```

## events

Relevant fields:

```text
match_id
event_index
minute
event_name
event_type
team_id
player_id
scorer_id
assist_id
sub_on_id
sub_off_id
```

`scorer_id` is normalized across `scoredBy` and `player`.

## data_squad_corrections

Relevant fields:

```text
correction_id
match_id
source_filename
squad_name
team_id
player_id
player_name
squad_index
action
source_label
source_reference
reason
```

This table records explicit squad-entry exclusions used when a raw squad contains duplicate rows for the same player in the same match/team.

---

# 16. Final v2 database statistics

Successful `build_db_v2.py` result for the 2000-onward v2 subset:

```text
matches                   965
players                  5167
teams                     125
competitions               14
grounds                   129
appearances             34406
events                  12962
data_corrections            2
data_squad_corrections      0
```

Brann controls:

```text
Brann-startere totalt:       10615
Brann-opptredener totalt:    13586
Rekonstruert fra events:        93
Brann-startstatus ukjent:        0
Anvendte korreksjoner:           2
Anvendte troppskorreksjoner:     0
```

V1 appearances:

```text
34239
```

V2 appearances:

```text
34406
```

Difference:

```text
167
```

Of those:
- 93 are reconstructed Brann appearances
- about 74 are equivalent reconstructed opponent appearances

---

# 16B. Historical sandbox database statistics

Historical sandbox database:

```text
data/brannspillet_historical_sandbox.db
```

Successful historical sandbox build:

```powershell
python build_db_v2.py --historical-sandbox
```

Result:

```text
matches                  1589
players                  5161
teams                     161
competitions               16
grounds                   117
appearances             33661
events                   9510
data_corrections            0
data_squad_corrections      9
```

Period:

```text
1911-06-21 through 1999-10-30
```

Brann controls:

```text
Brann starters:               16635
Brann substitute appearances:  1648
Brann total appearances:      18284
Reconstructed Brann apps:        47
Unknown Brann start status:       1
```

Brann starter count distribution per match:

```text
 0:   24
 1:    4
 2:    7
 3:    3
 4:   12
 5:   11
 6:   16
 7:   24
 8:   21
 9:   24
10:   23
11: 1414
12:    5
13:    1
```

This means the historical sandbox currently has:

```text
1,414 Hvem mangler-eligible pre-2000 matches
```

where "eligible" only means exactly 11 Brann starters in the current derived data. It does not imply all shirt numbers, events or opponent data are complete.

Historical import audit:

```powershell
python audit_historical_import.py
```

Report:

```text
data/historical_import_audit.csv
```

Current audit findings:

```text
298 total findings
175 BRANN_STARTERS_NOT_11
 76 GOAL_MISSING_SCORER
 40 SUB_MISSING_SUB_OFF
  6 SUB_MISSING_SUB_ON
  1 BRANN_UNKNOWN_START_STATUS
```

---

# 17. Final v2 audit

Audit script:

```text
audit_db_v2.py
```

Final result:

```text
OK SQLite integrity_check
OK Foreign keys
OK Alle kamper involverer Brann
OK 11 Brann-startere i alle kamper
OK Brann-opptredener stemmer med startere + innbyttere
OK Alle Brann-innbyttere finnes i kamptroppen
OK Alle utbyttede Brann-spillere finnes i kamptroppen
OK Alle ordinære Brann-mål har målscorer
OK Alle Brann-bytter har innbytter
OK Alle reelle events har normalisert lag
```

Exact appearance audit:

```text
Forventet 13586
Database 13586
Mangler 0
Ekstra 0
```

Additional v2 controls:

```text
OK Eksplisitte datakorreksjoner
   2/2

OK Ingen v2-troppskorreksjoner
   0/0

OK Rekonstruerte Brann-opptredener
   93/93

OK Ingen Brann-spillere med ukjent startstatus
   0 avvik

OK Squad index finnes i appearances
   kolonne finnes

OK Alle troppsførte rader har squad_index
   0 mangler

OK Ingen dupliserte squad_index per kamp/lag
   0 avvik

OK Event-rekonstruerte rader har ikke squad_index
   0 avvik
```

These are regression targets.

---

# 18. Current player statistics from validated v2

Top appearances since 2000:

```text
Erik Huseklepp                       308
Håkon Opdal                          296
Erlend Hanstveit                     295
Fredrik Haugen                       276
Ruben Kristiansen                    255
Azar Karadas                         251
Kristoffer Barmen                    250
Bård Finne                           228
Ólafur Örn Bjarnason                 213
Sivert Heltne Nilsen                 198
Hassan El Fakiri                     196
Birkir Sævarsson                     193
Fredrik Pallesen Knudsen             185
Piotr Leciejewski                    184
Felix Horn Myhre                     181
```

Top goals since 2000:

```text
Bård Finne                            95
Thorstein Helstad                     86
Robbie Winters                        70
Erik Huseklepp                        68
Aune Heggebø                          51
Azar Karadas                          45
Niklas Castro                         44
Raymond Kvisvik                       39
Bengt Sæternes                        37
Kristoffer Barmen                     35
Petter Vaagan Moen                    35
Kim Ojo                               33
Felix Horn Myhre                      32
Petter Furuseth Olsen                 30
Daouda Bamba                          29
```

These are database-derived statistics for this project dataset beginning in 2000, not automatically official all-time Brann records.

---

# 19. `query.py`

Current player lookup prototype:

```text
query.py
```

Purpose:
- human-readable interface to inspect database
- useful for spot-checking

Example:

```powershell
python query.py
```

or:

```powershell
python query.py "Bård Finne"
```

Current Bård Finne profile:

```text
Kamper:             228
Starter:            133
Innhopp:             95
Ubrukt reserve:      29

Mål:                 95
Straffemål:           4
Assists:              35
Gule kort:             4
Røde kort:             2
```

First:

```text
10.05.2012 Florø–Brann 1-6 (Cupen)
```

Latest in current dataset:

```text
23.08.2026 Fyllingen–Brann 0-4 (Cupen)
```

Competition breakdown:

```text
Eliteserien          112
Cupen                 31
OBOS-ligaen           29
Tippeligaen           26
Conference League     14
Europa League         13
Champions League       2
Kvalifisering          1
```

Year breakdown intentionally uses calendar year instead of `season_name` because UEFA season labels and domestic Norwegian seasons differ.

Current Bård Finne year breakdown:

```text
2012        9
2013       22
2021       17
2022       33
2023       42
2024       37
2025       41
2026       27
```

Totals = 228.

---

# 20. Assists caveat

Current `query.py` assists count uses:

```text
events.assist_id
```

on goal / penalty-goal events.

Branntall also contains separate:

```text
event_type = assist
```

events.

Before building gameplay around assists, audit whether separate assist events:
- duplicate `assistedBy`
- add extra information
- vary by era

Do not assume current assist count logic is the final canonical assist model without auditing.

---

# 21. Shirt-number problem

Audit script:

```text
audit_shirt_numbers.py
```

Initial findings:

```text
Brann starter appearances with missing shirt number: 298
```

Distribution:

```text
2000: 11
2001: 5
2002: 34
2003: 5
2004: 35
2005: 12
2006: 3
2007: 16
2008: 14
2009: 29
2010: 11
2012: 26
2013: 21
2014: 5
2015: 28
2016: 7
2017: 6
2018: 22
2019: 2
2020: 3
2021: 3
```

Conservative automatic inference:

> If the player has exactly one distinct known shirt number elsewhere in the same `season_name`, use it.

This resolves:

```text
173 of 298
```

Remaining unresolved after same-season inference:

```text
125
```

These 125 rows group into only 26 player/year cases.

---

# 22. Verified shirt-number enrichment

File:

```text
data/shirt_number_enrichments.json
```

Purpose:
- fill missing data
- not correct wrong raw data

Precedence:

```text
raw exact match number
→ verified enrichment
→ unambiguous same-season inference
→ ?
```

Do not reverse this precedence.

Current research produced:

```text
25 confirmed rules
1 unresolved case
```

Confirmed examples:

```text
Hassan El Fakiri 2000       #20
Kjetil Norland 2000         #20
Raymond Kvisvik 2002        #27
Thorstein Helstad 2002      #22
Runar Normann 2003          #26
Toni Nhleko 2003            #18
Ivar Rønningen 2004         #24
Raymond Kvisvik 2005        #27
Ardian Gashi 2007           #7
Eirik Bakke 2008            #17
Bjørn Dahl 2009             #3
Cato Hansen 2009            #19
Ármann Björnsson 2009       #28
Bjarte Haugsdal 2010        #16
Tijan Jaiteh 2010           #14
Hannes Halldórsson 2012     #33
Lars Grorud 2012            #4
Rodolph Austin 2012         #5
Fredrik Nordkvelle 2013     #14
Vasili Pavlov 2013          #11
Kristoffer Larsen 2014      #19
Emil Hansson 2015           #16
Halldor Stenevik 2017       #20
Steffen Lie Skålevik 2017   #11
Kristoffer Løkberg 2019     #23
```

The enrichment file includes:
- `player_name`
- `from_date`
- `to_date`
- `shirt_number`
- `confidence`
- `method`
- source metadata
- explanatory note

Do not discard provenance fields.

---

# 23. One deliberately unresolved shirt number

Current unresolved case:

```text
Andreas Vindheim
Bjarg–Brann
2012-05-01
```

He made his Brann A-team debut in this match.

A reliable exact shirt number was not found.

There was evidence he wore #2 for Brann 2 shortly before, but Birkir Sævarsson, the first-team #2, was also in the A-team squad.

Therefore:

> Do not infer #2.

Expected output:

```text
?
```

until stronger evidence is found.

This illustrates the philosophy:

> Unknown is better than plausible-but-unverified.

---

# 24. `hvem_mangler.py`

Current active game prototype:

```text
hvem_mangler.py
```

Current modern database path:

```text
data/brannspillet_v2.db
```

Current historical sandbox database path:

```text
data/brannspillet_historical_sandbox.db
```

Current enrichment path:

```text
data/shirt_number_enrichments.json
```

## Current mechanic

Streak mode.

The player chooses a year interval before the game starts:

```text
1963 through 2026
```

The terminal prototype asks for start year and end year. A future web frontend can represent the same selection as a two-handle range slider.

The game then samples random eligible lineups from the entire selected interval.

Eligibility:
- the match must involve Brann
- the derived database must contain exactly 11 Brann starters
- historical pre-2000 matches are read from the historical sandbox database
- incomplete historical lineups are excluded from Hvem mangler candidates

One Brann starter hidden from each lineup.

The hidden starter's slot remains visible in the lineup as:

```text
  --  --- MANGLER ---
```

This preserves the natural tactical position clue, e.g. showing that the missing player was between two defenders or in midfield, without revealing the player.

Hidden-player rule:
- the hidden player is partly random
- for the selected lineup, rank the 11 starters by Brann appearances in that specific calendar year
- build a hidden-player pool from the five starters with the fewest appearances
- randomly hide one player from that five-player pool
- this rule is not shown to the player

Scoring:
- the player starts with three lives
- each wrong answer costs one life and reveals the correct answer
- the third wrong answer ends the game
- each correct answer adds 1 to the streak
- quitting with `q` reports the current streak

## Seeds and CLI

Normal:

```powershell
python hvem_mangler.py
```

This starts a random streak game and prompts for year interval.

Random:

```powershell
python hvem_mangler.py --random
```

`--random` is retained for compatibility; random is now the default.

Specific date:

```powershell
python hvem_mangler.py --date 2026-08-26
```

This uses a deterministic seed for testing/replay.

Non-interactive interval:

```powershell
python hvem_mangler.py --start-year 1963 --end-year 1999
```

Current eligible candidate counts:

```text
1963-1999: 1010
2000-2026:  965
1963-2026: 1975
```

## Static GitHub Pages beta

Current static beta path:

```text
docs/hvem-mangler/
```

The static beta is a plain HTML/CSS/JavaScript version of Hvem mangler that can be served by GitHub Pages from the repository's `docs/` folder.

Generated puzzle data:

```text
docs/hvem-mangler/puzzles.json
```

Regenerate it with:

```powershell
python export_hvem_mangler_pages_data.py
```

Current exported puzzle count:
- 1,975 total eligible puzzles
- 1,010 historical pre-2000 puzzles
- 965 modern 2000-onward puzzles

The JSON export preserves:
- exactly 11 Brann starters per puzzle
- original squad insertion order
- visible hidden-player placeholder
- five-player hidden-candidate pool based on fewest Brann appearances in that calendar year
- shirt-number priority from the terminal prototype

Static beta autocomplete:
- suggestions are based on players who appear in the selected year range
- visible starters in the current lineup are excluded from suggestions
- this is a first native-browser `datalist` implementation for beta testing

Static beta limitation:
- answers are included client-side in the downloaded JSON
- this version is for informal beta testing, not anti-cheat production use

## Answer handling

Accept:
- full registered name
- unique partial player name among the XI
- accent-insensitive normalized matching

Examples intended to work:

```text
finne
huseklepp
pallesen
horn myhre
```

if unique among the XI.

---

# 25. Natural lineup ordering

Initial implementation sorted within positional groups by:

```text
role_sort
shirt_number
name
```

This produced unnatural defensive ordering.

Example bad ordering:

```text
6 Japhet Sery Larsen
20 Vetle Dragsnes
21 Denzel De Roeve
26 Eivind Helland
```

Expected natural order:

```text
21 Denzel De Roeve
6 Japhet Sery Larsen
26 Eivind Helland
20 Vetle Dragsnes
```

Testing showed that preserving original Branntall squad insertion order gives natural lineup order.

Current prototype query uses the explicit derived squad position:

```sql
ORDER BY
    a.squad_index IS NULL,
    a.squad_index,
    p.name
```

The database stores:

```text
squad_index
```

from the original raw squad list. This replaced the earlier temporary reliance on SQLite `rowid`.

---

# 26. Position grouping in Hvem mangler

Current categories:

```text
KEEPER
FORSVAR
MIDTBANE
ANGREP
ØVRIGE
```

Mapping:

```text
gk  -> KEEPER
def -> FORSVAR

d-m
mid
m-a -> MIDTBANE

att -> ANGREP
```

Within each category, preserve original squad order.

Do not sort by shirt number.

---

# 27. Shirt-number display in Hvem mangler

Current intended precedence:

## 1. Exact match number

Use:

```text
appearances.shirt_number
```

if non-null.

## 2. Verified enrichment

Search `shirt_number_enrichments.json` by:
- normalized player name
- match date in `from_date` / `to_date`

Only use if exactly one enrichment number matches.

## 3. Conservative same-season inference

Find all distinct non-null shirt numbers for player in same `season_name`.

Only use if:

```text
exactly one unique number
```

## 4. Unknown

Display:

```text
?
```

Do **not** display a `*` or other visual marker for enriched/inferred numbers.

The user explicitly rejected inference markers as unnecessary UI noise.

Provenance stays in the data layer.

---

# 28. Known Hvem mangler regression examples

Rodolph Austin:

```text
2012-07-15 Brann–Odd 6-2
```

Raw squad number missing.

Expected after enrichment:

```text
5 Rodolph Austin
```

Hassan El Fakiri:

```text
2000-04-16 Rosenborg–Brann 4-4
```

Expected:

```text
20 Hassan El Fakiri
```

Useful regression tests.

---

# 29. Current project files

Expected project root approximately:

```text
Brannspillet/
│
├── crawler.py
├── crawler_backwards.py
├── analyze.py
├── validate.py
├── inspect_warnings.py
├── inspect_remaining_warnings.py
├── inspect_db_failure.py
├── inspect_duplicate_squad.py
├── inspect_appearance_gaps.py
├── inspect_appearance_edge_cases.py
├── audit_shirt_numbers.py
│
├── build_db.py
├── build_db_v2.py
│
├── audit_db.py
├── audit_db_v2.py
├── audit_historical_import.py
│
├── query.py
├── hvem_mangler.py
├── tenable.py
│
├── AGENTS.md
├── PROJECT_CONTEXT.md
│
└── data/
    ├── raw/
    │   └── 2,554 JSON files
    │
    ├── matches.csv
    ├── matches_backfill_pre2000.csv
    ├── full_validation.csv
    ├── validation_backfill_pre2000.csv
    ├── historical_import_audit.csv
    │
    ├── corrections.json
    ├── shirt_number_enrichments.json
    │
    ├── brannspillet_v1.db
    ├── brannspillet_v2.db
    ├── brannspillet_historical_sandbox.db
    └── possibly brannspillet.db
```

Some inspection scripts may no longer be operationally necessary but are useful historical/debugging tools.

---

# 30. Data architecture principles

These are intentional. Preserve them.

## 30.1 Raw data is immutable

Never edit:

```text
data/raw/*.json
```

## 30.2 Stable external IDs

Use Branntall `_id` whenever available.

Names are display fields, not stable identities.

## 30.3 Derived facts should be derived

Do not store aggregate player totals as canonical facts if they can be queried from normalized match/appearance/event rows.

## 30.4 Corrections need provenance

Known wrong source data belongs in:

```text
corrections.json
```

and should retain:
- what changed
- original value
- replacement value
- external source
- reason

## 30.5 Enrichment is distinct from correction

Missing shirt number:

```text
enrichment
```

Wrong `subOff`:

```text
correction
```

Do not merge these concepts blindly.

## 30.6 Unknown beats guessed

If reliable evidence is unavailable:

```text
NULL
?
```

is correct.

Do not create plausible facts from unrelated seasons or player history.

## 30.7 Database is rebuildable

SQLite is a derived artifact.

Canonical pipeline:

```text
raw Branntall JSON
+ explicit corrections
+ verified enrichment
+ deterministic normalization
→ SQLite
```

The database must be reproducible.

---

# 31. Database safety principles

Do not:
- disable foreign keys to avoid import failures
- silently ignore conflicting duplicate rows
- silently discard events that do not fit assumptions
- patch raw source JSON
- hardcode one-off source IDs when a general resolver is possible

When an integrity error occurs:
1. inspect exact raw event / squad data
2. understand source inconsistency
3. implement a general solution when possible
4. explicitly document unavoidable one-off corrections

---

# 32. Source / rights note

Branntall is an external database.

Current project uses a polite local research crawl:
- one request per match
- approximately one-second delay
- identifiable user agent
- no aggressive parallel scraping

Before public / production-scale systematic reuse, it would be prudent to contact Branntall's maintainers for permission, export or read-only access.

Do not overstate legal conclusions.

Preferred production approach:
- permission
- export
- API/read-only access
- or another agreed ingestion method

rather than indefinitely relying on page scraping.

---

# 33. Historical competition naming

Branntall normalizes some competition names.

Example:
- 2000 UEFA Cup matches may appear as `"Europa League"`

Therefore raw `competition.name` may not always equal historically contemporary branding.

Future UI may need:

```text
canonical competition
historical display name
competition family
```

Examples:

```text
Tippeligaen + Eliteserien
→ top-flight family

Europa League + Conference League + Champions League
→ Europe family
```

Do not overwrite raw competition names merely for presentation.

Use a mapping layer.

---

# 34. Future player enrichment

Branntall's match role is broad and match-specific.

Observed abbreviations include:

```text
gk
def
d-m
mid
m-a
att
res
```

Enough for broad lineup grouping, not enough for detailed identity such as:
- right back
- left back
- centre back
- winger
- striker
- attacking midfielder

Future `Rødtrøyen` and grid games may need external enrichment.

Any external enrichment should retain provenance.

---

# 35. Future player aliases

A future table/file should support accepted answer aliases.

Potential examples:
- accentless forms
- surname only
- common abbreviated names
- alternate transliterations

Possible future schema:

```text
player_aliases
```

Do not overload canonical player names for answer matching.

---

# 36. Suggested next development steps

## 36.1 Stabilize `Hvem mangler?`

Next useful improvements:
- audit all shirt-number enrichment usage
- test that only Andreas Vindheim remains `?` among previously unresolved starter shirt numbers
- add a validation script for generated Hvem mangler rounds
- improve difficulty model

## 36.2 Better difficulty model

Current game sampling is random within the chosen year interval.

Potential signals:
- total Brann appearances
- number of starts
- years since match
- competition importance
- opponent prominence
- hidden-player obscurity
- lineup obscurity

Possible conceptual score:

```text
difficulty =
  age_of_match
+ low_player_appearances
+ low_player_starts
+ obscure_competition
+ obscure_opponent
```

For streak mode, difficulty should eventually help balance candidate selection without making the hidden-player rule visible to the player.

## 36.3 Build web frontend only after game logic is stable

Do not rush into framework work until:
- puzzle generation
- answer validation
- deterministic daily seeds
- database rules

are stable.

SQLite is intentionally the current development database.

## 36.4 Implement Tenable

Generate top-10 facts from database and validate exact answer set.

## 36.5 Implement Rødtrøyen

Requires richer player attributes, aliases, positions and career/debut stats.

---

# 37. Recommended immediate Codex workflow

First Codex prompt:

```text
Read AGENTS.md and PROJECT_CONTEXT.md, then inspect the repository without modifying anything.

Verify that:
- the database paths and schemas match the documentation,
- build_db_v2.py contains the documented normalization/correction behavior,
- audit_db_v2.py matches the documented regression checks,
- hvem_mangler.py uses natural squad order and the intended shirt-number precedence.

Then summarize any differences between the actual repository and PROJECT_CONTEXT.md before making changes.
```

Do not let a new agent immediately refactor based only on this document.

First compare documentation against actual files.

---

# 38. User working preferences relevant to development

The user:
- is comfortable running Python commands in PowerShell
- is not deeply experienced with Python/database architecture
- prefers explicit steps and complete replacement files when changes are substantial
- wants source-grounded factual handling
- values clear distinction between documented facts, inference and uncertainty
- does not want invented or silently normalized historical facts

When explaining a change:
- name exact file
- describe what the change does
- give command to run
- state expected output / regression values when known

Avoid asking user to manually debug complex code if Codex can inspect and fix it directly.

---

# 39. Current golden regression values

Treat these as important until dataset is intentionally updated.

Current full raw archive after pre-2000 backfill:

```text
Raw matches:                   2554
Unique match IDs:              2554
Raw events:                   22472
Raw validation errors:            2
Raw validation warnings:        286
```

Current validated v2 database subset, 2000 onward:

```text
Raw matches:                    965
Unique match IDs:               965
Raw events:                   12962

Brann starters:               10615
Brann substitute appearances:  2971
Brann total appearances:      13586

Reconstructed Brann apps:        93
Explicit event corrections:       2
Explicit squad corrections:       0
Unknown Brann start status:       0
```

Database v2:

```text
matches                   965
players                  5167
teams                     125
competitions               14
grounds                   129
appearances             34406
events                  12962
data_corrections            2
data_squad_corrections      0
```

Current historical sandbox database, pre-2000:

```text
Historical matches:             1589
Historical date range:          1911-06-21..1999-10-30
Brann starters:                16635
Brann substitute appearances:   1648
Brann total appearances:       18284
Reconstructed Brann apps:         47
Explicit squad corrections:        9
Unknown Brann start status:        1
Hvem mangler-eligible matches:  1414

Historical audit findings:       298
BRANN_STARTERS_NOT_11:           175
GOAL_MISSING_SCORER:              76
SUB_MISSING_SUB_OFF:              40
SUB_MISSING_SUB_ON:                6
BRANN_UNKNOWN_START_STATUS:        1
```

If these change without:
- new raw matches
- intentional correction
- documented schema/logic improvement

then investigate.

---

# 40. Current canonical philosophy

The most important summary for future development:

> Brannspillet is not a pile of quiz questions. It is a reproducible football knowledge base from which games are generated.

Quality hierarchy:

```text
correctness
> provenance
> reproducibility
> automation
> presentation convenience
```

A polished game built on guessed historical data is worse than a game that displays `?`.

Preserve that principle as the project grows.
