import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

import export_player_index
import tenable


FACTS_OUTPUT_FILE = Path("docs/shared/player-facts.json")
CRITERIA_OUTPUT_FILE = Path("docs/shared/grid-criteria-index.json")
MODERN_FACTS_OUTPUT_FILE = Path(
    "docs/shared/player-facts-modern.json"
)
MODERN_CRITERIA_OUTPUT_FILE = Path(
    "docs/shared/grid-criteria-index-modern.json"
)
GRID_RANGE_OUTPUT_DIR = Path("docs/shared/grid-ranges")
GRID_RANGE_START_YEARS = range(1990, 2011)
COACHES_FILE = Path("data/tenable/coaches.yaml")
HONORS_FILE = Path("data/brann_honors.yaml")
MANUAL_GRID_CRITERIA_FILE = Path("data/grid_manual_criteria.yaml")
GROUND_CORRECTIONS_FILE = Path("data/ground_corrections.json")
SHIRT_NUMBER_CORRECTIONS_FILE = Path(
    "data/shirt_number_corrections.json"
)
SCHEMA_VERSION = 1
LEAGUE_LEVEL_START_YEAR = 1961
SECOND_LEVEL_LEAGUE_SEASONS = {
    1965,
    1966,
    1967,
    1980,
    1982,
    1984,
    1986,
    2015,
    2022,
}
INCLUDED_SHIRT_NUMBER_CRITERIA = {
    7,
    8,
    9,
    10,
}
LEAGUE_COMPETITION_GROUPS = {
    "league_all": {
        "id": "league_all",
        "name": "Seriekamper",
        "playedLabel": "Spilt seriekamp for Brann",
        "goalLabel": "Scoret i seriekamp for Brann",
        "redCardLabel": "Fått rødt kort i seriekamp for Brann",
    },
    "league_top_level": {
        "id": "league_top_level",
        "name": "Øverste nivå",
        "playedLabel": "Spilt på øverste nivå for Brann",
        "goalLabel": "Scoret på øverste nivå for Brann",
        "redCardLabel": "Fått rødt kort på øverste nivå for Brann",
    },
    "league_second_level": {
        "id": "league_second_level",
        "name": "Nest øverste nivå",
        "playedLabel": "Spilt på nest øverste nivå for Brann",
        "goalLabel": "Scoret på nest øverste nivå for Brann",
        "redCardLabel": "Fått rødt kort på nest øverste nivå for Brann",
    },
}
WHITELISTED_GROUND_CRITERIA = [
    {
        "id": "goodison_park",
        "label": "Har spilt på Goodison Park",
        "ground_name": "Goodison Park",
        "set_name": "groundsPlayed",
        "category": "grounds",
    },
    {
        "id": "lerkendal_goal",
        "label": "Har scoret på Lerkendal",
        "ground_name": "Lerkendal",
        "set_name": "scoredAgainstGrounds",
        "category": "grounds",
    },
]
COUNTRY_LABELS = {
    "AL": "Albania",
    "AR": "Argentina",
    "AT": "Østerrike",
    "AU": "Australia",
    "BA": "Bosnia-Hercegovina",
    "BE": "Belgia",
    "BR": "Brasil",
    "BY": "Belarus",
    "CA": "Canada",
    "CH": "Sveits",
    "CI": "Elfenbenskysten",
    "CL": "Chile",
    "CM": "Kamerun",
    "CR": "Costa Rica",
    "CY": "Kypros",
    "DE": "Tyskland",
    "DK": "Danmark",
    "DZ": "Algerie",
    "EE": "Estland",
    "ES": "Spania",
    "FI": "Finland",
    "FO": "Færøyene",
    "FR": "Frankrike",
    "GB": "Storbritannia",
    "GB-ENG": "England",
    "GB-NIR": "Nord-Irland",
    "GB-SCT": "Skottland",
    "GB-WLS": "Wales",
    "GH": "Ghana",
    "GM": "Gambia",
    "GR": "Hellas",
    "HN": "Honduras",
    "HR": "Kroatia",
    "HU": "Ungarn",
    "IE": "Irland",
    "IS": "Island",
    "IT": "Italia",
    "JM": "Jamaica",
    "JP": "Japan",
    "KM": "Komorene",
    "KZ": "Kasakhstan",
    "LR": "Liberia",
    "LT": "Litauen",
    "LU": "Luxembourg",
    "LV": "Latvia",
    "MA": "Marokko",
    "MK": "Nord-Makedonia",
    "MT": "Malta",
    "MX": "Mexico",
    "NG": "Nigeria",
    "NL": "Nederland",
    "NO": "Norge",
    "NZ": "New Zealand",
    "PL": "Polen",
    "PT": "Portugal",
    "RO": "Romania",
    "RS": "Serbia",
    "RU": "Russland",
    "SE": "Sverige",
    "SI": "Slovenia",
    "SK": "Slovakia",
    "SN": "Senegal",
    "TR": "Tyrkia",
    "US": "USA",
    "UY": "Uruguay",
    "ZA": "Sør-Afrika",
}


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(
        encoding="utf-8",
        errors="replace"
    )


try:
    import yaml

except ImportError:
    yaml = None


COUNTRY_TO_CONTINENT = {
    "AL": "Europe",
    "AR": "South America",
    "AT": "Europe",
    "AU": "Oceania",
    "BA": "Europe",
    "BE": "Europe",
    "BR": "South America",
    "BY": "Europe",
    "CA": "North America",
    "CH": "Europe",
    "CI": "Africa",
    "CL": "South America",
    "CM": "Africa",
    "CR": "North America",
    "CY": "Europe",
    "DE": "Europe",
    "DK": "Europe",
    "DZ": "Africa",
    "EE": "Europe",
    "ES": "Europe",
    "FI": "Europe",
    "FO": "Europe",
    "FR": "Europe",
    "GB": "Europe",
    "GB-ENG": "Europe",
    "GB-NIR": "Europe",
    "GB-SCT": "Europe",
    "GB-WLS": "Europe",
    "GH": "Africa",
    "GM": "Africa",
    "GR": "Europe",
    "HN": "North America",
    "HR": "Europe",
    "HU": "Europe",
    "IE": "Europe",
    "IS": "Europe",
    "IT": "Europe",
    "JM": "North America",
    "JP": "Asia",
    "KM": "Africa",
    "KZ": "Asia",
    "LR": "Africa",
    "LT": "Europe",
    "LU": "Europe",
    "LV": "Europe",
    "MA": "Africa",
    "MK": "Europe",
    "MT": "Europe",
    "MX": "North America",
    "NG": "Africa",
    "NL": "Europe",
    "NO": "Europe",
    "NZ": "Oceania",
    "PL": "Europe",
    "PT": "Europe",
    "RO": "Europe",
    "RS": "Europe",
    "RU": "Europe",
    "SE": "Europe",
    "SI": "Europe",
    "SK": "Europe",
    "SN": "Africa",
    "TR": "Europe",
    "US": "North America",
    "UY": "South America",
    "ZA": "Africa",
}


ROLE_LABELS = {
    "gk": "Målvakt",
    "def": "Forsvar",
    "d-m": "Forsvar/midtbane",
    "mid": "Midtbane",
    "m-a": "Midtbane/angrep",
    "att": "Angrep",
    "res": "Reserve",
}
INCLUDED_ROLE_CRITERIA = {
    "gk",
}


