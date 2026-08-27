import sqlite3
import sys
import unicodedata
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path


# ============================================================
# INNSTILLINGER
# ============================================================

BRANN_ID = "05bb57f9-3430-5a18-b77c-96b578525b9c"

# Bruk v2 så lenge vi vet at dette er den validerte databasen.
DB_FILE = Path("data/brannspillet_v2.db")


# ============================================================
# HJELPEFUNKSJONER
# ============================================================

def normalize_text(text):
    """
    Gjør søk enklere:
    - små bokstaver
    - fjerner aksenter

    Eksempel:
    "Sævarsson" og "saevarsson" blir lettere å søke etter.
    """

    if not text:
        return ""

    text = text.casefold()

    text = unicodedata.normalize(
        "NFKD",
        text
    )

    return "".join(
        char
        for char in text
        if not unicodedata.combining(char)
    )


def format_date(date_text):

    if not date_text:
        return "Ukjent"

    try:
        date = datetime.strptime(
            date_text,
            "%Y-%m-%d"
        )

        return date.strftime(
            "%d.%m.%Y"
        )

    except ValueError:
        return date_text


def format_birthdate(date_text):

    return format_date(date_text)


def country_name(code):

    countries = {
        "NO": "Norge",
        "SE": "Sverige",
        "DK": "Danmark",
        "FI": "Finland",
        "IS": "Island",
        "FO": "Færøyene",
        "EE": "Estland",
        "LV": "Latvia",
        "LT": "Litauen",
        "DE": "Tyskland",
        "NL": "Nederland",
        "BE": "Belgia",
        "FR": "Frankrike",
        "ES": "Spania",
        "PT": "Portugal",
        "IT": "Italia",
        "GB": "Storbritannia",
        "ENG": "England",
        "SCO": "Skottland",
        "IE": "Irland",
        "PL": "Polen",
        "CZ": "Tsjekkia",
        "SK": "Slovakia",
        "HU": "Ungarn",
        "AT": "Østerrike",
        "CH": "Sveits",
        "BA": "Bosnia-Hercegovina",
        "RS": "Serbia",
        "HR": "Kroatia",
        "SI": "Slovenia",
        "ME": "Montenegro",
        "MK": "Nord-Makedonia",
        "AL": "Albania",
        "GR": "Hellas",
        "CY": "Kypros",
        "TR": "Tyrkia",
        "RO": "Romania",
        "BG": "Bulgaria",
        "UA": "Ukraina",
        "BY": "Belarus",
        "RU": "Russland",
        "GE": "Georgia",
        "AM": "Armenia",
        "AZ": "Aserbajdsjan",
        "GH": "Ghana",
        "NG": "Nigeria",
        "SN": "Senegal",
        "CI": "Elfenbenskysten",
        "CM": "Kamerun",
        "GM": "Gambia",
        "ZA": "Sør-Afrika",
        "JM": "Jamaica",
        "BR": "Brasil",
        "AR": "Argentina",
        "UY": "Uruguay",
        "CL": "Chile",
        "CO": "Colombia",
        "US": "USA",
        "CA": "Canada",
        "AU": "Australia",
        "NZ": "New Zealand"
    }

    if not code:
        return "Ukjent"

    return countries.get(
        code,
        code
    )


def print_line(
    label,
    value,
    width=24
):

    print(
        f"{label:<{width}} {value}"
    )


# ============================================================
# DATABASE
# ============================================================

def connect_database():

    if not DB_FILE.exists():

        raise FileNotFoundError(
            f"Fant ikke databasen: "
            f"{DB_FILE}"
        )

    conn = sqlite3.connect(
        DB_FILE
    )

    conn.row_factory = sqlite3.Row

    return conn


def check_database_version(conn):

    columns = {
        row["name"]
        for row in conn.execute(
            """
            PRAGMA table_info(appearances)
            """
        )
    }

    if "listed_in_squad" not in columns:

        raise RuntimeError(
            "Databasen ser ikke ut til å være "
            "Brannspillet v2."
        )


# ============================================================
# SPILLERSØK
# ============================================================

def get_brann_players(conn):

    return conn.execute(
        """
        SELECT DISTINCT
            p.id,
            p.name,
            p.full_name,
            p.birthdate

        FROM players p

        JOIN appearances a
            ON a.player_id = p.id

        WHERE
            a.team_id = ?

        ORDER BY
            p.name
        """,
        (BRANN_ID,)
    ).fetchall()


