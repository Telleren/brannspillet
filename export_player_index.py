import json
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import tenable


OUTPUT_FILE = Path("docs/shared/player-index.json")
ALIAS_FILE = Path("data/player_aliases.yaml")
SCHEMA_VERSION = 1


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(
        encoding="utf-8",
        errors="replace"
    )


try:
    import yaml

except ImportError:
    yaml = None


SPECIAL_ASCII_REPLACEMENTS = str.maketrans(
    {
        "Æ": "Ae",
        "Ø": "O",
        "Å": "A",
        "æ": "ae",
        "ø": "o",
        "å": "a",
        "Ð": "D",
        "ð": "d",
        "Þ": "Th",
        "þ": "th",
        "Ł": "L",
        "ł": "l",
    }
)


def ascii_fold(text):

    if not text:
        return ""

    translated = text.translate(
        SPECIAL_ASCII_REPLACEMENTS
    )
    normalized = unicodedata.normalize(
        "NFKD",
        translated
    )

    return "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )


def normalize_text(text):

    return " ".join(
        ascii_fold(text)
        .casefold()
        .replace("-", " ")
        .split()
    )


def add_year(years_by_player, player_id, match_date):

    years_by_player.setdefault(
        player_id,
        set()
    ).add(
        int(match_date[:4])
    )


def merge_player_row(players, row, source_name):

    player_id = row["player_id"]

    if player_id not in players:

        players[player_id] = {
            "id": player_id,
            "name": row["name"],
            "fullName": row["full_name"],
            "birthdate": row["birthdate"],
            "countryCode": row["country_code"],
            "firstBrannMatchDate": row["first_match_date"],
            "lastBrannMatchDate": row["last_match_date"],
            "appearanceCount": row["appearance_count"],
            "startCount": row["start_count"],
            "substituteAppearanceCount": row[
                "substitute_appearance_count"
            ],
            "goalCount": 0,
            "sources": [source_name],
        }

        return

    player = players[player_id]

    for field in (
        "name",
        "fullName",
        "birthdate",
        "countryCode",
    ):

        if not player.get(field):

            if field == "fullName":
                row_field = "full_name"
            elif field == "countryCode":
                row_field = "country_code"
            else:
                row_field = field

            player[field] = row[row_field]

    player["firstBrannMatchDate"] = min(
        player["firstBrannMatchDate"],
        row["first_match_date"]
    )
    player["lastBrannMatchDate"] = max(
        player["lastBrannMatchDate"],
        row["last_match_date"]
    )
    player["appearanceCount"] += row["appearance_count"]
    player["startCount"] += row["start_count"]
    player["substituteAppearanceCount"] += row[
        "substitute_appearance_count"
    ]

    if source_name not in player["sources"]:
        player["sources"].append(source_name)


