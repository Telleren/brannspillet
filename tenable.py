import argparse
import random
import sqlite3
import sys
import unicodedata
from pathlib import Path


# ============================================================
# INNSTILLINGER
# ============================================================

BRANN_ID = "05bb57f9-3430-5a18-b77c-96b578525b9c"

MODERN_DB_FILE = Path("data/brannspillet_v2.db")
HISTORICAL_DB_FILE = Path(
    "data/brannspillet_historical_sandbox.db"
)

MIN_YEAR = 1911
DEFAULT_START_YEAR = 1963
MAX_YEAR = 2026
ANSWER_COUNT = 10
STARTING_LIVES = 3

MIN_CUTOFF_BY_THEME = {
    "kamper": 50,
    "starter": 35,
    "innhopp": 20,
    "maal": 10,
    "utlendinger-kamper": 50,
    "utlendinger-maal": 10,
    "seire": 30,
    "kamper-mot": 5,
    "maal-mot": 3,
}

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(
        encoding="utf-8",
        errors="replace"
    )


# ============================================================
# TEMAER
# ============================================================

THEMES = {
    "kamper": {
        "title": "Flest kamper for Brann",
        "description": "Finn de 10 spillerne med flest Brann-kamper.",
        "kind": "simple",
        "metric": "kamper",
    },
    "starter": {
        "title": "Flest starter for Brann",
        "description": "Finn de 10 spillerne med flest starter for Brann.",
        "kind": "simple",
        "metric": "starter",
    },
    "innhopp": {
        "title": "Flest innhopp for Brann",
        "description": "Finn de 10 spillerne med flest innhopp for Brann.",
        "kind": "simple",
        "metric": "innhopp",
    },
    "maal": {
        "title": "Flest mål for Brann",
        "description": "Finn de 10 spillerne med flest Brann-mål.",
        "kind": "simple",
        "metric": "mål",
    },
    "utlendinger-kamper": {
        "title": "Utlendinger med flest kamper for Brann",
        "description": (
            "Finn de 10 utenlandske spillerne "
            "med flest Brann-kamper."
        ),
        "kind": "simple",
        "metric": "kamper",
    },
    "utlendinger-maal": {
        "title": "Utlendinger med flest mål for Brann",
        "description": (
            "Finn de 10 utenlandske spillerne "
            "med flest Brann-mål."
        ),
        "kind": "simple",
        "metric": "mål",
    },
    "seire": {
        "title": "Flest seire med Brann",
        "description": "Finn de 10 spillerne med flest Brann-seire.",
        "kind": "simple",
        "metric": "seire",
    },
    "kamper-mot": {
        "title": "Flest kamper mot {opponent}",
        "description": "Finn de 10 Brann-spillerne med flest kamper mot {opponent}.",
        "kind": "opponent",
        "metric": "kamper",
    },
    "maal-mot": {
        "title": "Flest mål mot {opponent}",
        "description": "Finn de 10 Brann-spillerne med flest mål mot {opponent}.",
        "kind": "opponent",
        "metric": "mål",
    },
}


# ============================================================
# HJELPEFUNKSJONER
# ============================================================

def normalize_text(text):

    if not text:
        return ""

    text = text.casefold().strip()

    text = unicodedata.normalize(
        "NFKD",
        text
    )

    return "".join(
        char
        for char in text
        if not unicodedata.combining(char)
    )


def parse_year(value, label):

    try:
        year = int(value)

    except ValueError as error:
        raise ValueError(
            f"{label} må være et årstall."
        ) from error

    if year < MIN_YEAR or year > MAX_YEAR:

        raise ValueError(
            f"{label} må være mellom "
            f"{MIN_YEAR} og {MAX_YEAR}."
        )

    return year


def open_database(path):

    if not path.exists():

        raise FileNotFoundError(
            f"Fant ikke databasen: {path}"
        )

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row

    return conn


def connect_databases(start_year, end_year):

    databases = []

    if start_year <= 1999:

        databases.append(
            {
                "name": "historical",
                "conn": open_database(
                    HISTORICAL_DB_FILE
                ),
            }
        )

    if end_year >= 2000:

        databases.append(
            {
                "name": "modern",
                "conn": open_database(
                    MODERN_DB_FILE
                ),
            }
        )

    return databases


def close_databases(databases):

    for database in databases:
        database["conn"].close()


def date_bounds(start_year, end_year):

    return (
        f"{start_year}-01-01",
        f"{end_year}-12-31"
    )


