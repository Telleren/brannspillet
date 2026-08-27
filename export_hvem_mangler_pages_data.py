import json
from datetime import datetime, timezone
from pathlib import Path

from hvem_mangler import (
    BRANN_ID,
    GROUP_ORDER,
    MAX_YEAR,
    MIN_YEAR,
    close_databases,
    connect_databases,
    get_all_candidate_matches,
    get_enriched_shirt_number,
    get_starting_eleven,
    load_shirt_enrichments,
    normalize_text,
    role_group,
)


OUTPUT_FILE = Path("docs/hvem-mangler/puzzles.json")


def player_names(player):

    names = [
        player["name"]
    ]

    if player.get("full_name"):
        names.append(
            player["full_name"]
        )

    return [
        name
        for name in names
        if name
    ]


def is_known_player(player):

    return (
        normalize_text(player["name"])
        not in {
            "ukjent",
            "ukjent ukjent"
        }
    )


def build_appearance_counts(database):

    rows = database["conn"].execute(
        """
        SELECT
            substr(m.date, 1, 4) AS year,
            a.player_id,
            COUNT(*) AS appearances

        FROM appearances a

        JOIN matches m
            ON m.id = a.match_id

        WHERE
            a.team_id = ?
            AND a.appeared = 1

        GROUP BY
            year,
            a.player_id
        """,
        (
            BRANN_ID,
        )
    ).fetchall()

    return {
        (
            int(row["year"]),
            row["player_id"]
        ): row["appearances"]
        for row in rows
    }


def build_match_seasons(database):

    rows = database["conn"].execute(
        """
        SELECT
            id,
            season_name

        FROM matches
        """
    ).fetchall()

    return {
        row["id"]: row["season_name"]
        for row in rows
    }


def build_unique_season_shirts(database):

    rows = database["conn"].execute(
        """
        SELECT
            m.season_name,
            a.player_id,
            a.shirt_number

        FROM appearances a

        JOIN matches m
            ON m.id = a.match_id

        WHERE
            a.team_id = ?
            AND m.season_name IS NOT NULL
            AND a.shirt_number IS NOT NULL
        """,
        (
            BRANN_ID,
        )
    ).fetchall()

    numbers = {}

    for row in rows:

        key = (
            row["player_id"],
            row["season_name"]
        )

        numbers.setdefault(
            key,
            set()
        ).add(
            row["shirt_number"]
        )

    return {
        key: next(iter(values))
        for key, values in numbers.items()
        if len(values) == 1
    }


def choose_hidden_player(
    database,
    match,
    starters
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
            "har ingen gyldig spiller å skjule."
        )

    ranked = []

    for player in possible_hidden:

        appearances = database["appearance_counts"].get(
            (
                year,
                player["id"]
            ),
            0
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

    return ranked[0][3]


def get_display_shirt_number(
    database,
    enrichments,
    player,
    match
):

    if player["shirt_number"] is not None:
        return player["shirt_number"]

    shirt = get_enriched_shirt_number(
        enrichments,
        player["name"],
        match["date"]
    )

    if shirt is not None:
        return shirt

    season_name = database["match_seasons"].get(
        match["id"]
    )

    if not season_name:
        return None

    return database["unique_season_shirts"].get(
        (
            player["id"],
            season_name
        )
    )


def build_lineup(
    database,
    enrichments,
    match,
    starters,
    hidden
):

    lineup = []

    for player in starters:

        shirt = get_display_shirt_number(
            database,
            enrichments,
            player,
            match
        )

        lineup.append(
            {
                "id": player["id"],
                "name": player["name"],
                "fullName": player["full_name"],
                "role": role_group(
                    player["role_abbr"]
                ),
                "shirt": (
                    str(shirt)
                    if shirt is not None
                    else "?"
                ),
                "hidden": (
                    player["id"]
                    == hidden["id"]
                ),
            }
        )

    return lineup


def build_puzzle(
    database,
    enrichments,
    match
):

    starters = get_starting_eleven(
        database,
        match["id"]
    )

    hidden = choose_hidden_player(
        database,
        match,
        starters
    )

    return {
        "id": (
            f"{match['database']}:"
            f"{match['id']}"
        ),
        "date": match["date"],
        "year": int(
            match["date"][:4]
        ),
        "competition": (
            match["competition"]
            or "Ukjent turnering"
        ),
        "homeTeam": match["home_team"],
        "awayTeam": match["away_team"],
        "score": match["score"],
        "lineup": build_lineup(
            database,
            enrichments,
            match,
            starters,
            hidden
        ),
        "answer": {
            "id": hidden["id"],
            "names": player_names(
                hidden
            ),
        },
    }


def main():

    enrichments = load_shirt_enrichments()
    databases = connect_databases(
        MIN_YEAR,
        MAX_YEAR
    )

    try:

        database_by_name = {
            database["name"]: database
            for database in databases
        }

        for database in databases:

            database["appearance_counts"] = (
                build_appearance_counts(
                    database
                )
            )

            database["match_seasons"] = (
                build_match_seasons(
                    database
                )
            )

            database["unique_season_shirts"] = (
                build_unique_season_shirts(
                    database
                )
            )

        candidates = get_all_candidate_matches(
            databases,
            MIN_YEAR,
            MAX_YEAR
        )

        puzzles = []

        for match in candidates:

            database = database_by_name[
                match["database"]
            ]

            puzzles.append(
                build_puzzle(
                    database,
                    enrichments,
                    match
                )
            )

        OUTPUT_FILE.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with OUTPUT_FILE.open(
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                {
                    "generatedAt": datetime.now(
                        timezone.utc
                    ).isoformat(),
                    "minYear": MIN_YEAR,
                    "maxYear": MAX_YEAR,
                    "groupOrder": GROUP_ORDER,
                    "puzzles": puzzles,
                },
                file,
                ensure_ascii=False,
                separators=(",", ":")
            )

        print(
            f"Exported {len(puzzles)} puzzles "
            f"to {OUTPUT_FILE}"
        )

    finally:

        close_databases(
            databases
        )


if __name__ == "__main__":
    main()