def query_players():

    players = {}
    years_by_player = {}

    databases = tenable.connect_databases(
        tenable.MIN_YEAR,
        tenable.MAX_YEAR
    )

    try:

        for database in databases:

            source_name = database["name"]
            conn = database["conn"]

            rows = conn.execute(
                """
                SELECT
                    a.player_id,
                    p.name,
                    p.full_name,
                    p.birthdate,
                    p.country_code,
                    MIN(m.date) AS first_match_date,
                    MAX(m.date) AS last_match_date,
                    COUNT(*) AS appearance_count,
                    SUM(
                        CASE
                            WHEN a.starting = 1 THEN 1
                            ELSE 0
                        END
                    ) AS start_count,
                    SUM(
                        CASE
                            WHEN a.starting = 0 THEN 1
                            ELSE 0
                        END
                    ) AS substitute_appearance_count

                FROM appearances a

                JOIN matches m
                    ON m.id = a.match_id

                JOIN players p
                    ON p.id = a.player_id

                WHERE
                    a.team_id = ?
                    AND a.appeared = 1

                GROUP BY
                    a.player_id,
                    p.name,
                    p.full_name,
                    p.birthdate,
                    p.country_code
                """,
                (
                    tenable.BRANN_ID,
                )
            ).fetchall()

            for row in rows:
                merge_player_row(
                    players,
                    row,
                    source_name
                )

            year_rows = conn.execute(
                """
                SELECT DISTINCT
                    a.player_id,
                    m.date

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

            for row in year_rows:
                add_year(
                    years_by_player,
                    row["player_id"],
                    row["date"]
                )

            goal_rows = conn.execute(
                """
                SELECT
                    COALESCE(e.scorer_id, e.player_id) AS player_id,
                    COUNT(*) AS goal_count

                FROM events e

                WHERE
                    e.team_id = ?
                    AND e.event_type IN ('goal', 'penaltyGoal')
                    AND COALESCE(e.scorer_id, e.player_id) IS NOT NULL

                GROUP BY
                    COALESCE(e.scorer_id, e.player_id)
                """,
                (
                    tenable.BRANN_ID,
                )
            ).fetchall()

            for row in goal_rows:

                player_id = row["player_id"]

                if player_id in players:
                    players[player_id]["goalCount"] += row["goal_count"]

    finally:

        tenable.close_databases(
            databases
        )

    for player_id, player in players.items():

        years = sorted(
            years_by_player.get(
                player_id,
                set()
            )
        )

        player["brannYears"] = years
        player["firstBrannYear"] = years[0]
        player["lastBrannYear"] = years[-1]

    return players


def load_manual_aliases():

    if not ALIAS_FILE.exists():
        return {}

    if yaml is None:
        raise SystemExit(
            "PyYAML mangler. Kjor: python -m pip install -r requirements.txt"
        )

    with ALIAS_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:

        data = yaml.safe_load(file)

    if data is None:
        return {}

    if not isinstance(data, dict):
        raise ValueError(
            f"{ALIAS_FILE} must contain a YAML object."
        )

    aliases_by_id = data.get(
        "players",
        data
    )

    if not isinstance(aliases_by_id, dict):
        raise ValueError(
            f"{ALIAS_FILE} players must be a YAML object."
        )

    result = {}

    for player_id, value in aliases_by_id.items():

        if value is None:
            continue

        if isinstance(value, dict):
            aliases = value.get(
                "aliases",
                []
            )
        else:
            aliases = value

        if not isinstance(aliases, list):
            raise ValueError(
                f"{ALIAS_FILE}: aliases for {player_id} must be a list."
            )

        result[str(player_id)] = [
            str(alias)
            for alias in aliases
            if str(alias).strip()
        ]

    return result


def automatic_aliases(player):

    aliases = []

    for field in ("name", "fullName"):

        value = player.get(field)

        if not value:
            continue

        folded = ascii_fold(value)

        if folded != value:
            aliases.append(folded)

    return aliases


def unique_aliases(player, manual_aliases):

    seen = {
        normalize_text(player["name"])
    }

    if player.get("fullName"):
        seen.add(
            normalize_text(player["fullName"])
        )

    aliases = []

    for alias in (
        manual_aliases.get(
            player["id"],
            []
        )
        + automatic_aliases(player)
    ):

        normalized = normalize_text(alias)

        if not normalized or normalized in seen:
            continue

        seen.add(normalized)
        aliases.append(alias)

    return aliases


def serialize_players(players):

    manual_aliases = load_manual_aliases()
    serialized = []

    for player in players.values():

        aliases = unique_aliases(
            player,
            manual_aliases
        )
        search_values = [
            player["name"],
            player["fullName"],
            *aliases,
        ]

        item = {
            "id": player["id"],
            "name": player["name"],
            "fullName": player["fullName"],
            "aliases": aliases,
            "searchText": normalize_text(
                " ".join(
                    value
                    for value in search_values
                    if value
                )
            ),
            "birthdate": player["birthdate"],
            "countryCode": player["countryCode"],
            "firstBrannMatchDate": player[
                "firstBrannMatchDate"
            ],
            "lastBrannMatchDate": player[
                "lastBrannMatchDate"
            ],
            "firstBrannYear": player["firstBrannYear"],
            "lastBrannYear": player["lastBrannYear"],
            "brannYears": player["brannYears"],
            "appearanceCount": player["appearanceCount"],
            "startCount": player["startCount"],
            "substituteAppearanceCount": player[
                "substituteAppearanceCount"
            ],
            "goalCount": player["goalCount"],
            "sources": sorted(player["sources"]),
        }

        serialized.append(item)

    return sorted(
        serialized,
        key=lambda player: (
            normalize_text(player["name"]),
            player["id"]
        )
    )


def build_index():

    players = serialize_players(
        query_players()
    )

    return {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": datetime.now(
            timezone.utc
        ).isoformat(),
        "source": "derived_from_sqlite",
        "brannTeamId": tenable.BRANN_ID,
        "playerCount": len(players),
        "players": players,
    }


def main():

    data = build_index()

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with OUTPUT_FILE.open(
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

    print(
        f"Exported {data['playerCount']} players to {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