def add_stat(stats, row):

    player_id = row["player_id"]

    if player_id not in stats:

        stats[player_id] = {
            "player_id": player_id,
            "name": row["name"],
            "full_name": row["full_name"],
            "value": 0,
        }

    stats[player_id]["value"] += row["value"]


def combine_rows(rows):

    stats = {}

    for row in rows:
        add_stat(stats, row)

    return list(stats.values())


def rank_rows(rows):

    return sorted(
        rows,
        key=lambda row: (
            -row["value"],
            normalize_text(row["name"]),
            row["player_id"]
        )
    )


def build_answer_slots(rows):

    ranked = rank_rows(
        rows
    )

    if len(ranked) < ANSWER_COUNT:

        return {
            "playable": False,
            "reason": "Listen har færre enn 10 svar.",
            "slots": [],
            "eligible_answers": ranked,
            "cutoff_value": None,
        }

    cutoff_value = ranked[
        ANSWER_COUNT - 1
    ]["value"]

    above_cutoff = [
        row
        for row in ranked
        if row["value"] > cutoff_value
    ]

    cutoff_players = [
        row
        for row in ranked
        if row["value"] == cutoff_value
    ]

    slots = [
        {
            "value": row["value"],
            "players": [
                row
            ]
        }
        for row in above_cutoff
    ]

    remaining_slots = (
        ANSWER_COUNT
        - len(slots)
    )

    for _ in range(remaining_slots):

        slots.append(
            {
                "value": cutoff_value,
                "players": cutoff_players
            }
        )

    top_answers = (
        above_cutoff
        + cutoff_players
    )

    slots = slots[
        :ANSWER_COUNT
    ]

    return {
        "playable": True,
        "reason": None,
        "slots": slots,
        "eligible_answers": top_answers,
        "cutoff_value": cutoff_value,
    }


def build_top_ten(rows, theme_id):

    answer_data = build_answer_slots(
        rows
    )

    if not answer_data["playable"]:
        return answer_data

    minimum = MIN_CUTOFF_BY_THEME[
        theme_id
    ]

    if answer_data["cutoff_value"] < minimum:

        return {
            "playable": False,
            "reason": (
                "10.-plassen har for lav verdi "
                f"({answer_data['cutoff_value']} < {minimum})."
            ),
            "slots": answer_data["slots"],
            "eligible_answers": answer_data["eligible_answers"],
            "cutoff_value": answer_data["cutoff_value"],
        }

    return answer_data


def player_names(player):

    names = {
        normalize_text(
            player["name"]
        )
    }

    if player["full_name"]:

        names.add(
            normalize_text(
                player["full_name"]
            )
        )

    return {
        name
        for name in names
        if name
    }


# ============================================================
# SQL-SPØRRINGER
# ============================================================