def load_json_file(path):

    if not path.exists():
        return {}

    with path.open(
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


def load_yaml_file(path):

    if not path.exists():
        return {}

    if yaml is None:
        raise SystemExit(
            "PyYAML mangler. Kjor: python -m pip install -r requirements.txt"
        )

    with path.open(
        "r",
        encoding="utf-8"
    ) as file:
        return yaml.safe_load(file) or {}


def listify(values):

    return sorted(
        values
    )


def make_counter():

    return defaultdict(int)


def make_nested_counter():

    return defaultdict(make_counter)


def sort_player_ids(player_ids, player_sort_key):

    return sorted(
        set(player_ids),
        key=lambda player_id: player_sort_key.get(
            player_id,
            player_id
        )
    )


def normalize_id_part(value):

    return (
        str(value)
        .casefold()
        .replace(" ", "-")
        .replace("/", "-")
        .replace(":", "-")
    )


def decade_label(year):

    return f"{year // 10 * 10}s"


def first_initial(name):

    parts = (name or "").strip().split()

    if not parts:
        return None

    return export_player_index.ascii_fold(
        parts[0][0]
    ).upper()


def last_initial(name):

    parts = (name or "").strip().split()

    if not parts:
        return None

    return export_player_index.ascii_fold(
        parts[-1][0]
    ).upper()


def load_ground_corrections():

    data = load_json_file(
        GROUND_CORRECTIONS_FILE
    )
    corrections = {}
    entities = {}

    for correction in data.get("corrections", []):

        corrections[
            correction["source_filename"]
        ] = correction
        entities[
            correction["corrected_ground_id"]
        ] = {
            "id": correction["corrected_ground_id"],
            "name": correction["corrected_ground_name"],
            "countryCode": None,
            "source": "explicit_correction",
        }

    return corrections, entities


def load_shirt_number_corrections():

    data = load_json_file(
        SHIRT_NUMBER_CORRECTIONS_FILE
    )
    corrections = {}

    for correction in data.get("corrections", []):

        key = (
            correction["source_filename"],
            correction["match_date"],
            correction["team_id"],
            correction["player_id"],
            correction["raw_shirt_number"],
        )

        corrections[key] = correction["corrected_shirt_number"]

    return corrections


def corrected_shirt_number(row, corrections):

    key = (
        row["source_filename"],
        row["match_date"],
        row["team_id"],
        row["player_id"],
        row["shirt_number"],
    )

    return corrections.get(
        key,
        row["shirt_number"]
    )


def load_coaches():

    data = load_yaml_file(
        COACHES_FILE
    )

    coaches = data.get(
        "coaches",
        []
    )

    if not isinstance(coaches, list):
        raise ValueError(
            f"{COACHES_FILE} coaches must be a list."
        )

    return coaches


def load_honors():

    data = load_yaml_file(
        HONORS_FILE
    )

    for key in (
        "league_titles",
        "league_silver_medals",
        "league_bronze_medals",
        "league_relegations",
        "league_promotions",
        "cup_titles",
        "lost_cup_finals",
    ):

        values = data.get(
            key,
            []
        )

        if not isinstance(values, list):
            raise ValueError(
                f"{HONORS_FILE} {key} must be a list."
            )

        data[key] = values

    return data


def load_manual_grid_criteria():

    data = load_yaml_file(
        MANUAL_GRID_CRITERIA_FILE
    )
    criteria = data.get(
        "criteria",
        []
    )

    if not isinstance(criteria, list):
        raise ValueError(
            f"{MANUAL_GRID_CRITERIA_FILE} criteria must be a list."
        )

    for criterion in criteria:

        if not criterion.get("id") or not criterion.get("label"):
            raise ValueError(
                f"{MANUAL_GRID_CRITERIA_FILE} criterion needs id and label."
            )

        players = criterion.get(
            "players",
            []
        )

        if not isinstance(players, list) or not players:
            raise ValueError(
                f"{MANUAL_GRID_CRITERIA_FILE} {criterion['id']} needs players."
            )

    return criteria


def load_player_index():

    data = export_player_index.build_index()
    players = {}

    for player in data["players"]:

        players[player["id"]] = {
            "id": player["id"],
            "name": player["name"],
            "fullName": player["fullName"],
            "aliases": player["aliases"],
            "searchText": player["searchText"],
            "birthdate": player["birthdate"],
            "countryCode": player["countryCode"],
            "firstBrannMatchDate": None,
            "lastBrannMatchDate": None,
            "firstBrannYear": None,
            "lastBrannYear": None,
            "brannYears": [],
            "stats": {
                "appearances": 0,
                "starts": 0,
                "substituteAppearances": 0,
                "goals": 0,
                "penaltyGoals": 0,
                "lateGoalsAfter90": 0,
                "multiGoalMatches": 0,
                "hatTrickMatches": 0,
                "yellowCards": 0,
                "redCards": 0,
            },
            "sets": defaultdict(set),
            "sources": player["sources"],
        }

    return players


def apply_manual_grid_criteria(players, criteria):

    for criterion in criteria:

        for player_ref in criterion.get(
            "players",
            []
        ):

            player_id = player_ref.get(
                "id"
            )

            if player_id not in players:
                raise ValueError(
                    "Fant ikke spiller-ID "
                    f"{player_id} i manuelt grid-kriterium "
                    f"{criterion['id']}."
                )

            if players[player_id]["stats"]["appearances"] > 0:
                players[player_id]["sets"]["manualCriteria"].add(
                    criterion["id"]
                )


def match_in_year_range(match, start_year=None, end_year=None):

    year = int(
        match["date"][:4]
    )

    if start_year is not None and year < start_year:
        return False

    if end_year is not None and year > end_year:
        return False

    return True


def query_all_data(start_year=None, end_year=None):

    ground_corrections, corrected_ground_entities = (
        load_ground_corrections()
    )

    data = {
        "matches": {},
        "brann_appearances": [],
        "opponent_appearances_against_brann": [],
        "brann_events": [],
        "entities": {
            "teams": {},
            "competitions": {},
            "grounds": corrected_ground_entities,
        },
    }

    databases = tenable.connect_databases(
        tenable.MIN_YEAR,
        tenable.MAX_YEAR
    )

    try:

        for database in databases:

            conn = database["conn"]

            team_rows = conn.execute(
                """
                SELECT
                    id,
                    name,
                    full_name,
                    country_code
                FROM teams
                """
            ).fetchall()

            for row in team_rows:
                data["entities"]["teams"][row["id"]] = {
                    "id": row["id"],
                    "name": row["name"],
                    "fullName": row["full_name"],
                    "countryCode": row["country_code"],
                }

            competition_rows = conn.execute(
                """
                SELECT
                    id,
                    name,
                    count_as
                FROM competitions
                """
            ).fetchall()

            for row in competition_rows:
                data["entities"]["competitions"][row["id"]] = {
                    "id": row["id"],
                    "name": row["name"],
                    "countAs": row["count_as"],
                }

            ground_rows = conn.execute(
                """
                SELECT
                    id,
                    name,
                    full_name,
                    country_code
                FROM grounds
                """
            ).fetchall()

            for row in ground_rows:
                data["entities"]["grounds"][row["id"]] = {
                    "id": row["id"],
                    "name": row["name"],
                    "fullName": row["full_name"],
                    "countryCode": row["country_code"],
                    "source": "database",
                }

            match_rows = conn.execute(
                """
                SELECT
                    m.id,
                    m.date,
                    m.season_name,
                    m.source_filename,
                    m.home_team_id,
                    m.away_team_id,
                    m.home_score,
                    m.away_score,
                    m.shootout_score,
                    m.ground_id,
                    g.name AS ground_name,
                    g.country_code AS ground_country_code,
                    m.competition_id,
                    c.name AS competition_name,
                    c.count_as AS competition_count_as,
                    m.round_name,
                    m.round_abbr

                FROM matches m

                LEFT JOIN competitions c
                    ON c.id = m.competition_id

                LEFT JOIN grounds g
                    ON g.id = m.ground_id
                """
            ).fetchall()

            for row in match_rows:

                match = dict(row)
                correction = ground_corrections.get(
                    match["source_filename"]
                )

                if correction:
                    match["ground_id"] = correction[
                        "corrected_ground_id"
                    ]
                    match["ground_name"] = correction[
                        "corrected_ground_name"
                    ]
                    match["ground_country_code"] = (
                        data["entities"]["grounds"]
                        .get(match["ground_id"], {})
                        .get("countryCode")
                    )

                if match_in_year_range(
                    match,
                    start_year,
                    end_year
                ):
                    data["matches"][match["id"]] = match

            brann_rows = conn.execute(
                """
                SELECT
                    a.match_id,
                    a.team_id,
                    a.player_id,
                    a.shirt_number,
                    a.role_abbr,
                    a.starting,
                    m.date AS match_date,
                    m.source_filename

                FROM appearances a

                JOIN matches m
                    ON m.id = a.match_id

                WHERE
                    a.team_id = ?
                    AND a.appeared = 1
                """,
                (
                    tenable.BRANN_ID,
                )
            ).fetchall()

            data["brann_appearances"].extend(
                dict(row)
                for row in brann_rows
                if row["match_id"] in data["matches"]
            )

            opponent_rows = conn.execute(
                """
                SELECT
                    a.match_id,
                    a.team_id,
                    a.player_id

                FROM appearances a

                JOIN matches m
                    ON m.id = a.match_id

                WHERE
                    a.team_id != ?
                    AND a.appeared = 1
                    AND (
                        m.home_team_id = ?
                        OR m.away_team_id = ?
                    )
                """,
                (
                    tenable.BRANN_ID,
                    tenable.BRANN_ID,
                    tenable.BRANN_ID,
                )
            ).fetchall()

            data["opponent_appearances_against_brann"].extend(
                dict(row)
                for row in opponent_rows
                if row["match_id"] in data["matches"]
            )

            event_rows = conn.execute(
                """
                SELECT
                    e.match_id,
                    e.event_index,
                    e.minute,
                    e.event_type,
                    e.team_id,
                    e.player_id,
                    e.scorer_id,
                    COALESCE(e.scorer_id, e.player_id) AS subject_player_id

                FROM events e

                WHERE
                    e.team_id = ?
                    AND e.event_type IN (
                        'goal',
                        'penaltyGoal',
                        'yc',
                        'rc'
                    )
                """,
                (
                    tenable.BRANN_ID,
                )
            ).fetchall()

            data["brann_events"].extend(
                dict(row)
                for row in event_rows
                if row["match_id"] in data["matches"]
            )

    finally:

        tenable.close_databases(
            databases
        )

    return data


def opponent_id_for_match(match):

    if match["home_team_id"] == tenable.BRANN_ID:
        return match["away_team_id"]

    return match["home_team_id"]


def brann_won_match(match):

    home_score = match["home_score"]
    away_score = match["away_score"]

    if home_score is None or away_score is None:
        return None

    if home_score != away_score:

        if match["home_team_id"] == tenable.BRANN_ID:
            return home_score > away_score

        return away_score > home_score

    shootout_score = match["shootout_score"]

    if not shootout_score or "-" not in shootout_score:
        return None

    left, right = shootout_score.split(
        "-",
        1
    )

    try:
        home_shootout = int(left.strip())
        away_shootout = int(right.strip())
    except ValueError:
        return None

    if home_shootout == away_shootout:
        return None

    if match["home_team_id"] == tenable.BRANN_ID:
        return home_shootout > away_shootout

    return away_shootout > home_shootout


def is_cup_final(match):

    return (
        match["competition_count_as"] == "cup"
        and match["round_abbr"] == "F"
    )


def is_cup_semifinal(match):

    return (
        match["competition_count_as"] == "cup"
        and match["round_abbr"] == "SF"
    )


def is_euro_group_or_league_phase(match):

    return (
        match["competition_count_as"] == "euro"
        and match["round_abbr"] in ("GR", "Sp")
    )


def is_euro_qualifier(match):

    round_abbr = match["round_abbr"] or ""
    round_name = (
        match["round_name"] or ""
    ).casefold()

    return (
        match["competition_count_as"] == "euro"
        and (
            round_abbr.startswith("Q")
            or round_abbr == "PO"
            or "kval" in round_name
        )
    )


def season_start_year(match):

    season_name = str(
        match.get("season_name")
        or ""
    )

    if len(season_name) >= 4 and season_name[:4].isdigit():
        return int(season_name[:4])

    date = match.get("date") or ""

    if len(date) >= 4 and date[:4].isdigit():
        return int(date[:4])

    return None


def league_competition_group_ids(match):

    if match["competition_count_as"] != "serie":
        return []

    group_ids = [
        "league_all"
    ]
    start_year = season_start_year(
        match
    )

    if start_year is None or start_year < LEAGUE_LEVEL_START_YEAR:
        return group_ids

    if start_year in SECOND_LEVEL_LEAGUE_SEASONS:
        group_ids.append(
            "league_second_level"
        )
    else:
        group_ids.append(
            "league_top_level"
        )

    return group_ids


def latest_match(matches):

    return sorted(
        matches.values(),
        key=lambda match: (
            match["date"],
            match["source_filename"]
        ),
        reverse=True
    )[0]


def raw_coach_periods(coach):

    periods = coach.get(
        "periods"
    )

    if periods is None:
        periods = [
            {
                "id": "main",
                "from_match": coach["from_match"],
                "to_match": coach["to_match"],
            }
        ]

    if not isinstance(periods, list) or not periods:
        raise ValueError(
            f"{coach['name']} mangler trenerperioder."
        )

    return periods


def coach_match_bounds(coaches, matches, strict=True):

    by_filename = {
        match["source_filename"]: match
        for match in matches.values()
    }
    latest = latest_match(
        matches
    )
    result = []

    for coach in coaches:

        periods = []

        for period in raw_coach_periods(
            coach
        ):

            from_match = by_filename.get(
                period["from_match"]
            )
            to_match = (
                by_filename.get(
                    period["to_match"]
                )
                if period.get("to_match")
                else latest
            )

            if not from_match or not to_match:
                if not strict:
                    continue

                raise ValueError(
                    "Fant ikke trenergrensekamp for "
                    f"{coach['name']}."
                )

            if from_match["date"] > to_match["date"]:
                raise ValueError(
                    f"Trenerperioden for {coach['name']} starter "
                    "etter sluttkampen."
                )

            periods.append(
                {
                    "id": period.get("id", "main"),
                    "fromMatch": period["from_match"],
                    "toMatch": period.get("to_match"),
                    "fromDate": from_match["date"],
                    "toDate": to_match["date"],
                    "current": bool(
                        period.get("current")
                        or not period.get("to_match")
                    ),
                }
            )

        if not periods:
            continue

        result.append(
            {
                "id": coach["id"],
                "name": coach["name"],
                "periods": periods,
                "fromDate": min(
                    period["fromDate"]
                    for period in periods
                ),
                "toDate": max(
                    period["toDate"]
                    for period in periods
                ),
                "current": any(
                    period["current"]
                    for period in periods
                ),
                "tenableQuestions": bool(
                    coach.get(
                        "tenable_questions",
                        False
                    )
                ),
            }
        )

    return result


def coach_ids_for_date(coaches, match_date):

    return [
        coach["id"]
        for coach in coaches
        if any(
            period["fromDate"] <= match_date <= period["toDate"]
            for period in coach["periods"]
        )
    ]


def honor_matches(matches, honor, final_only=False):

    result = []

    for match in matches.values():

        if (
            match["season_name"]
            != str(honor["season_name"])
        ):
            continue

        if (
            match["competition_count_as"]
            != honor["competition_count_as"]
        ):
            continue

        if (
            final_only
            and match["round_abbr"]
            != honor.get("round_abbr", "F")
        ):
            continue

        result.append(match)

    return sorted(
        result,
        key=lambda match: (
            match["date"],
            match["source_filename"]
        )
    )


def count_appearances_by_player(appearances, match_ids):

    counts = defaultdict(int)

    for appearance in appearances:

        if appearance["match_id"] in match_ids:
            counts[appearance["player_id"]] += 1

    return counts


def add_honor_to_player(player, honor_type, honor):

    set_name_by_type = {
        "league_title": "leagueTitleHonors",
        "league_silver": "leagueSilverHonors",
        "league_bronze": "leagueBronzeHonors",
        "league_medal": "leagueMedalHonors",
        "league_relegation": "leagueRelegationHonors",
        "league_promotion": "leaguePromotionHonors",
        "cup_title": "cupTitleHonors",
        "lost_cup_final": "lostCupFinalHonors",
    }
    league_medal_types = {
        "league_title",
        "league_silver",
        "league_bronze",
    }

    player["sets"]["honors"].add(
        honor_type
    )
    player["sets"][set_name_by_type[honor_type]].add(
        honor["id"]
    )
    player["sets"]["honorSeasons"].add(
        f"{honor_type}:{honor['id']}"
    )

    if honor_type in league_medal_types:
        player["sets"]["honors"].add(
            "league_medal"
        )
        player["sets"]["leagueMedalHonors"].add(
            honor["id"]
        )
        player["sets"]["honorSeasons"].add(
            f"league_medal:{honor['id']}"
        )


def apply_league_honor(
    players,
    appearances,
    matches,
    honor,
    honor_type,
    strict=True
):

    season_matches = honor_matches(
        matches,
        honor
    )

    if not season_matches:
        if not strict:
            return

        raise ValueError(
            f"Fant ingen seriekamper for {honor['label']}."
        )

    minimum_share = float(
        honor.get(
            "minimum_appearance_share",
            0
        )
    )
    minimum = max(
        1,
        math.ceil(
            len(season_matches)
            * minimum_share
        )
    )
    match_ids = {
        match["id"]
        for match in season_matches
    }
    counts = count_appearances_by_player(
        appearances,
        match_ids
    )

    for player_id, count in counts.items():

        if count < minimum:
            continue

        if player_id not in players:
            continue

        add_honor_to_player(
            players[player_id],
            honor_type,
            honor
        )


def apply_appearance_honor(
    players,
    appearances,
    matches,
    honor,
    honor_type,
    final_only=False,
    strict=True
):

    season_matches = honor_matches(
        matches,
        honor,
        final_only=final_only
    )

    if not season_matches:
        if not strict:
            return

        raise ValueError(
            f"Fant ingen kamper for {honor['label']}."
        )

    minimum = int(
        honor.get(
            "minimum_appearances",
            1
        )
    )
    match_ids = {
        match["id"]
        for match in season_matches
    }
    counts = count_appearances_by_player(
        appearances,
        match_ids
    )

    for player_id, count in counts.items():

        if count < minimum:
            continue

        if player_id not in players:
            continue

        add_honor_to_player(
            players[player_id],
            honor_type,
            honor
        )


def apply_honors(players, all_data, honors, strict=True):

    for honor in honors.get(
        "league_titles",
        []
    ):
        apply_league_honor(
            players,
            all_data["brann_appearances"],
            all_data["matches"],
            honor,
            "league_title",
            strict=strict
        )

    for honor in honors.get(
        "league_silver_medals",
        []
    ):
        apply_league_honor(
            players,
            all_data["brann_appearances"],
            all_data["matches"],
            honor,
            "league_silver",
            strict=strict
        )

    for honor in honors.get(
        "league_bronze_medals",
        []
    ):
        apply_league_honor(
            players,
            all_data["brann_appearances"],
            all_data["matches"],
            honor,
            "league_bronze",
            strict=strict
        )

    for honor in honors.get(
        "league_relegations",
        []
    ):
        apply_league_honor(
            players,
            all_data["brann_appearances"],
            all_data["matches"],
            honor,
            "league_relegation",
            strict=strict
        )

    for honor in honors.get(
        "league_promotions",
        []
    ):
        apply_league_honor(
            players,
            all_data["brann_appearances"],
            all_data["matches"],
            honor,
            "league_promotion",
            strict=strict
        )

    for honor in honors.get(
        "cup_titles",
        []
    ):
        apply_appearance_honor(
            players,
            all_data["brann_appearances"],
            all_data["matches"],
            honor,
            "cup_title",
            strict=strict
        )

    for honor in honors.get(
        "lost_cup_finals",
        []
    ):
        apply_appearance_honor(
            players,
            all_data["brann_appearances"],
            all_data["matches"],
            honor,
            "lost_cup_final",
            final_only=True,
            strict=strict
        )


def add_match_context_sets(player, match, opponent_id):

    year = int(match["date"][:4])
    ground_id = match["ground_id"]
    ground_country = match["ground_country_code"]
    competition_id = match["competition_id"]
    competition_family = match["competition_count_as"]

    player["sets"]["opponentsPlayed"].add(
        opponent_id
    )
    player["sets"]["yearsPlayed"].add(
        year
    )
    player["sets"]["decadesPlayed"].add(
        decade_label(year)
    )

    if ground_id:
        player["sets"]["groundsPlayed"].add(
            ground_id
        )

    if ground_country:
        player["sets"]["groundCountriesPlayed"].add(
            ground_country
        )

    if competition_id and competition_family != "serie":
        player["sets"]["competitionsPlayed"].add(
            competition_id
        )

    for group_id in league_competition_group_ids(match):
        player["sets"]["leagueCompetitionGroupsPlayed"].add(
            group_id
        )

    if competition_family:
        player["sets"]["competitionFamiliesPlayed"].add(
            competition_family
        )


def add_event_context_sets(
    player,
    match,
    opponent_id,
    prefix,
    include_opponent=True
):

    ground_id = match["ground_id"]
    competition_id = match["competition_id"]
    competition_family = match["competition_count_as"]

    if include_opponent:
        player["sets"][f"{prefix}Opponents"].add(
            opponent_id
        )

    if ground_id:
        player["sets"][f"{prefix}Grounds"].add(
            ground_id
        )

    if competition_id and competition_family != "serie":
        player["sets"][f"{prefix}Competitions"].add(
            competition_id
        )

    for group_id in league_competition_group_ids(match):
        player["sets"][f"{prefix}LeagueCompetitionGroups"].add(
            group_id
        )


def build_facts_and_indexes(start_year=None, end_year=None):

    players = load_player_index()
    player_sort_key = {
        player_id: (
            player["searchText"],
            player_id
        )
        for player_id, player in players.items()
    }
    all_data = query_all_data(
        start_year=start_year,
        end_year=end_year
    )
    matches = all_data["matches"]
    coaches = coach_match_bounds(
        load_coaches(),
        matches,
        strict=start_year is None and end_year is None
    )
    honors = load_honors()
    manual_grid_criteria = load_manual_grid_criteria()
    shirt_number_corrections = load_shirt_number_corrections()

    metrics = {
        "appearancesTotal": {},
        "goalsTotal": {},
        "penaltyGoalsTotal": {},
        "lateGoalsAfter90Total": {},
        "multiGoalMatchesTotal": {},
        "hatTrickMatchesTotal": {},
        "redCardsTotal": {},
        "coachCount": {},
        "goalsByOpponent": make_nested_counter(),
        "appearancesByCompetition": make_nested_counter(),
        "goalsByCompetition": make_nested_counter(),
        "redCardsByCompetition": make_nested_counter(),
        "appearancesByLeagueCompetitionGroup": make_nested_counter(),
        "goalsByLeagueCompetitionGroup": make_nested_counter(),
        "redCardsByLeagueCompetitionGroup": make_nested_counter(),
        "appearancesByCoach": make_nested_counter(),
        "goalsByCoach": make_nested_counter(),
        "coAppearancesByPlayer": make_nested_counter(),
        "appearancesForOpponentTeamAgainstBrann": (
            make_nested_counter()
        ),
    }

    brann_players_by_match = defaultdict(set)
    first_match_by_player = {}
    last_match_by_player = {}

    for appearance in all_data["brann_appearances"]:

        player_id = appearance["player_id"]
        player = players.get(player_id)

        if not player:
            continue

        match = matches[appearance["match_id"]]
        opponent_id = opponent_id_for_match(match)
        brann_players_by_match[appearance["match_id"]].add(
            player_id
        )
        player["stats"]["appearances"] += 1

        if appearance["starting"] == 1:
            player["stats"]["starts"] += 1
        elif appearance["starting"] == 0:
            player["stats"]["substituteAppearances"] += 1

        if (
            player_id not in first_match_by_player
            or match["date"] < first_match_by_player[player_id]["date"]
        ):
            first_match_by_player[player_id] = match

        if (
            player_id not in last_match_by_player
            or match["date"] > last_match_by_player[player_id]["date"]
        ):
            last_match_by_player[player_id] = match

        add_match_context_sets(
            player,
            match,
            opponent_id
        )

        if appearance["role_abbr"]:
            player["sets"]["roles"].add(
                appearance["role_abbr"]
            )

        if appearance["shirt_number"] is not None:
            shirt_number = corrected_shirt_number(
                appearance,
                shirt_number_corrections
            )
            player["sets"]["shirtNumbers"].add(
                int(shirt_number)
            )

        if is_cup_final(match):
            player["sets"]["cupFinals"].add(
                match["id"]
            )
            won = brann_won_match(match)

            if won is True:
                player["sets"]["wonCupFinals"].add(
                    match["id"]
                )
            elif won is False:
                player["sets"]["lostCupFinals"].add(
                    match["id"]
                )

        if is_cup_semifinal(match):
            player["sets"]["cupSemifinals"].add(
                match["id"]
            )

        if is_euro_group_or_league_phase(match):
            player["sets"]["euroGroupOrLeaguePhase"].add(
                match["id"]
            )

        if is_euro_qualifier(match):
            player["sets"]["euroQualifiers"].add(
                match["id"]
            )

        for coach_id in coach_ids_for_date(
            coaches,
            match["date"]
        ):
            player["sets"]["coachesPlayed"].add(
                coach_id
            )
            metrics["appearancesByCoach"][coach_id][player_id] += 1

    players = {
        player_id: player
        for player_id, player in players.items()
        if player["stats"]["appearances"] > 0
    }
    apply_manual_grid_criteria(
        players,
        manual_grid_criteria
    )

    goals_by_match_player = defaultdict(make_counter)

    for event in all_data["brann_events"]:

        player_id = event["subject_player_id"]

        if not player_id or player_id not in players:
            continue

        player = players[player_id]
        match = matches[event["match_id"]]
        opponent_id = opponent_id_for_match(match)
        event_type = event["event_type"]

        if event_type in ("goal", "penaltyGoal"):
            include_opponent_goal = (
                match["competition_count_as"] != "cup"
            )
            player["stats"]["goals"] += 1
            goals_by_match_player[event["match_id"]][player_id] += 1
            add_event_context_sets(
                player,
                match,
                opponent_id,
                "scoredAgainst",
                include_opponent=include_opponent_goal
            )

            if include_opponent_goal:
                metrics["goalsByOpponent"][opponent_id][player_id] += 1

            if (
                match["competition_id"]
                and match["competition_count_as"] != "serie"
            ):
                metrics["goalsByCompetition"][
                    match["competition_id"]
                ][player_id] += 1

            for group_id in league_competition_group_ids(match):
                metrics["goalsByLeagueCompetitionGroup"][
                    group_id
                ][player_id] += 1

            if event_type == "penaltyGoal":
                player["stats"]["penaltyGoals"] += 1

            if event["minute"] is not None and event["minute"] > 90:
                player["stats"]["lateGoalsAfter90"] += 1
                player["sets"]["lateGoalAfter90Matches"].add(
                    match["id"]
                )

            for coach_id in coach_ids_for_date(
                coaches,
                match["date"]
            ):
                player["sets"]["coachesScored"].add(
                    coach_id
                )
                metrics["goalsByCoach"][coach_id][player_id] += 1

        elif event_type == "yc":
            player["stats"]["yellowCards"] += 1
            add_event_context_sets(
                player,
                match,
                opponent_id,
                "yellowCardAgainst"
            )

        elif event_type == "rc":
            player["stats"]["redCards"] += 1
            add_event_context_sets(
                player,
                match,
                opponent_id,
                "redCardAgainst"
            )

            if (
                match["competition_id"]
                and match["competition_count_as"] != "serie"
            ):
                metrics["redCardsByCompetition"][
                    match["competition_id"]
                ][player_id] += 1

            for group_id in league_competition_group_ids(match):
                metrics["redCardsByLeagueCompetitionGroup"][
                    group_id
                ][player_id] += 1

    for match_id, match_players in brann_players_by_match.items():

        for player_a, player_b in combinations(
            sorted(match_players),
            2
        ):
            metrics["coAppearancesByPlayer"][player_a][player_b] += 1
            metrics["coAppearancesByPlayer"][player_b][player_a] += 1

    for appearance in all_data["opponent_appearances_against_brann"]:

        player_id = appearance["player_id"]

        if player_id not in players:
            continue

        team_id = appearance["team_id"]
        players[player_id]["sets"][
            "opponentTeamsPlayedForAgainstBrann"
        ].add(
            team_id
        )
        metrics["appearancesForOpponentTeamAgainstBrann"][
            team_id
        ][player_id] += 1

    for player_id, player in players.items():

        first_match = first_match_by_player.get(
            player_id
        )
        last_match = last_match_by_player.get(
            player_id
        )

        if first_match:
            player["firstBrannMatchDate"] = first_match["date"]
            player["firstBrannYear"] = int(first_match["date"][:4])
            for coach_id in coach_ids_for_date(
                coaches,
                first_match["date"]
            ):
                player["sets"]["coachesDebutedUnder"].add(
                    coach_id
                )

        if last_match:
            player["lastBrannMatchDate"] = last_match["date"]
            player["lastBrannYear"] = int(last_match["date"][:4])

        player["brannYears"] = listify(
            player["sets"].get(
                "yearsPlayed",
                set()
            )
        )

        if (
            first_match
            and goals_by_match_player[first_match["id"]].get(player_id)
        ):
            player["sets"]["scoredInBrannDebut"].add(
                first_match["id"]
            )

        if (
            last_match
            and goals_by_match_player[last_match["id"]].get(player_id)
        ):
            player["sets"]["scoredInLastBrannMatch"].add(
                last_match["id"]
            )

        player["sets"]["firstNameInitials"].add(
            first_initial(
                player["name"]
            )
        )
        player["sets"]["lastNameInitials"].add(
            last_initial(
                player["name"]
            )
        )

        country_code = player["countryCode"]

        if country_code:
            player["sets"]["nationalities"].add(
                country_code
            )
            continent = COUNTRY_TO_CONTINENT.get(
                country_code
            )

            if continent:
                player["sets"]["continents"].add(
                    continent
                )

    for match_id, goal_counts in goals_by_match_player.items():

        for player_id, goal_count in goal_counts.items():

            if player_id not in players:
                continue

            if goal_count >= 2:
                players[player_id]["stats"]["multiGoalMatches"] += 1
                players[player_id]["sets"]["multiGoalMatches"].add(
                    match_id
                )

            if goal_count >= 3:
                players[player_id]["stats"]["hatTrickMatches"] += 1
                players[player_id]["sets"]["hatTrickMatches"].add(
                    match_id
                )

    apply_honors(
        players,
        all_data,
        honors,
        strict=start_year is None and end_year is None
    )

    for player_id, player in players.items():
        metrics["appearancesTotal"][player_id] = player["stats"][
            "appearances"
        ]
        metrics["goalsTotal"][player_id] = player["stats"]["goals"]
        metrics["penaltyGoalsTotal"][player_id] = player["stats"][
            "penaltyGoals"
        ]
        metrics["lateGoalsAfter90Total"][player_id] = player["stats"][
            "lateGoalsAfter90"
        ]
        metrics["multiGoalMatchesTotal"][player_id] = player["stats"][
            "multiGoalMatches"
        ]
        metrics["hatTrickMatchesTotal"][player_id] = player["stats"][
            "hatTrickMatches"
        ]
        metrics["redCardsTotal"][player_id] = player["stats"][
            "redCards"
        ]
        metrics["coachCount"][player_id] = len(
            player["sets"].get(
                "coachesPlayed",
                set()
            )
        )

    for appearance in all_data["brann_appearances"]:

        player_id = appearance["player_id"]

        if player_id not in players:
            continue

        match = matches[appearance["match_id"]]
        opponent_id = opponent_id_for_match(match)

        if (
            match["competition_id"]
            and match["competition_count_as"] != "serie"
        ):
            metrics["appearancesByCompetition"][
                match["competition_id"]
            ][player_id] += 1

        for group_id in league_competition_group_ids(match):
            metrics["appearancesByLeagueCompetitionGroup"][
                group_id
            ][player_id] += 1

    return (
        players,
        all_data["entities"],
        coaches,
        honors,
        manual_grid_criteria,
        metrics,
        player_sort_key,
    )


def metric_values(counter):

    return {
        player_id: value
        for player_id, value in sorted(
            counter.items(),
            key=lambda item: item[0]
        )
        if value
    }


def nested_metric_values(counter):

    return {
        entity_id: metric_values(values)
        for entity_id, values in sorted(
            counter.items(),
            key=lambda item: item[0]
        )
        if values
    }


def serialize_metrics(metrics):

    serialized = {}

    for metric_id, value in metrics.items():

        first_value = next(
            iter(value.values()),
            None
        )

        if isinstance(first_value, dict):
            serialized[metric_id] = nested_metric_values(
                value
            )
        else:
            serialized[metric_id] = metric_values(
                value
            )

    return serialized


def add_criterion(criteria, criterion_id, label, players, category):

    if not players:
        return

    criteria[criterion_id] = {
        "id": criterion_id,
        "label": label,
        "category": category,
        "players": players,
        "count": len(players),
    }


def players_with_set(players, set_name, value=None):

    result = []

    for player_id, player in players.items():

        values = player["sets"].get(
            set_name,
            set()
        )

        if value is None:

            if values:
                result.append(player_id)

        elif value in values:
            result.append(player_id)

    return result


def players_without_stat(players, stat_name):

    return [
        player_id
        for player_id, player in players.items()
        if player["stats"].get(
            stat_name,
            0
        ) == 0
    ]


def entity_name(entities, entity_type, entity_id):

    return (
        entities
        .get(entity_type, {})
        .get(entity_id, {})
        .get("name")
        or entities
        .get(entity_type, {})
        .get(entity_id, {})
        .get("label")
        or str(entity_id)
    )


def country_label(country_code):

    return COUNTRY_LABELS.get(
        country_code,
        country_code
    )


def display_competition(competition):

    result = dict(
        competition
    )

    if result.get("name") == "Champions League":
        result["name"] = "kvalik til Champions League"
        result["fullName"] = "Kvalifisering til Champions League"

    return result


def whitelisted_ground_ids(ground_entities, ground_name):

    wanted = ground_name.casefold()

    return {
        ground_id
        for ground_id, ground in ground_entities.items()
        if (ground.get("name") or "").casefold() == wanted
        or (ground.get("fullName") or "").casefold() == wanted
    }


def build_entities(players, entities, coaches):

    result = {
        "players": {
            player_id: {
                "id": player_id,
                "name": player["name"],
                "searchText": player["searchText"],
            }
            for player_id, player in sorted(
                players.items()
            )
        },
        "opponents": {},
        "competitions": {
            competition_id: display_competition(
                competition
            )
            for competition_id, competition in entities[
                "competitions"
            ].items()
            if competition.get("countAs") != "serie"
        },
        "leagueCompetitionGroups": LEAGUE_COMPETITION_GROUPS,
        "grounds": {},
        "groundCountries": {},
        "shirtNumbers": {},
        "roles": {
            role_id: {
                "id": role_id,
                "label": label,
            }
            for role_id, label in ROLE_LABELS.items()
        },
        "years": {},
        "decades": {},
        "coaches": {
            coach["id"]: coach
            for coach in coaches
        },
        "nationalities": {},
        "continents": {},
        "initials": {},
    }

    all_sets = defaultdict(set)

    for player in players.values():

        for set_name, values in player["sets"].items():

            for value in values:

                if value is not None:
                    all_sets[set_name].add(value)

    for opponent_id in all_sets["opponentsPlayed"]:

        team = entities["teams"].get(
            opponent_id
        )

        if team:
            result["opponents"][opponent_id] = team

    for country_code in all_sets["groundCountriesPlayed"]:

        result["groundCountries"][country_code] = {
            "id": country_code,
            "label": country_label(
                country_code
            ),
        }

    whitelisted_names = {
        criterion["ground_name"]
        for criterion in WHITELISTED_GROUND_CRITERIA
    }

    for ground_id, ground in entities["grounds"].items():

        if (
            ground.get("name") in whitelisted_names
            or ground.get("fullName") in whitelisted_names
        ):
            result["grounds"][ground_id] = ground

    for shirt_number in all_sets["shirtNumbers"]:
        result["shirtNumbers"][str(shirt_number)] = {
            "id": str(shirt_number),
            "label": str(shirt_number),
        }

    for year in all_sets["yearsPlayed"]:
        result["years"][str(year)] = {
            "id": str(year),
            "label": str(year),
        }

    for decade in all_sets["decadesPlayed"]:
        result["decades"][decade] = {
            "id": decade,
            "label": decade,
        }

    for country_code in all_sets["nationalities"]:
        result["nationalities"][country_code] = {
            "id": country_code,
            "label": country_label(
                country_code
            ),
            "continent": COUNTRY_TO_CONTINENT.get(
                country_code
            ),
        }

    for continent in all_sets["continents"]:
        result["continents"][continent] = {
            "id": continent,
            "label": continent,
        }

    for initial in (
        all_sets["firstNameInitials"]
        | all_sets["lastNameInitials"]
    ):
        result["initials"][initial] = {
            "id": initial,
            "label": initial,
        }

    return result


def build_criteria(
    players,
    entities,
    coaches,
    honors,
    manual_grid_criteria,
    player_sort_key
):

    criteria = {}

    def sorted_players(player_ids):

        return sort_player_ids(
            player_ids,
            player_sort_key
        )

    all_players = sorted_players(
        players.keys()
    )
    add_criterion(
        criteria,
        "player:any",
        "Alle registrerte Brann-spillere",
        all_players,
        "base"
    )

    simple_sets = [
        (
            "goal:any",
            "Scoret minst ett Brann-mål",
            "scoredAgainstOpponents",
            "scoring",
        ),
        (
            "penalty_goal:any",
            "Scoret minst ett straffemål for Brann",
            None,
            "scoring",
        ),
        (
            "late_goal_after_90:any",
            "Scoret minst ett mål etter 90. minutt",
            "lateGoalAfter90Matches",
            "scoring",
        ),
        (
            "multi_goal_match:any",
            "Scoret minst to mål i samme Brann-kamp",
            "multiGoalMatches",
            "scoring",
        ),
        (
            "hat_trick:any",
            "Scoret hat trick for Brann",
            "hatTrickMatches",
            "scoring",
        ),
        (
            "goal_in_debut:any",
            "Scoret i Brann-debuten",
            "scoredInBrannDebut",
            "scoring",
        ),
        (
            "goal_in_last_match:any",
            "Scoret i siste registrerte Brann-kamp",
            "scoredInLastBrannMatch",
            "scoring",
        ),
        (
            "red_card:any",
            "Fikk minst ett rødt kort for Brann",
            "redCardAgainstOpponents",
            "cards",
        ),
        (
            "cup_final:appeared",
            "Spilte cupfinale for Brann",
            "cupFinals",
            "cup",
        ),
        (
            "cup_final:won",
            "Spilte og vant cupfinale for Brann",
            "wonCupFinals",
            "cup",
        ),
        (
            "cup_final:lost",
            "Spilte og tapte cupfinale for Brann",
            "lostCupFinals",
            "cup",
        ),
        (
            "cup_semifinal:appeared",
            "Spilte semifinale i cupen for Brann",
            "cupSemifinals",
            "cup",
        ),
        (
            "euro_group_or_league_phase:appeared",
            "Spilte gruppespill eller ligafase i Europa for Brann",
            "euroGroupOrLeaguePhase",
            "europe",
        ),
        (
            "euro_qualifier:appeared",
            "Spilte kvalifiseringskamp i Europa for Brann",
            "euroQualifiers",
            "europe",
        ),
        (
            "honor:league_title",
            "Seriegull med Brann",
            "leagueTitleHonors",
            "honors",
        ),
        (
            "honor:league_silver",
            "Seriesølv med Brann",
            "leagueSilverHonors",
            "honors",
        ),
        (
            "honor:league_bronze",
            "Seriebronse med Brann",
            "leagueBronzeHonors",
            "honors",
        ),
        (
            "honor:league_medal",
            "Seriemedalje med Brann",
            "leagueMedalHonors",
            "honors",
        ),
        (
            "honor:league_relegation",
            "Rykket ned med Brann",
            "leagueRelegationHonors",
            "honors",
        ),
        (
            "honor:league_promotion",
            "Rykket opp med Brann",
            "leaguePromotionHonors",
            "honors",
        ),
        (
            "honor:cup_title",
            "Vunnet cupen for Brann",
            "cupTitleHonors",
            "honors",
        ),
        (
            "honor:lost_cup_final",
            "Tapt cupfinale for Brann",
            "lostCupFinalHonors",
            "honors",
        ),
    ]

    for criterion_id, label, set_name, category in simple_sets:

        if criterion_id == "penalty_goal:any":
            matching = [
                player_id
                for player_id, player in players.items()
                if player["stats"]["penaltyGoals"] > 0
            ]
        else:
            matching = players_with_set(
                players,
                set_name
            )

        add_criterion(
            criteria,
            criterion_id,
            label,
            sorted_players(matching),
            category
        )

    for manual_criterion in manual_grid_criteria:
        add_criterion(
            criteria,
            f"manual:{manual_criterion['id']}",
            manual_criterion["label"],
            sorted_players(
                players_with_set(
                    players,
                    "manualCriteria",
                    manual_criterion["id"]
                )
            ),
            manual_criterion.get(
                "category",
                "manual"
            )
        )

    honor_criteria = [
        (
            "league_title",
            "league_titles",
            "Seriegull med Brann {label}",
        ),
        (
            "league_silver",
            "league_silver_medals",
            "Seriesølv med Brann {label}",
        ),
        (
            "league_bronze",
            "league_bronze_medals",
            "Seriebronse med Brann {label}",
        ),
        (
            "league_relegation",
            "league_relegations",
            "Rykket ned med Brann {label}",
        ),
        (
            "league_promotion",
            "league_promotions",
            "Rykket opp med Brann {label}",
        ),
        (
            "cup_title",
            "cup_titles",
            "Vunnet cupen for Brann {label}",
        ),
        (
            "lost_cup_final",
            "lost_cup_finals",
            "Tapt cupfinale for Brann {label}",
        ),
    ]

    for honor_type, honor_key, label_template in honor_criteria:

        for honor in honors.get(
            honor_key,
            []
        ):
            value = f"{honor_type}:{honor['id']}"
            add_criterion(
                criteria,
                f"honor:{value}",
                label_template.format(
                    label=honor["label"]
                ),
                sorted_players(
                    players_with_set(
                        players,
                        "honorSeasons",
                        value
                    )
                ),
                "honors"
            )

    league_medal_honors = []
    for honor_key in (
        "league_titles",
        "league_silver_medals",
        "league_bronze_medals",
    ):
        league_medal_honors.extend(
            honors.get(
                honor_key,
                []
            )
        )

    for honor in league_medal_honors:
        value = f"league_medal:{honor['id']}"
        add_criterion(
            criteria,
            f"honor:{value}",
            "Seriemedalje med Brann {label}".format(
                label=honor["label"]
            ),
            sorted_players(
                players_with_set(
                    players,
                    "honorSeasons",
                    value
                )
            ),
            "honors"
        )

    add_criterion(
        criteria,
        "penalty_goal:none",
        "Aldri scoret straffemål for Brann",
        sorted_players(
            players_without_stat(
                players,
                "penaltyGoals"
            )
        ),
        "scoring"
    )

    for ground_criterion in WHITELISTED_GROUND_CRITERIA:

        matching_players = set()

        for ground_id in whitelisted_ground_ids(
            entities.get(
                "grounds",
                {}
            ),
            ground_criterion["ground_name"]
        ):
            matching_players.update(
                players_with_set(
                    players,
                    ground_criterion["set_name"],
                    ground_id
                )
            )

        add_criterion(
            criteria,
            f"ground_whitelist:{ground_criterion['id']}",
            ground_criterion["label"],
            sorted_players(
                matching_players
            ),
            ground_criterion["category"]
        )

    set_category_labels = [
        (
            "opponent_goal",
            "scoredAgainstOpponents",
            "Har scoret mot {name}",
            "opponents",
            "opponent"
        ),
        (
            "competition",
            "competitionsPlayed",
            "Har spilt i {name}",
            "competitions",
            "competitions"
        ),
        (
            "competition_goal",
            "scoredAgainstCompetitions",
            "Har scoret i {name}",
            "competitions",
            "competitions"
        ),
        (
            "competition_red_card",
            "redCardAgainstCompetitions",
            "Har fått rødt kort i {name}",
            "competitions",
            "cards"
        ),
        (
            "league_competition_group",
            "leagueCompetitionGroupsPlayed",
            "{playedLabel}",
            "leagueCompetitionGroups",
            "competitions"
        ),
        (
            "league_competition_group_goal",
            "scoredAgainstLeagueCompetitionGroups",
            "{goalLabel}",
            "leagueCompetitionGroups",
            "competitions"
        ),
        (
            "league_competition_group_red_card",
            "redCardAgainstLeagueCompetitionGroups",
            "{redCardLabel}",
            "leagueCompetitionGroups",
            "cards"
        ),
        (
            "ground",
            "groundsPlayed",
            "Har spilt på {name}",
            "grounds",
            "grounds"
        ),
        (
            "ground_goal",
            "scoredAgainstGrounds",
            "Har scoret på {name}",
            "grounds",
            "grounds"
        ),
        (
            "ground_red_card",
            "redCardAgainstGrounds",
            "Har fått rødt kort på {name}",
            "grounds",
            "cards"
        ),
        (
            "ground_country",
            "groundCountriesPlayed",
            "Har spilt kamp for Brann i {name}",
            "groundCountries",
            "geography"
        ),
        (
            "shirt_number",
            "shirtNumbers",
            "Har spilt kamp for Brann med draktnummer {name}",
            "shirtNumbers",
            "shirtNumbers"
        ),
        (
            "role",
            "roles",
            "Har vært registrert som {name}",
            "roles",
            "positions"
        ),
        (
            "year",
            "yearsPlayed",
            "Spilte Brann-kamp i {name}",
            "years",
            "dates"
        ),
        (
            "decade",
            "decadesPlayed",
            "Spilte Brann-kamp på {name}-tallet",
            "decades",
            "dates"
        ),
        (
            "nationality",
            "nationalities",
            "Nasjonalitet: {name}",
            "nationalities",
            "identity"
        ),
        (
            "continent",
            "continents",
            "Kontinent: {name}",
            "continents",
            "identity"
        ),
        (
            "opponent_team_against_brann",
            "opponentTeamsPlayedForAgainstBrann",
            "Har spilt for {name} mot Brann",
            "opponents",
            "opponents"
        ),
    ]

    for prefix, set_name, label_template, entity_type, category in (
        set_category_labels
    ):

        if prefix in {
            "ground",
            "ground_goal",
            "ground_red_card",
        }:
            continue

        values = set()

        for player in players.values():
            values.update(
                value
                for value in player["sets"].get(
                    set_name,
                    set()
                )
                if value is not None
            )

        for value in values:

            if (
                prefix == "role"
                and value not in INCLUDED_ROLE_CRITERIA
            ):
                continue

            if (
                prefix == "shirt_number"
                and int(value) not in INCLUDED_SHIRT_NUMBER_CRITERIA
            ):
                continue

            entity = {}

            if entity_type == "roles":
                name = ROLE_LABELS.get(
                    value,
                    value
                )
            elif entity_type in ("shirtNumbers", "years"):
                name = str(value)
            elif entity_type == "decades":
                name = str(value)[:-1]
            else:
                entity = entities.get(
                    entity_type,
                    {}
                ).get(
                    value,
                    {}
                )
                name = (
                    entity.get("name")
                    or entity.get("label")
                    or str(value)
                )

            add_criterion(
                criteria,
                f"{prefix}:{normalize_id_part(value)}",
                (
                    name if prefix == "role" else label_template.format(
                    name=name,
                    playedLabel=entity.get("playedLabel", name),
                    goalLabel=entity.get("goalLabel", name),
                    redCardLabel=entity.get("redCardLabel", name),
                    )
                ),
                sorted_players(
                    players_with_set(
                        players,
                        set_name,
                        value
                    )
                ),
                category
            )

    for initial_kind, set_name, label_part in [
        ("first_name_initial", "firstNameInitials", "Fornavn"),
        ("last_name_initial", "lastNameInitials", "Etternavn"),
    ]:

        initials = set()

        for player in players.values():
            initials.update(
                value
                for value in player["sets"].get(
                    set_name,
                    set()
                )
                if value
            )

        for initial in initials:
            add_criterion(
                criteria,
                f"{initial_kind}:{initial}",
                f"{label_part} begynner på {initial}",
                sorted_players(
                    players_with_set(
                        players,
                        set_name,
                        initial
                    )
                ),
                "identity"
            )

    for coach in coaches:

        add_criterion(
            criteria,
            f"coach_played:{coach['id']}",
            f"Spilte under {coach['name']}",
            sorted_players(
                players_with_set(
                    players,
                    "coachesPlayed",
                    coach["id"]
                )
            ),
            "coaches"
        )
        add_criterion(
            criteria,
            f"coach_debut:{coach['id']}",
            f"Debuterte under {coach['name']}",
            sorted_players(
                players_with_set(
                    players,
                    "coachesDebutedUnder",
                    coach["id"]
                )
            ),
            "coaches"
        )
        add_criterion(
            criteria,
            f"coach_goal:{coach['id']}",
            f"Scoret under {coach['name']}",
            sorted_players(
                players_with_set(
                    players,
                    "coachesScored",
                    coach["id"]
                )
            ),
            "coaches"
        )

    max_coaches = max(
        (
            len(player["sets"].get("coachesPlayed", set()))
            for player in players.values()
        ),
        default=0
    )

    for threshold in range(2, max_coaches + 1):
        add_criterion(
            criteria,
            f"coach_count:min:{threshold}",
            f"Spilte under minst {threshold} Brann-trenere",
            sorted_players(
                player_id
                for player_id, player in players.items()
                if len(
                    player["sets"].get(
                        "coachesPlayed",
                        set()
                    )
                ) >= threshold
            ),
            "coaches"
        )

    for coach_a, coach_b in combinations(
        coaches,
        2
    ):

        add_criterion(
            criteria,
            f"coach_pair_played:{coach_a['id']}:{coach_b['id']}",
            (
                f"Spilte under både {coach_a['name']} "
                f"og {coach_b['name']}"
            ),
            sorted_players(
                player_id
                for player_id, player in players.items()
                if coach_a["id"] in player["sets"].get(
                    "coachesPlayed",
                    set()
                )
                and coach_b["id"] in player["sets"].get(
                    "coachesPlayed",
                    set()
                )
            ),
            "coaches"
        )
        add_criterion(
            criteria,
            f"coach_pair_goal:{coach_a['id']}:{coach_b['id']}",
            (
                f"Scoret under både {coach_a['name']} "
                f"og {coach_b['name']}"
            ),
            sorted_players(
                player_id
                for player_id, player in players.items()
                if coach_a["id"] in player["sets"].get(
                    "coachesScored",
                    set()
                )
                and coach_b["id"] in player["sets"].get(
                    "coachesScored",
                    set()
                )
            ),
            "coaches"
        )

    return dict(
        sorted(
            criteria.items()
        )
    )


def serialize_player_facts(players):

    serialized = {}

    for player_id, player in sorted(
        players.items()
    ):

        serialized[player_id] = {
            key: value
            for key, value in player.items()
            if key != "sets"
        }
        serialized[player_id]["sets"] = {
            set_name: listify(
                value
                for value in values
                if value is not None
            )
            for set_name, values in sorted(
                player["sets"].items()
            )
        }

    return serialized


def metric_families():

    families = {
        "appearancesTotal": {
            "label": "Antall Brann-kamper",
            "unit": "kamper",
            "supportsThreshold": True,
        },
        "goalsTotal": {
            "label": "Antall Brann-mål",
            "unit": "mål",
            "supportsThreshold": True,
        },
        "penaltyGoalsTotal": {
            "label": "Antall straffemål for Brann",
            "unit": "straffemål",
            "supportsThreshold": True,
        },
        "lateGoalsAfter90Total": {
            "label": "Antall mål etter 90. minutt",
            "unit": "mål",
            "supportsThreshold": True,
        },
        "multiGoalMatchesTotal": {
            "label": "Antall kamper med minst to Brann-mål",
            "unit": "kamper",
            "supportsThreshold": True,
        },
        "hatTrickMatchesTotal": {
            "label": "Antall hat trick for Brann",
            "unit": "hat trick",
            "supportsThreshold": True,
        },
        "redCardsTotal": {
            "label": "Antall røde kort for Brann",
            "unit": "røde kort",
            "supportsThreshold": True,
        },
        "coachCount": {
            "label": "Antall Brann-trenere spilt under",
            "unit": "trenere",
            "supportsThreshold": True,
        },
        "goalsByOpponent": {
            "label": "Antall Brann-mål mot motstander",
            "entityType": "opponents",
            "unit": "mål",
            "supportsThreshold": True,
        },
        "appearancesByCompetition": {
            "label": "Antall Brann-kamper i turnering",
            "entityType": "competitions",
            "unit": "kamper",
            "supportsThreshold": True,
        },
        "goalsByCompetition": {
            "label": "Antall Brann-mål i turnering",
            "entityType": "competitions",
            "unit": "mål",
            "supportsThreshold": True,
        },
        "redCardsByCompetition": {
            "label": "Antall røde kort i turnering",
            "entityType": "competitions",
            "unit": "røde kort",
            "supportsThreshold": True,
        },
        "appearancesByLeagueCompetitionGroup": {
            "label": "Antall Brann-kamper i seriekategori",
            "entityType": "leagueCompetitionGroups",
            "unit": "kamper",
            "supportsThreshold": True,
        },
        "goalsByLeagueCompetitionGroup": {
            "label": "Antall Brann-mål i seriekategori",
            "entityType": "leagueCompetitionGroups",
            "unit": "mål",
            "supportsThreshold": True,
        },
        "redCardsByLeagueCompetitionGroup": {
            "label": "Antall røde kort i seriekategori",
            "entityType": "leagueCompetitionGroups",
            "unit": "røde kort",
            "supportsThreshold": True,
        },
        "appearancesByGround": {
            "label": "Antall Brann-kamper på stadion",
            "entityType": "grounds",
            "unit": "kamper",
            "supportsThreshold": True,
        },
        "goalsByGround": {
            "label": "Antall Brann-mål på stadion",
            "entityType": "grounds",
            "unit": "mål",
            "supportsThreshold": True,
        },
        "redCardsByGround": {
            "label": "Antall røde kort på stadion",
            "entityType": "grounds",
            "unit": "røde kort",
            "supportsThreshold": True,
        },
        "appearancesByCoach": {
            "label": "Antall Brann-kamper under trener",
            "entityType": "coaches",
            "unit": "kamper",
            "supportsThreshold": True,
        },
        "goalsByCoach": {
            "label": "Antall Brann-mål under trener",
            "entityType": "coaches",
            "unit": "mål",
            "supportsThreshold": True,
        },
        "coAppearancesByPlayer": {
            "label": "Antall kamper på banen samtidig med spiller",
            "entityType": "players",
            "unit": "kamper",
            "supportsThreshold": True,
        },
        "appearancesForOpponentTeamAgainstBrann": {
            "label": "Antall kamper for motstanderlag mot Brann",
            "entityType": "opponents",
            "unit": "kamper",
            "supportsThreshold": True,
        },
    }

    return {
        metric_id: family
        for metric_id, family in families.items()
        if family.get("entityType") != "grounds"
    }


def date_fields():

    return {
        "firstBrannMatchDate": {
            "label": "Debutdato for Brann",
            "supportsBeforeAfter": True,
        },
        "lastBrannMatchDate": {
            "label": "Dato for siste registrerte Brann-kamp",
            "supportsBeforeAfter": True,
        },
    }


def unsupported_criteria():

    return [
        {
            "label": "Detaljert posisjon som h\u00f8yreback/spiss/ving",
            "reason": (
                "Databasen har bare bred kamprolle, "
                "ikke prim\u00e6rposisjon."
            ),
        },
    ]


def period_metadata(start_year=None, end_year=None):

    if start_year is None and end_year is None:
        return {
            "id": "all",
            "label": "Full historikk",
            "startYear": None,
            "endYear": None,
        }

    if start_year is not None and end_year is None:
        label = f"Moderne ({start_year}-)"
    elif start_year is None:
        label = f"Til og med {end_year}"
    else:
        label = f"{start_year}-{end_year}"

    return {
        "id": "modern" if start_year == 2000 and end_year is None else (
            f"{start_year or 'start'}-{end_year or 'latest'}"
        ),
        "label": label,
        "startYear": start_year,
        "endYear": end_year,
    }


def build_exports(start_year=None, end_year=None):

    (
        players,
        entities,
        coaches,
        honors,
        manual_grid_criteria,
        metrics,
        player_sort_key,
    ) = build_facts_and_indexes(
        start_year=start_year,
        end_year=end_year
    )
    generated_at = datetime.now(
        timezone.utc
    ).isoformat()
    serialized_entities = build_entities(
        players,
        entities,
        coaches
    )
    criteria = build_criteria(
        players,
        serialized_entities,
        coaches,
        honors,
        manual_grid_criteria,
        player_sort_key
    )
    serialized_metrics = serialize_metrics(
        metrics
    )
    period = period_metadata(
        start_year=start_year,
        end_year=end_year
    )

    facts = {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": generated_at,
        "source": "derived_from_sqlite_and_manual_grid_criteria",
        "period": period,
        "brannTeamId": tenable.BRANN_ID,
        "playerCount": len(players),
        "players": serialize_player_facts(
            players
        ),
    }
    criteria_index = {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": generated_at,
        "source": "derived_from_sqlite_and_manual_grid_criteria",
        "period": period,
        "brannTeamId": tenable.BRANN_ID,
        "playerCount": len(players),
        "criteriaCount": len(criteria),
        "metricFamilyCount": len(serialized_metrics),
        "entities": serialized_entities,
        "criteria": criteria,
        "metricFamilies": metric_families(),
        "metrics": serialized_metrics,
        "dateFields": date_fields(),
        "unsupportedCriteria": unsupported_criteria(),
    }

    return facts, criteria_index


def write_json(path, data):

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with path.open(
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2
        )
        file.write("\n")


def main():

    export_jobs = [
        (
            None,
            None,
            FACTS_OUTPUT_FILE,
            CRITERIA_OUTPUT_FILE,
        ),
        (
            2000,
            None,
            MODERN_FACTS_OUTPUT_FILE,
            MODERN_CRITERIA_OUTPUT_FILE,
        ),
    ]
    export_jobs.extend(
        (
            start_year,
            None,
            GRID_RANGE_OUTPUT_DIR / f"player-facts-since-{start_year}.json",
            GRID_RANGE_OUTPUT_DIR / f"grid-criteria-index-since-{start_year}.json",
        )
        for start_year in GRID_RANGE_START_YEARS
    )

    for start_year, end_year, facts_file, criteria_file in export_jobs:
        facts, criteria_index = build_exports(
            start_year=start_year,
            end_year=end_year
        )

        write_json(
            facts_file,
            facts
        )
        write_json(
            criteria_file,
            criteria_index
        )

        print(
            f"Exported {facts['playerCount']} player facts to "
            f"{facts_file}"
        )
        print(
            f"Exported {criteria_index['criteriaCount']} criteria and "
            f"{criteria_index['metricFamilyCount']} metric families to "
            f"{criteria_file}"
        )


if __name__ == "__main__":
    main()
