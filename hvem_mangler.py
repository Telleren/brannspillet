import argparse
import hashlib
import json
import random
import sqlite3
import unicodedata
from datetime import date
from pathlib import Path


# ============================================================
# INNSTILLINGER
# ============================================================

DB_FILE = Path("data/brannspillet_v2.db")
HISTORICAL_DB_FILE = Path(
    "data/brannspillet_historical_sandbox.db"
)

SHIRT_ENRICHMENTS_FILE = Path(
    "data/shirt_number_enrichments.json"
)

BRANN_ID = "05bb57f9-3430-5a18-b77c-96b578525b9c"

MIN_YEAR = 1963
MAX_YEAR = 2026
STARTING_LIVES = 3
HIDDEN_POOL_SIZE = 5


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


def daily_seed(day_string):

    text = (
        f"hvem-mangler-v1|{day_string}"
    )

    digest = hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()

    return int(
        digest[:16],
        16
    )


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
                "path": HISTORICAL_DB_FILE,
                "conn": open_database(
                    HISTORICAL_DB_FILE
                ),
            }
        )

    if end_year >= 2000:

        databases.append(
            {
                "name": "modern",
                "path": DB_FILE,
                "conn": open_database(
                    DB_FILE
                ),
            }
        )

    return databases


def close_databases(databases):

    for database in databases:
        database["conn"].close()


def connect_database():

    return open_database(DB_FILE)


# ============================================================
# LAST DRAKTNUMMER-BERIKELSER
# ============================================================

def load_shirt_enrichments():

    if not SHIRT_ENRICHMENTS_FILE.exists():

        print(
            "MERK: Fant ikke "
            f"{SHIRT_ENRICHMENTS_FILE}."
        )

        print(
            "Spillet fortsetter uten "
            "manuelle draktnummer-berikelser."
        )

        return []


    with SHIRT_ENRICHMENTS_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)


    rules = data.get(
        "rules",
        []
    )


    return rules


# ============================================================
# FINN AKTUELLE KAMPER
# ============================================================

def get_candidate_matches(
    database,
    start_year,
    end_year
):

    start_date = f"{start_year}-01-01"
    end_date = f"{end_year}-12-31"

    rows = database["conn"].execute(
        """
        SELECT
            m.id,
            m.date,
            m.score,

            ht.name AS home_team,
            at.name AS away_team,

            c.name AS competition

        FROM matches m

        JOIN teams ht
            ON ht.id = m.home_team_id

        JOIN teams at
            ON at.id = m.away_team_id

        LEFT JOIN competitions c
            ON c.id = m.competition_id

        JOIN appearances a
            ON a.match_id = m.id
            AND a.team_id = ?
            AND a.starting = 1

        WHERE
            m.date >= ?
            AND m.date <= ?

        GROUP BY
            m.id

        HAVING
            COUNT(a.player_id) = 11

        ORDER BY
            m.date
        """,
        (
            BRANN_ID,
            start_date,
            end_date
        )
    ).fetchall()

    matches = []

    for row in rows:

        match = dict(row)
        match["database"] = database["name"]

        matches.append(match)


    return matches


def get_all_candidate_matches(
    databases,
    start_year,
    end_year
):

    matches = []

    for database in databases:

        matches.extend(
            get_candidate_matches(
                database,
                start_year,
                end_year
            )
        )


    return matches


# ============================================================
# HENT STARTELLEVER
# ============================================================

def get_starting_eleven(
    database,
    match_id
):

    rows = database["conn"].execute(
        """
        SELECT
            p.id,
            p.name,
            p.full_name,

            a.shirt_number,
            a.squad_index,
            a.role_abbr,
            a.role_sort

        FROM appearances a

        JOIN players p
            ON p.id = a.player_id

        WHERE
            a.match_id = ?
            AND a.team_id = ?
            AND a.starting = 1

        ORDER BY
            a.squad_index IS NULL,
            a.squad_index,
            p.name
        """,
        (
            match_id,
            BRANN_ID
        )
    ).fetchall()

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# VERIFISERT DRAKTNUMMER-BERIKELSE
# ============================================================