def query_simple_theme(
    database,
    theme_id,
    start_year,
    end_year
):

    start_date, end_date = date_bounds(
        start_year,
        end_year
    )

    queries = {
        "kamper": """
            SELECT
                p.id AS player_id,
                p.name,
                p.full_name,
                COUNT(*) AS value

            FROM appearances a

            JOIN matches m
                ON m.id = a.match_id

            JOIN players p
                ON p.id = a.player_id

            WHERE
                a.team_id = ?
                AND a.appeared = 1
                AND m.date >= ?
                AND m.date <= ?

            GROUP BY
                p.id,
                p.name,
                p.full_name
        """,
        "starter": """
            SELECT
                p.id AS player_id,
                p.name,
                p.full_name,
                COUNT(*) AS value

            FROM appearances a

            JOIN matches m
                ON m.id = a.match_id

            JOIN players p
                ON p.id = a.player_id

            WHERE
                a.team_id = ?
                AND a.starting = 1
                AND m.date >= ?
                AND m.date <= ?

            GROUP BY
                p.id,
                p.name,
                p.full_name
        """,
        "innhopp": """
            SELECT
                p.id AS player_id,
                p.name,
                p.full_name,
                COUNT(*) AS value

            FROM appearances a

            JOIN matches m
                ON m.id = a.match_id

            JOIN players p
                ON p.id = a.player_id

            WHERE
                a.team_id = ?
                AND a.appeared = 1
                AND a.starting = 0
                AND m.date >= ?
                AND m.date <= ?

            GROUP BY
                p.id,
                p.name,
                p.full_name
        """,
        "maal": """
            SELECT
                p.id AS player_id,
                p.name,
                p.full_name,
                COUNT(*) AS value

            FROM events e

            JOIN matches m
                ON m.id = e.match_id

            JOIN players p
                ON p.id = e.scorer_id

            WHERE
                e.team_id = ?
                AND e.event_type IN (
                    'goal',
                    'penaltyGoal'
                )
                AND e.scorer_id IS NOT NULL
                AND m.date >= ?
                AND m.date <= ?

            GROUP BY
                p.id,
                p.name,
                p.full_name
        """,
        "utlendinger-kamper": """
            SELECT
                p.id AS player_id,
                p.name,
                p.full_name,
                COUNT(*) AS value

            FROM appearances a

            JOIN matches m
                ON m.id = a.match_id

            JOIN players p
                ON p.id = a.player_id

            WHERE
                a.team_id = ?
                AND a.appeared = 1
                AND p.country_code IS NOT NULL
                AND p.country_code != 'NO'
                AND m.date >= ?
                AND m.date <= ?

            GROUP BY
                p.id,
                p.name,
                p.full_name
        """,
        "utlendinger-maal": """
            SELECT
                p.id AS player_id,
                p.name,
                p.full_name,
                COUNT(*) AS value

            FROM events e

            JOIN matches m
                ON m.id = e.match_id

            JOIN players p
                ON p.id = e.scorer_id

            WHERE
                e.team_id = ?
                AND e.event_type IN (
                    'goal',
                    'penaltyGoal'
                )
                AND e.scorer_id IS NOT NULL
                AND p.country_code IS NOT NULL
                AND p.country_code != 'NO'
                AND m.date >= ?
                AND m.date <= ?

            GROUP BY
                p.id,
                p.name,
                p.full_name
        """,
        "seire": """
            SELECT
                p.id AS player_id,
                p.name,
                p.full_name,
                COUNT(*) AS value

            FROM appearances a

            JOIN matches m
                ON m.id = a.match_id

            JOIN players p
                ON p.id = a.player_id

            WHERE
                a.team_id = ?
                AND a.appeared = 1
                AND m.date >= ?
                AND m.date <= ?
                AND m.home_score IS NOT NULL
                AND m.away_score IS NOT NULL
                AND (
                    (
                        m.home_team_id = ?
                        AND m.home_score > m.away_score
                    )
                    OR (
                        m.away_team_id = ?
                        AND m.away_score > m.home_score
                    )
                )

            GROUP BY
                p.id,
                p.name,
                p.full_name
        """,
    }

    if theme_id == "seire":

        params = (
            BRANN_ID,
            start_date,
            end_date,
            BRANN_ID,
            BRANN_ID
        )

    else:

        params = (
            BRANN_ID,
            start_date,
            end_date
        )

    return database["conn"].execute(
        queries[theme_id],
        params
    ).fetchall()


def query_opponent_theme(
    database,
    theme_id,
    opponent_id,
    start_year,
    end_year
):

    start_date, end_date = date_bounds(
        start_year,
        end_year
    )

    if theme_id == "kamper-mot":

        sql = """
            SELECT
                p.id AS player_id,
                p.name,
                p.full_name,
                COUNT(*) AS value

            FROM appearances a

            JOIN matches m
                ON m.id = a.match_id

            JOIN players p
                ON p.id = a.player_id

            WHERE
                a.team_id = ?
                AND a.appeared = 1
                AND m.date >= ?
                AND m.date <= ?
                AND (
                    m.home_team_id = ?
                    OR m.away_team_id = ?
                )
                AND (
                    m.home_team_id = ?
                    OR m.away_team_id = ?
                )

            GROUP BY
                p.id,
                p.name,
                p.full_name
        """

        params = (
            BRANN_ID,
            start_date,
            end_date,
            BRANN_ID,
            BRANN_ID,
            opponent_id,
            opponent_id
        )

    else:

        sql = """
            SELECT
                p.id AS player_id,
                p.name,
                p.full_name,
                COUNT(*) AS value

            FROM events e

            JOIN matches m
                ON m.id = e.match_id

            JOIN players p
                ON p.id = e.scorer_id

            WHERE
                e.team_id = ?
                AND e.event_type IN (
                    'goal',
                    'penaltyGoal'
                )
                AND e.scorer_id IS NOT NULL
                AND m.date >= ?
                AND m.date <= ?
                AND (
                    m.home_team_id = ?
                    OR m.away_team_id = ?
                )
                AND (
                    m.home_team_id = ?
                    OR m.away_team_id = ?
                )

            GROUP BY
                p.id,
                p.name,
                p.full_name
        """

        params = (
            BRANN_ID,
            start_date,
            end_date,
            BRANN_ID,
            BRANN_ID,
            opponent_id,
            opponent_id
        )

    return database["conn"].execute(
        sql,
        params
    ).fetchall()