def search_players(
    conn,
    search_text
):

    wanted = normalize_text(
        search_text
    )

    players = get_brann_players(
        conn
    )

    exact = []
    starts = []
    contains = []


    for player in players:

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


        if wanted in names:

            exact.append(
                player
            )

            continue


        if any(
            name.startswith(wanted)
            for name in names
        ):

            starts.append(
                player
            )

            continue


        if any(
            wanted in name
            for name in names
        ):

            contains.append(
                player
            )


    if exact:
        return exact

    if starts:
        return starts

    return contains


def get_suggestions(
    conn,
    search_text,
    limit=5
):

    wanted = normalize_text(
        search_text
    )

    players = get_brann_players(
        conn
    )

    scored = []


    for player in players:

        name = normalize_text(
            player["name"]
        )

        score = SequenceMatcher(
            None,
            wanted,
            name
        ).ratio()

        scored.append(
            (
                score,
                player
            )
        )


    scored.sort(
        key=lambda item: item[0],
        reverse=True
    )


    return [
        player
        for score, player
        in scored[:limit]
        if score >= 0.35
    ]


# ============================================================
# VELG SPILLER VED FLERE TREFF
# ============================================================

def choose_player(players):

    if not players:
        return None


    if len(players) == 1:
        return players[0]


    print()
    print(
        "Flere spillere matcher søket:"
    )

    print()


    for number, player in enumerate(
        players,
        start=1
    ):

        birthdate = (
            format_birthdate(
                player["birthdate"]
            )
            if player["birthdate"]
            else "fødselsdato ukjent"
        )

        print(
            f"{number}. "
            f"{player['name']} "
            f"({birthdate})"
        )


    print()

    while True:

        choice = input(
            "Velg nummer: "
        ).strip()

        try:

            number = int(choice)

            if (
                1
                <= number
                <= len(players)
            ):
                return players[
                    number - 1
                ]

        except ValueError:
            pass

        print(
            "Skriv nummeret på spilleren."
        )


# ============================================================
# HENT SPILLERPROFIL
# ============================================================

def get_player(
    conn,
    player_id
):

    return conn.execute(
        """
        SELECT
            id,
            name,
            full_name,
            birthdate,
            birthplace,
            country_code,
            slug

        FROM players

        WHERE id = ?
        """,
        (player_id,)
    ).fetchone()


def get_appearance_stats(
    conn,
    player_id
):

    return conn.execute(
        """
        SELECT

            COUNT(*) AS squad_entries,

            SUM(
                CASE
                    WHEN appeared = 1
                    THEN 1
                    ELSE 0
                END
            ) AS appearances,

            SUM(
                CASE
                    WHEN starting = 1
                    THEN 1
                    ELSE 0
                END
            ) AS starts,

            SUM(
                CASE
                    WHEN
                        appeared = 1
                        AND starting = 0
                    THEN 1
                    ELSE 0
                END
            ) AS sub_appearances,

            SUM(
                CASE
                    WHEN
                        appeared = 0
                        AND listed_in_squad = 1
                    THEN 1
                    ELSE 0
                END
            ) AS unused_subs,

            SUM(
                CASE
                    WHEN
                        appeared = 1
                        AND listed_in_squad = 0
                    THEN 1
                    ELSE 0
                END
            ) AS reconstructed,

            SUM(
                CASE
                    WHEN
                        appeared = 1
                        AND starting IS NULL
                    THEN 1
                    ELSE 0
                END
            ) AS unknown_start

        FROM appearances

        WHERE
            team_id = ?
            AND player_id = ?
        """,
        (
            BRANN_ID,
            player_id
        )
    ).fetchone()


def get_event_stats(
    conn,
    player_id
):

    goals = conn.execute(
        """
        SELECT COUNT(*)

        FROM events

        WHERE
            team_id = ?
            AND scorer_id = ?
            AND event_type IN (
                'goal',
                'penaltyGoal'
            )
        """,
        (
            BRANN_ID,
            player_id
        )
    ).fetchone()[0]


    penalty_goals = conn.execute(
        """
        SELECT COUNT(*)

        FROM events

        WHERE
            team_id = ?
            AND scorer_id = ?
            AND event_type = 'penaltyGoal'
        """,
        (
            BRANN_ID,
            player_id
        )
    ).fetchone()[0]


    assists = conn.execute(
        """
        SELECT COUNT(*)

        FROM events

        WHERE
            team_id = ?
            AND assist_id = ?
            AND event_type IN (
                'goal',
                'penaltyGoal'
            )
        """,
        (
            BRANN_ID,
            player_id
        )
    ).fetchone()[0]


    yellow_cards = conn.execute(
        """
        SELECT COUNT(*)

        FROM events

        WHERE
            team_id = ?
            AND player_id = ?
            AND event_type = 'yc'
        """,
        (
            BRANN_ID,
            player_id
        )
    ).fetchone()[0]


    red_cards = conn.execute(
        """
        SELECT COUNT(*)

        FROM events

        WHERE
            team_id = ?
            AND player_id = ?
            AND event_type = 'rc'
        """,
        (
            BRANN_ID,
            player_id
        )
    ).fetchone()[0]


    return {
        "goals": goals,
        "penalty_goals": penalty_goals,
        "assists": assists,
        "yellow_cards": yellow_cards,
        "red_cards": red_cards
    }