def get_enriched_shirt_number(
    enrichments,
    player_name,
    match_date
):

    wanted_name = normalize_text(
        player_name
    )


    matches = []


    for rule in enrichments:

        rule_name = normalize_text(
            rule.get("player_name")
        )


        if rule_name != wanted_name:
            continue


        from_date = rule.get(
            "from_date"
        )

        to_date = rule.get(
            "to_date"
        )


        if not from_date or not to_date:
            continue


        if (
            from_date
            <= match_date
            <= to_date
        ):

            shirt_number = rule.get(
                "shirt_number"
            )


            if shirt_number is not None:

                matches.append(
                    shirt_number
                )


    unique_numbers = set(
        matches
    )


    # En kamp skal aldri matche to regler
    # som sier forskjellige ting.
    #
    # Hvis det skulle skje, bruker vi
    # ingen av dem fremfor å gjette.

    if len(unique_numbers) == 1:

        return next(
            iter(unique_numbers)
        )


    return None


# ============================================================
# AUTOMATISK SESONG-INFERENS AV DRAKTNUMMER
# ============================================================

def infer_shirt_number(
    database,
    player_id,
    match_id
):

    conn = database["conn"]

    match = conn.execute(
        """
        SELECT
            season_name

        FROM matches

        WHERE
            id = ?
        """,
        (match_id,)
    ).fetchone()


    if not match:
        return None


    season_name = match[
        "season_name"
    ]


    if not season_name:
        return None


    rows = conn.execute(
        """
        SELECT DISTINCT
            a.shirt_number

        FROM appearances a

        JOIN matches m
            ON m.id = a.match_id

        WHERE
            a.team_id = ?
            AND a.player_id = ?
            AND m.season_name = ?
            AND a.shirt_number IS NOT NULL
        """,
        (
            BRANN_ID,
            player_id,
            season_name
        )
    ).fetchall()


    numbers = {
        row["shirt_number"]
        for row in rows
    }


    # Bare bruk nummeret dersom spilleren
    # har nøyaktig ett kjent draktnummer
    # i denne sesongen.

    if len(numbers) == 1:

        return next(
            iter(numbers)
        )


    return None


# ============================================================
# FINN DRAKTNUMMER
# ============================================================

def get_display_shirt_number(
    database,
    enrichments,
    player,
    match
):

    # --------------------------------------------------------
    # 1. Nummer fra akkurat denne kampen
    # --------------------------------------------------------

    shirt = player[
        "shirt_number"
    ]


    if shirt is not None:

        return shirt


    # --------------------------------------------------------
    # 2. Manuelt verifisert enrichment
    # --------------------------------------------------------

    shirt = get_enriched_shirt_number(
        enrichments,
        player["name"],
        match["date"]
    )


    if shirt is not None:

        return shirt


    # --------------------------------------------------------
    # 3. Automatisk inferens fra samme sesong
    # --------------------------------------------------------

    shirt = infer_shirt_number(
        database,
        player["id"],
        match["id"]
    )


    if shirt is not None:

        return shirt


    # --------------------------------------------------------
    # 4. Fremdeles ukjent
    # --------------------------------------------------------

    return None


# ============================================================
# VELG FEM DAGENS KAMPER
# ============================================================

def select_rounds(
    conn,
    rng
):

    selected = []

    used_matches = set()


    for start_date, end_date in DIFFICULTY_TIERS:

        candidates = get_candidate_matches(
            conn,
            start_date,
            end_date
        )


        candidates = [
            match

            for match in candidates

            if match["id"]
            not in used_matches
        ]


        if not candidates:

            raise RuntimeError(
                "Fant ingen gyldige kamper "
                f"mellom {start_date} "
                f"og {end_date}."
            )


        match = rng.choice(
            candidates
        )


        starters = get_starting_eleven(
            conn,
            match["id"]
        )


        if len(starters) != 11:

            raise RuntimeError(
                f"Kamp {match['id']} "
                "har ikke 11 startere."
            )


        possible_hidden = [
            player

            for player in starters

            if normalize_text(
                player["name"]
            )
            not in {
                "ukjent",
                "ukjent ukjent"
            }
        ]


        if not possible_hidden:

            raise RuntimeError(
                f"Kamp {match['id']} "
                "har ingen gyldig spiller "
                "å skjule."
            )


        hidden = rng.choice(
            possible_hidden
        )


        selected.append(
            {
                "match": match,
                "starters": starters,
                "hidden": hidden
            }
        )


        used_matches.add(
            match["id"]
        )


    return selected