def query_opponents(
    database,
    start_year,
    end_year
):

    start_date, end_date = date_bounds(
        start_year,
        end_year
    )

    return database["conn"].execute(
        """
        SELECT DISTINCT
            t.id,
            t.name,
            t.slug

        FROM matches m

        JOIN teams t
            ON (
                (
                    m.home_team_id = ?
                    AND t.id = m.away_team_id
                )
                OR (
                    m.away_team_id = ?
                    AND t.id = m.home_team_id
                )
            )

        WHERE
            m.date >= ?
            AND m.date <= ?

        ORDER BY
            t.name
        """,
        (
            BRANN_ID,
            BRANN_ID,
            start_date,
            end_date
        )
    ).fetchall()


# ============================================================
# OPPGAVEBYGGING
# ============================================================

def find_opponents(
    databases,
    start_year,
    end_year
):

    opponents = {}

    for database in databases:

        for row in query_opponents(
            database,
            start_year,
            end_year
        ):

            opponents[row["id"]] = {
                "id": row["id"],
                "name": row["name"],
                "slug": row["slug"],
            }

    return sorted(
        opponents.values(),
        key=lambda opponent: normalize_text(
            opponent["name"]
        )
    )


def find_opponent(
    databases,
    search_text,
    start_year,
    end_year
):

    wanted = normalize_text(
        search_text
    )

    matches = []

    for opponent in find_opponents(
        databases,
        start_year,
        end_year
    ):

        names = {
            normalize_text(
                opponent["name"]
            ),
            normalize_text(
                opponent["slug"]
            ),
        }

        if wanted in names:
            return opponent

        if any(
            wanted in name
            for name in names
        ):
            matches.append(opponent)

    if len(matches) == 1:
        return matches[0]

    if matches:

        names = ", ".join(
            opponent["name"]
            for opponent in matches[:8]
        )

        raise ValueError(
            "Motstander er ikke entydig. "
            f"Mulige treff: {names}"
        )

    raise ValueError(
        f"Fant ikke motstander: {search_text}"
    )


def build_question(
    databases,
    theme_id,
    start_year,
    end_year,
    opponent=None
):

    theme = THEMES[theme_id]
    rows = []

    for database in databases:

        if theme["kind"] == "simple":

            rows.extend(
                query_simple_theme(
                    database,
                    theme_id,
                    start_year,
                    end_year
                )
            )

        else:

            rows.extend(
                query_opponent_theme(
                    database,
                    theme_id,
                    opponent["id"],
                    start_year,
                    end_year
                )
            )

    top_ten = build_top_ten(
        combine_rows(
            rows
        ),
        theme_id
    )

    title = theme["title"]
    description = theme["description"]

    if opponent:

        title = title.format(
            opponent=opponent["name"]
        )
        description = description.format(
            opponent=opponent["name"]
        )

    return {
        "theme_id": theme_id,
        "title": title,
        "description": description,
        "metric": theme["metric"],
        "start_year": start_year,
        "end_year": end_year,
        "opponent": opponent,
        "playable": top_ten["playable"],
        "reason": top_ten["reason"],
        "slots": top_ten["slots"],
        "eligible_answers": top_ten["eligible_answers"],
        "cutoff_value": top_ten["cutoff_value"],
    }


def get_playable_questions(
    databases,
    start_year,
    end_year
):

    questions = []

    for theme_id, theme in THEMES.items():

        if theme["kind"] != "simple":
            continue

        question = build_question(
            databases,
            theme_id,
            start_year,
            end_year
        )

        if question["playable"]:
            questions.append(question)

    opponents = find_opponents(
        databases,
        start_year,
        end_year
    )

    for theme_id, theme in THEMES.items():

        if theme["kind"] != "opponent":
            continue

        for opponent in opponents:

            question = build_question(
                databases,
                theme_id,
                start_year,
                end_year,
                opponent
            )

            if question["playable"]:
                questions.append(question)

    return questions


# ============================================================
# SVAR OG SPILL
# ============================================================