# ============================================================
# FØRSTE / SISTE KAMP
# ============================================================

def get_edge_match(
    conn,
    player_id,
    order
):

    if order not in {
        "ASC",
        "DESC"
    }:

        raise ValueError(
            "Ugyldig sortering."
        )


    return conn.execute(
        f"""
        SELECT
            m.date,
            m.score,

            ht.name AS home_team,
            at.name AS away_team,

            c.name AS competition,

            a.starting,
            a.entered_minute

        FROM appearances a

        JOIN matches m
            ON m.id = a.match_id

        JOIN teams ht
            ON ht.id = m.home_team_id

        JOIN teams at
            ON at.id = m.away_team_id

        LEFT JOIN competitions c
            ON c.id = m.competition_id

        WHERE
            a.team_id = ?
            AND a.player_id = ?
            AND a.appeared = 1

        ORDER BY
            m.date {order},
            m.time {order}

        LIMIT 1
        """,
        (
            BRANN_ID,
            player_id
        )
    ).fetchone()


def describe_match(row):

    if not row:
        return "Ingen registrert kamp"


    match = (
        f"{row['home_team']}–"
        f"{row['away_team']} "
        f"{row['score']}"
    )


    competition = (
        row["competition"]
        or "ukjent turnering"
    )


    return (
        f"{format_date(row['date'])} – "
        f"{match} "
        f"({competition})"
    )


# ============================================================
# TURNERINGSFORDELING
# ============================================================

def get_competition_stats(
    conn,
    player_id
):

    return conn.execute(
        """
        SELECT
            COALESCE(
                c.name,
                'Ukjent turnering'
            ) AS competition,

            COUNT(*) AS appearances,

            SUM(
                CASE
                    WHEN a.starting = 1
                    THEN 1
                    ELSE 0
                END
            ) AS starts

        FROM appearances a

        JOIN matches m
            ON m.id = a.match_id

        LEFT JOIN competitions c
            ON c.id = m.competition_id

        WHERE
            a.team_id = ?
            AND a.player_id = ?
            AND a.appeared = 1

        GROUP BY
            m.competition_id,
            c.name

        ORDER BY
            appearances DESC,
            competition
        """,
        (
            BRANN_ID,
            player_id
        )
    ).fetchall()


# ============================================================
# SESONGFORDELING
# ============================================================

def get_year_stats(
    conn,
    player_id
):

    return conn.execute(
        """
        SELECT
            substr(m.date, 1, 4) AS year,

            COUNT(*) AS appearances,

            SUM(
                CASE
                    WHEN a.starting = 1
                    THEN 1
                    ELSE 0
                END
            ) AS starts,

            SUM(
                CASE
                    WHEN
                        a.appeared = 1
                        AND a.starting = 0
                    THEN 1
                    ELSE 0
                END
            ) AS sub_appearances

        FROM appearances a

        JOIN matches m
            ON m.id = a.match_id

        WHERE
            a.team_id = ?
            AND a.player_id = ?
            AND a.appeared = 1

        GROUP BY
            substr(m.date, 1, 4)

        ORDER BY
            year
        """,
        (
            BRANN_ID,
            player_id
        )
    ).fetchall()

    return conn.execute(
        """
        SELECT
            m.season_name,

            COUNT(*) AS appearances,

            SUM(
                CASE
                    WHEN a.starting = 1
                    THEN 1
                    ELSE 0
                END
            ) AS starts

        FROM appearances a

        JOIN matches m
            ON m.id = a.match_id

        WHERE
            a.team_id = ?
            AND a.player_id = ?
            AND a.appeared = 1

        GROUP BY
            m.season_name

        ORDER BY
            m.season_name
        """,
        (
            BRANN_ID,
            player_id
        )
    ).fetchall()


# ============================================================
# VIS PROFIL
# ============================================================