# ============================================================
# NY STREAK-LOGIKK
# ============================================================

def is_known_player(player):

    return (
        normalize_text(player["name"])
        not in {
            "ukjent",
            "ukjent ukjent"
        }
    )


def count_brann_appearances_in_year(
    database,
    player_id,
    year
):

    return database["conn"].execute(
        """
        SELECT COUNT(*)

        FROM appearances a

        JOIN matches m
            ON m.id = a.match_id

        WHERE
            a.team_id = ?
            AND a.player_id = ?
            AND a.appeared = 1
            AND m.date >= ?
            AND m.date <= ?
        """,
        (
            BRANN_ID,
            player_id,
            f"{year}-01-01",
            f"{year}-12-31"
        )
    ).fetchone()[0]


def choose_hidden_player(
    database,
    match,
    starters,
    rng
):

    year = int(
        match["date"][:4]
    )

    possible_hidden = [
        player
        for player in starters
        if is_known_player(player)
    ]


    if not possible_hidden:

        raise RuntimeError(
            f"Kamp {match['id']} "
            "har ingen gyldig spiller "
            "å skjule."
        )


    ranked = []

    for player in possible_hidden:

        appearances = count_brann_appearances_in_year(
            database,
            player["id"],
            year
        )

        ranked.append(
            (
                appearances,
                normalize_text(
                    player["name"]
                ),
                player["id"],
                player
            )
        )


    ranked.sort()

    hidden_pool = [
        item[3]
        for item in ranked[
            :HIDDEN_POOL_SIZE
        ]
    ]

    return rng.choice(
        hidden_pool
    )


def select_round(
    databases,
    candidates,
    rng,
    used_matches
):

    available = [
        match
        for match in candidates
        if (
            match["database"],
            match["id"]
        ) not in used_matches
    ]


    if not available:
        return None


    match = rng.choice(available)

    database = next(
        item
        for item in databases
        if item["name"] == match["database"]
    )

    starters = get_starting_eleven(
        database,
        match["id"]
    )

    if len(starters) != 11:

        raise RuntimeError(
            f"Kamp {match['id']} "
            "har ikke 11 startere."
        )


    hidden = choose_hidden_player(
        database,
        match,
        starters,
        rng
    )

    used_matches.add(
        (
            match["database"],
            match["id"]
        )
    )

    return {
        "database": database,
        "match": match,
        "starters": starters,
        "hidden": hidden
    }


def select_rounds(*args, **kwargs):

    raise RuntimeError(
        "Gammel femrunderslogikk er erstattet "
        "av streak mode."
    )


# ============================================================
# POSISJONSGRUPPER
# ============================================================

def role_group(role_abbr):

    if role_abbr == "gk":

        return "KEEPER"


    if role_abbr == "def":

        return "FORSVAR"


    if role_abbr in {
        "d-m",
        "mid",
        "m-a"
    }:

        return "MIDTBANE"


    if role_abbr == "att":

        return "ANGREP"


    return "ØVRIGE"


GROUP_ORDER = [
    "KEEPER",
    "FORSVAR",
    "MIDTBANE",
    "ANGREP",
    "ØVRIGE"
]


# ============================================================
# VIS STARTELLEVER
# ============================================================