def get_slot_results(
    question,
    guessed_ids
):

    used_ids = set()
    results = []

    for slot in question["slots"]:

        guessed_player = None
        players_by_id = {
            player["player_id"]: player
            for player in slot["players"]
        }

        for player_id in guessed_ids:

            if (
                player_id in players_by_id
                and player_id not in used_ids
            ):

                guessed_player = players_by_id[
                    player_id
                ]
                used_ids.add(
                    player_id
                )
                break

        results.append(
            {
                "slot": slot,
                "player": guessed_player
            }
        )

    return results


def count_solved_slots(
    question,
    guessed_ids
):

    return sum(
        1
        for result in get_slot_results(
            question,
            guessed_ids
        )
        if result["player"] is not None
    )


def match_answer(
    answer,
    question,
    guessed_ids
):

    wanted = normalize_text(
        answer
    )

    if not wanted:

        return {
            "status": "empty"
        }

    matches = []

    for player in question["eligible_answers"]:

        names = player_names(
            player
        )

        if wanted in names:

            matches = [
                player
            ]
            break

        if len(wanted) >= 3 and any(
            wanted in name
            for name in names
        ):

            matches.append(
                player
            )

    unique = {
        player["player_id"]: player
        for player in matches
    }

    if len(unique) != 1:

        return {
            "status": "wrong"
        }

    player = next(
        iter(unique.values())
    )

    if player["player_id"] in guessed_ids:

        return {
            "status": "duplicate",
            "player": player
        }

    return {
        "status": "correct",
        "player": player
    }


def print_board(
    question,
    guessed_ids,
    mistakes
):

    print()
    print("=" * 72)
    print(question["title"].upper())
    print("=" * 72)
    print(question["description"])
    print(
        f"År: {question['start_year']}-"
        f"{question['end_year']} | "
        f"Liv igjen: {STARTING_LIVES - mistakes}"
    )
    print()

    for index, result in enumerate(
        get_slot_results(
            question,
            guessed_ids
        ),
        start=1
    ):

        slot = result["slot"]
        player = result["player"]

        if player:

            print(
                f"{index:>2}. "
                f"{player['name']:<28} "
                f"{slot['value']:>4} "
                f"{question['metric']}"
            )

        else:

            print(
                f"{index:>2}. "
                "____________________________ "
                f"{slot['value']:>4} "
                f"{question['metric']}"
            )

    print()
    print('Skriv "q" for å avslutte.')


def print_result(
    question,
    guessed_ids,
    mistakes
):

    correct = count_solved_slots(
        question,
        guessed_ids
    )

    print()
    print("=" * 72)
    print(
        f"RESULTAT: {correct}/{ANSWER_COUNT}"
    )
    print(
        f"FEIL: {mistakes}/{STARTING_LIVES}"
    )
    print("=" * 72)

    revealed_ids = set()

    for index, result in enumerate(
        get_slot_results(
            question,
            guessed_ids
        ),
        start=1
    ):

        slot = result["slot"]
        player = result["player"]

        if player:
            marker = "x"
            revealed_ids.add(
                player["player_id"]
            )

        else:

            player = next(
                (
                    candidate
                    for candidate in slot["players"]
                    if candidate["player_id"]
                    not in revealed_ids
                ),
                slot["players"][0]
            )
            revealed_ids.add(
                player["player_id"]
            )
            marker = " "

        print(
            f"{marker} {index:>2}. "
            f"{player['name']:<28} "
            f"{slot['value']:>4} "
            f"{question['metric']}"
        )

        if (
            index == ANSWER_COUNT
            and len(slot["players"]) > 1
        ):

            alternatives = [
                player["name"]
                for player in slot["players"]
            ]

            print(
                "      Delt cutoff-gruppe: "
                + ", ".join(alternatives)
            )


def play_question(question):

    guessed_ids = []
    mistakes = 0

    while True:

        print_board(
            question,
            guessed_ids,
            mistakes
        )

        solved_slots = count_solved_slots(
            question,
            guessed_ids
        )

        if solved_slots == ANSWER_COUNT:

            print_result(
                question,
                guessed_ids,
                mistakes
            )
            return

        answer = input(
            "Svar: "
        ).strip()

        if normalize_text(answer) in {
            "q",
            "quit",
            "avslutt"
        }:

            print_result(
                question,
                guessed_ids,
                mistakes
            )
            return

        result = match_answer(
            answer,
            question,
            guessed_ids
        )

        status = result["status"]

        if status == "empty":
            continue

        if status == "correct":

            player = result["player"]
            guessed_ids.append(
                player["player_id"]
            )
            print(
                f"RIKTIG: {player['name']} "
                f"({player['value']} "
                f"{question['metric']})"
            )
            continue

        if status == "duplicate":

            print(
                f"Allerede tatt: "
                f"{result['player']['name']}."
            )
            continue

        mistakes += 1

        if mistakes >= STARTING_LIVES:

            print(
                "Tredje feil. Spillet er over."
            )
            print_result(
                question,
                guessed_ids,
                mistakes
            )
            return

        print(
            f"FEIL. Liv igjen: "
            f"{STARTING_LIVES - mistakes}"
        )