def print_profile(
    conn,
    player_id
):

    player = get_player(
        conn,
        player_id
    )

    appearances = get_appearance_stats(
        conn,
        player_id
    )

    events = get_event_stats(
        conn,
        player_id
    )

    first_match = get_edge_match(
        conn,
        player_id,
        "ASC"
    )

    last_match = get_edge_match(
        conn,
        player_id,
        "DESC"
    )

    competitions = get_competition_stats(
        conn,
        player_id
    )

    years = get_year_stats(
        conn,
        player_id
    )


    print()
    print("=" * 72)

    print(
        player["name"].upper()
    )

    print("=" * 72)
    print()


    if (
        player["full_name"]
        and player["full_name"]
        != player["name"]
    ):

        print_line(
            "Fullt navn:",
            player["full_name"]
        )


    print_line(
        "Født:",
        (
            format_birthdate(
                player["birthdate"]
            )
            if player["birthdate"]
            else "Ukjent"
        )
    )

    print_line(
        "Fødested:",
        (
            player["birthplace"]
            or "Ukjent"
        )
    )

    print_line(
        "Nasjonalitet:",
        country_name(
            player["country_code"]
        )
    )


    print()
    print("KAMPER")
    print("-" * 72)


    print_line(
        "Kamper:",
        appearances["appearances"]
        or 0
    )

    print_line(
        "Starter:",
        appearances["starts"]
        or 0
    )

    print_line(
        "Innhopp:",
        appearances["sub_appearances"]
        or 0
    )

    print_line(
        "Ubrukt reserve:",
        appearances["unused_subs"]
        or 0
    )


    if appearances["reconstructed"]:

        print_line(
            "Rekonstruert fra events:",
            appearances["reconstructed"]
        )


    if appearances["unknown_start"]:

        print_line(
            "Ukjent startstatus:",
            appearances["unknown_start"]
        )


    print()
    print("MÅL / HENDELSER")
    print("-" * 72)


    print_line(
        "Mål:",
        events["goals"]
    )

    print_line(
        "– hvorav straffemål:",
        events["penalty_goals"]
    )

    print_line(
        "Assists:",
        events["assists"]
    )

    print_line(
        "Gule kort:",
        events["yellow_cards"]
    )

    print_line(
        "Røde kort:",
        events["red_cards"]
    )


    print()
    print("FØRSTE OG SISTE KAMP")
    print("-" * 72)


    print_line(
        "Første:",
        describe_match(
            first_match
        )
    )

    print_line(
        "Siste:",
        describe_match(
            last_match
        )
    )


    print()
    print("TURNERINGER")
    print("-" * 72)


    for row in competitions:

        print(
            f"{row['competition']:<32} "
            f"{row['appearances']:>4} kamper "
            f"({row['starts']:>3} starter)"
        )


    print()
    print("ÅR")
    print("-" * 72)


    for row in years:

        print(
            f"{row['year']:<8} "
            f"{row['appearances']:>4} kamper "
            f"({row['starts']:>3} starter, "
            f"{row['sub_appearances']:>3} innhopp)"
        )


    print()
    print("=" * 72)


# ============================================================
# SØK OG VIS
# ============================================================

def query_player(
    conn,
    search_text
):

    matches = search_players(
        conn,
        search_text
    )


    if not matches:

        print()
        print(
            f'Fant ingen Brann-spiller '
            f'som matcher "{search_text}".'
        )

        suggestions = get_suggestions(
            conn,
            search_text
        )

        if suggestions:

            print()
            print(
                "Mente du kanskje:"
            )

            for player in suggestions:

                print(
                    f"  - {player['name']}"
                )

        return


    player = choose_player(
        matches
    )

    if player:

        print_profile(
            conn,
            player["id"]
        )


# ============================================================
# HOVEDPROGRAM
# ============================================================

def main():

    try:

        conn = connect_database()

        check_database_version(
            conn
        )


    except Exception as error:

        print()
        print(
            "KUNNE IKKE ÅPNE DATABASEN"
        )

        print("-" * 72)

        print(error)

        return


    # Hvis navn gis direkte:
    #
    # python query.py "Bård Finne"

    if len(sys.argv) > 1:

        search_text = " ".join(
            sys.argv[1:]
        ).strip()

        query_player(
            conn,
            search_text
        )

        conn.close()

        return


    # Ellers interaktiv modus.

    print()
    print("=" * 72)
    print("BRANNSPILLET – SPILLEROPPSLAG")
    print("=" * 72)

    print()
    print(
        "Skriv navn eller deler av navnet "
        "på en Brann-spiller."
    )

    print(
        'Skriv "q" for å avslutte.'
    )


    while True:

        print()

        search_text = input(
            "Spiller: "
        ).strip()


        if normalize_text(
            search_text
        ) in {
            "q",
            "quit",
            "exit",
            "avslutt"
        }:

            break


        if not search_text:
            continue


        query_player(
            conn,
            search_text
        )


    conn.close()

    print()
    print("Avsluttet.")


if __name__ == "__main__":
    main()