def print_visible_lineup(
    database,
    enrichments,
    match,
    starters,
    hidden_id
):

    groups = {
        group: []

        for group in GROUP_ORDER
    }


    # starters er allerede hentet i Branntalls
    # originale squad-rekkefølge.
    #
    # Vi sorterer derfor ikke på draktnummer.
    #
    # Dermed beholdes den naturlige
    # oppstillingsrekkefølgen:
    #
    # høyreback
    # midtstopper
    # midtstopper
    # venstreback
    #
    # osv.

    for player in starters:

        group = role_group(
            player["role_abbr"]
        )


        if player["id"] == hidden_id:

            groups[group].append(
                {
                    "kind": "hidden"
                }
            )

        else:

            groups[group].append(
                {
                    "kind": "player",
                    "player": player
                }
            )


    for group in GROUP_ORDER:

        players = groups[
            group
        ]


        if not players:
            continue


        print()
        print(group)


        for item in players:

            if item["kind"] == "hidden":

                print(
                    "  --  --- MANGLER ---"
                )

                continue


            player = item["player"]

            shirt = get_display_shirt_number(
                database,
                enrichments,
                player,
                match
            )


            if shirt is None:

                shirt_text = "?"

            else:

                shirt_text = str(
                    shirt
                )


            print(
                f"  {shirt_text:>2}  "
                f"{player['name']}"
            )


# ============================================================
# SVARKONTROLL
# ============================================================

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


def is_correct_answer(
    answer,
    hidden,
    starters
):

    wanted = normalize_text(
        answer
    )


    if not wanted:

        return False


    hidden_names = player_names(
        hidden
    )


    # Fullt registrert navn.

    if wanted in hidden_names:

        return True


    # Tillat for eksempel:
    #
    # finne
    # huseklepp
    # pallesen
    # horn myhre
    #
    # men bare dersom teksten peker
    # entydig på den skjulte spilleren
    # blant de elleve starterne.

    if len(wanted) < 3:

        return False


    matches = []


    for player in starters:

        names = player_names(
            player
        )


        if any(
            wanted in name

            for name in names
        ):

            matches.append(
                player["id"]
            )


    unique_matches = set(
        matches
    )


    return (
        unique_matches
        == {
            hidden["id"]
        }
    )


# ============================================================
# KAMPTEKST
# ============================================================

def describe_match(match):

    competition = (
        match["competition"]
        or "Ukjent turnering"
    )


    return (
        f"{match['date']} | "
        f"{competition}\n"

        f"{match['home_team']}–"
        f"{match['away_team']} "
        f"{match['score']}"
    )


# ============================================================
# SPILL ÉN RUNDE
# ============================================================

def play_round(
    enrichments,
    number,
    round_data,
    score=None,
    lives_left=None
):

    database = round_data[
        "database"
    ]

    match = round_data[
        "match"
    ]

    starters = round_data[
        "starters"
    ]

    hidden = round_data[
        "hidden"
    ]


    print()
    print("=" * 72)


    print(
        f"OPPGAVE {number}"
    )


    print("=" * 72)

    print()

    if score is not None and lives_left is not None:

        print(
            f"Streak: {score} | "
            f"Liv igjen: {lives_left}"
        )

        print()


    print(
        describe_match(
            match
        )
    )


    print()


    print(
        "Én spiller mangler fra "
        "Branns startellever:"
    )


    print_visible_lineup(
        database,
        enrichments,
        match,
        starters,
        hidden["id"]
    )


    print()
    print("-" * 72)


    while True:

        answer = input(
            "Hvem mangler? "
        ).strip()


        if normalize_text(
            answer
        ) in {
            "q",
            "quit",
            "exit",
            "avslutt"
        }:

            return None


        if not answer:
            continue


        break


    correct = is_correct_answer(
        answer,
        hidden,
        starters
    )


    print()


    if correct:

        print(
            f"RIKTIG! "
            f"{hidden['name']}."
        )

    else:

        print(
            f"FEIL. "
            f"Riktig svar var "
            f"{hidden['name']}."
        )


    return correct


# ============================================================
# RESULTAT
# ============================================================