# ============================================================
# KOMMANDOLINJE
# ============================================================

def list_themes():

    print("Tilgjengelige Tenable-temaer:")

    for theme_id, theme in THEMES.items():

        if theme["kind"] == "opponent":

            print(
                f"- {theme_id} "
                "(krever --opponent)"
            )

        else:

            print(
                f"- {theme_id}"
            )


def list_questions(
    databases,
    start_year,
    end_year
):

    questions = get_playable_questions(
        databases,
        start_year,
        end_year
    )

    print(
        f"Spillbare Tenable-oppgaver "
        f"{start_year}-{end_year}: "
        f"{len(questions)}"
    )

    for question in questions:

        print(
            f"- {question['theme_id']}: "
            f"{question['title']} "
            f"(10.-plass: "
            f"{question['cutoff_value']} "
            f"{question['metric']})"
        )


def parse_args():

    parser = argparse.ArgumentParser(
        description="Tenable-prototype for Brannspillet."
    )

    parser.add_argument(
        "--theme",
        choices=sorted(THEMES),
        help="Velg tema. Uten tema trekkes en tilfeldig spillbar oppgave."
    )

    parser.add_argument(
        "--opponent",
        help=(
            "Motstander for temaene "
            "kamper-mot og maal-mot."
        )
    )

    parser.add_argument(
        "--start-year",
        type=int,
        default=DEFAULT_START_YEAR,
        help=(
            "Startår. Standard er "
            f"{DEFAULT_START_YEAR}."
        )
    )

    parser.add_argument(
        "--end-year",
        type=int,
        default=MAX_YEAR,
        help=(
            "Sluttår. Standard er "
            f"{MAX_YEAR}."
        )
    )

    parser.add_argument(
        "--list-themes",
        action="store_true",
        help="Vis tilgjengelige temaer og avslutt."
    )

    parser.add_argument(
        "--list-opponents",
        action="store_true",
        help="Vis motstandere i valgt tidsrom og avslutt."
    )

    parser.add_argument(
        "--list-questions",
        action="store_true",
        help="Vis spillbare oppgaver i valgt tidsrom og avslutt."
    )

    parser.add_argument(
        "--seed",
        type=int,
        help="Fast random-seed for testing."
    )

    return parser.parse_args()


def main():

    args = parse_args()

    if args.list_themes:

        list_themes()
        return

    try:

        start_year = parse_year(
            args.start_year,
            "Startår"
        )
        end_year = parse_year(
            args.end_year,
            "Sluttår"
        )

        if start_year > end_year:

            raise ValueError(
                "Startår kan ikke være etter sluttår."
            )

    except ValueError as error:

        print(error)
        return

    databases = connect_databases(
        start_year,
        end_year
    )

    try:

        if args.list_opponents:

            for opponent in find_opponents(
                databases,
                start_year,
                end_year
            ):

                print(
                    opponent["name"]
                )

            return

        if args.list_questions:

            list_questions(
                databases,
                start_year,
                end_year
            )
            return

        opponent = None

        if args.theme and THEMES[args.theme]["kind"] == "opponent":

            if not args.opponent:

                print(
                    "Dette temaet krever "
                    "--opponent."
                )
                return

            opponent = find_opponent(
                databases,
                args.opponent,
                start_year,
                end_year
            )

        if args.theme:

            question = build_question(
                databases,
                args.theme,
                start_year,
                end_year,
                opponent
            )

            if not question["playable"]:

                print(
                    "Oppgaven er ikke spillbar: "
                    f"{question['reason']}"
                )
                return

        else:

            rng = random.Random(
                args.seed
            )

            questions = get_playable_questions(
                databases,
                start_year,
                end_year
            )

            if not questions:

                print(
                    "Fant ingen spillbare "
                    "Tenable-oppgaver i tidsrommet."
                )
                return

            question = rng.choice(
                questions
            )

        play_question(
            question
        )

    finally:

        close_databases(
            databases
        )


if __name__ == "__main__":
    main()