def print_result(
    score,
    mistakes=None
):

    print()
    print("=" * 72)


    print(
        f"STREAK: {score}"
    )

    if mistakes is not None:

        print(
            f"FEIL: {mistakes}/{STARTING_LIVES}"
        )


    print("=" * 72)


    if score == 0:

        print(
            "Streaken stoppet før "
            "den kom i gang."
        )

        return


    if score == 1:

        print(
            "Én riktig."
        )

        return


    if score < 5:

        print(
            f"{score} riktige."
        )

        return


    if score < 10:

        print(
            f"{score} riktige. Solid."
        )

        return


    print(
        f"{score} riktige. Sterkt."
    )

    return


    if score == 5:

        print(
            "Full pott."
        )


    elif score == 4:

        print(
            "Svært sterkt."
        )


    elif score == 3:

        print(
            "Godkjent Brann-kunnskap."
        )


    elif score == 2:

        print(
            "To riktige."
        )


    elif score == 1:

        print(
            "Én riktig."
        )


    else:

        print(
            "Null av fem."
        )


# ============================================================
# HOVEDPROGRAM
# ============================================================

def parse_year(value, label):

    try:
        year = int(value)

    except (TypeError, ValueError):
        raise ValueError(
            f"{label} må være et årstall."
        )


    if year < MIN_YEAR or year > MAX_YEAR:

        raise ValueError(
            f"{label} må være mellom "
            f"{MIN_YEAR} og {MAX_YEAR}."
        )


    return year


def ask_year(label, default_year):

    while True:

        answer = input(
            f"{label} [{default_year}]: "
        ).strip()

        if not answer:
            return default_year

        if normalize_text(answer) in {
            "q",
            "quit",
            "exit",
            "avslutt"
        }:

            return None

        try:
            return parse_year(
                answer,
                label
            )

        except ValueError as error:
            print(error)


def get_year_range(args):

    if args.start_year is not None:

        start_year = parse_year(
            args.start_year,
            "Startår"
        )

    else:

        start_year = ask_year(
            "Startår",
            MIN_YEAR
        )


    if start_year is None:
        return None


    if args.end_year is not None:

        end_year = parse_year(
            args.end_year,
            "Sluttår"
        )

    else:

        end_year = ask_year(
            "Sluttår",
            MAX_YEAR
        )


    if end_year is None:
        return None


    if start_year > end_year:

        raise ValueError(
            "Startår kan ikke være "
            "etter sluttår."
        )


    return start_year, end_year


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Hvem mangler? – "
            "Brannspillet"
        )
    )


    parser.add_argument(
        "--random",
        action="store_true",
        help=(
            "Bruk tilfeldig seed. "
            "Dette er standard nå."
        )
    )


    parser.add_argument(
        "--date",
        help=(
            "Bruk en bestemt dato "
            "som seed for test/replay, "
            "f.eks. 2026-08-26."
        )
    )


    parser.add_argument(
        "--start-year",
        help=(
            "Startår for kampene, "
            f"{MIN_YEAR}-{MAX_YEAR}."
        )
    )


    parser.add_argument(
        "--end-year",
        help=(
            "Sluttår for kampene, "
            f"{MIN_YEAR}-{MAX_YEAR}."
        )
    )


    args = parser.parse_args()


    conn = connect_database()


    enrichments = (
        load_shirt_enrichments()
    )


    if args.random:

        rng = random.Random()

        puzzle_label = (
            "Tilfeldig spill"
        )


    else:

        day_string = (
            args.date
            or date.today().isoformat()
        )


        rng = random.Random(
            daily_seed(
                day_string
            )
        )


        puzzle_label = (
            f"Dagens spill – "
            f"{day_string}"
        )


    rounds = select_rounds(
        conn,
        rng
    )


    print()
    print("=" * 72)


    print(
        "HVEM MANGLER?"
    )


    print("=" * 72)

    print()


    print(
        puzzle_label
    )


    print()


    print(
        "Fem Brann-startellevere. "
        "Én spiller er fjernet fra hver."
    )


    print(
        "Rundene går grovt fra nyere "
        "til eldre kamper."
    )


    print(
        'Skriv "q" for å avslutte.'
    )


    score = 0


    for number, round_data in enumerate(
        rounds,
        start=1
    ):

        result = play_round(
            conn,
            enrichments,
            number,
            round_data
        )


        if result is None:

            print()
            print(
                "Spillet ble avsluttet."
            )

            conn.close()

            return


        if result:

            score += 1


    print_result(
        score
    )


    conn.close()


def main_streak():

    parser = argparse.ArgumentParser(
        description=(
            "Hvem mangler? - "
            "Brannspillet"
        )
    )

    parser.add_argument(
        "--random",
        action="store_true",
        help=(
            "Bruk tilfeldig seed. "
            "Dette er standard nå."
        )
    )

    parser.add_argument(
        "--date",
        help=(
            "Bruk en bestemt dato "
            "som seed for test/replay, "
            "f.eks. 2026-08-26."
        )
    )

    parser.add_argument(
        "--start-year",
        help=(
            "Startår for kampene, "
            f"{MIN_YEAR}-{MAX_YEAR}."
        )
    )

    parser.add_argument(
        "--end-year",
        help=(
            "Sluttår for kampene, "
            f"{MIN_YEAR}-{MAX_YEAR}."
        )
    )

    args = parser.parse_args()

    print()
    print("=" * 72)
    print("HVEM MANGLER?")
    print("=" * 72)
    print()
    print(
        "Velg hvilke år du vil "
        "få lagoppstillinger fra."
    )
    print(
        f"Tilgjengelig spenn: "
        f"{MIN_YEAR}-{MAX_YEAR}."
    )
    print()

    try:

        year_range = get_year_range(args)

    except ValueError as error:

        print(error)
        return

    if year_range is None:
        print("Spillet ble avsluttet.")
        return

    start_year, end_year = year_range

    databases = connect_databases(
        start_year,
        end_year
    )

    try:

        enrichments = (
            load_shirt_enrichments()
        )

        candidates = get_all_candidate_matches(
            databases,
            start_year,
            end_year
        )

        if not candidates:

            raise RuntimeError(
                "Fant ingen gyldige kamper "
                f"mellom {start_year} og "
                f"{end_year}."
            )


        if args.date:

            rng = random.Random(
                daily_seed(args.date)
            )

            puzzle_label = (
                f"Testspill - {args.date}"
            )

        else:

            rng = random.Random()

            puzzle_label = (
                "Tilfeldig streak"
            )


        print()
        print(puzzle_label)
        print(
            f"Årsintervall: "
            f"{start_year}-{end_year}"
        )
        print(
            f"Gyldige lagoppstillinger: "
            f"{len(candidates)}"
        )
        print()
        print(
            "Du har tre liv. "
            "Tredje feil avslutter streaken."
        )
        print(
            'Skriv "q" for å avslutte.'
        )

        score = 0
        mistakes = 0
        attempts = 0
        used_matches = set()

        while True:

            round_data = select_round(
                databases,
                candidates,
                rng,
                used_matches
            )

            if round_data is None:

                print()
                print(
                    "Ingen flere gyldige "
                    "lagoppstillinger i utvalget."
                )
                print_result(
                    score,
                    mistakes
                )
                return


            attempts += 1

            result = play_round(
                enrichments,
                attempts,
                round_data,
                score,
                STARTING_LIVES - mistakes
            )

            if result is None:

                print()
                print(
                    "Spillet ble avsluttet."
                )
                print_result(
                    score,
                    mistakes
                )
                return


            if not result:

                mistakes += 1

                lives_left = (
                    STARTING_LIVES
                    - mistakes
                )

                if lives_left <= 0:

                    print()
                    print(
                        "Tredje feil. "
                        "Streaken er over."
                    )
                    print_result(
                        score,
                        mistakes
                    )
                    return


                print()
                print(
                    f"Liv igjen: {lives_left}"
                )
                continue


            score += 1

    finally:

        close_databases(databases)


if __name__ == "__main__":
    main_streak()
