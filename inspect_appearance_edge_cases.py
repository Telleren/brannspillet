import json
import sqlite3
from pathlib import Path


DB_FILE = Path("data/brannspillet.db")
RAW_DIR = Path("data/raw")

BRANN_ID = "05bb57f9-3430-5a18-b77c-96b578525b9c"


def load_match(filename):

    filepath = RAW_DIR / filename

    with filepath.open(
        "r",
        encoding="utf-8"
    ) as file:
        data = json.load(file)

    return data["result"]["data"]["model"]


def get_brann_squad(match):

    if match["homeTeam"]["_id"] == BRANN_ID:
        return match.get("homeSquad") or []

    return match.get("awaySquad") or []


def print_squad(match):

    squad = get_brann_squad(match)

    print()
    print("BRANN-TROPP")
    print("-" * 80)

    for entry in squad:

        player = entry.get("player") or {}
        role = entry.get("role") or {}

        print(
            f"{str(entry.get('shirt')):>3}  "
            f"{player.get('name')}  "
            f"ID={player.get('_id')}  "
            f"starting={role.get('starting')}  "
            f"role={role.get('abbr')}"
        )


def print_player_events(
    match,
    player_id
):

    print()
    print("ALLE EVENTS SOM INVOLVERER SPILLEREN")
    print("-" * 80)

    found = False

    for event in match.get("events", []):

        involved = False

        for field in [
            "player",
            "scoredBy",
            "assistedBy",
            "subOn",
            "subOff"
        ]:

            player = event.get(field)

            if (
                player
                and player.get("_id") == player_id
            ):
                involved = True

        if not involved:
            continue

        found = True

        print(
            json.dumps(
                event,
                ensure_ascii=False,
                indent=2
            )
        )

        print()

    if not found:
        print("Ingen andre events funnet.")


def inspect_case(
    row,
    player_field
):

    match = load_match(
        row["source_filename"]
    )

    player_id = row[player_field]

    print()
    print("=" * 80)

    print(
        f"{row['date']} – "
        f"{row['home_team']}–"
        f"{row['away_team']} "
        f"{row['score']}"
    )

    print("=" * 80)

    print(
        f"Minutt: {row['minute']}"
    )

    print(
        f"Spiller: {row['player_name']}"
    )

    print(
        f"ID: {player_id}"
    )

    print_player_events(
        match,
        player_id
    )

    print_squad(
        match
    )


def main():

    conn = sqlite3.connect(
        DB_FILE
    )

    conn.row_factory = sqlite3.Row


    # ========================================================
    # MODERNE MANGLENDE INNBYTTERE
    # ========================================================

    modern_missing_subs = conn.execute(
        """
        SELECT
            m.date,
            m.score,
            m.source_filename,

            ht.name AS home_team,
            at.name AS away_team,

            e.minute,
            e.sub_on_id,

            p.name AS player_name

        FROM events e

        JOIN matches m
            ON m.id = e.match_id

        JOIN teams ht
            ON ht.id = m.home_team_id

        JOIN teams at
            ON at.id = m.away_team_id

        LEFT JOIN players p
            ON p.id = e.sub_on_id

        LEFT JOIN appearances a
            ON a.match_id = e.match_id
            AND a.team_id = e.team_id
            AND a.player_id = e.sub_on_id

        WHERE
            e.team_id = ?
            AND e.event_type = 'subApp'
            AND e.sub_on_id IS NOT NULL
            AND a.player_id IS NULL
            AND m.date >= '2024-01-01'

        ORDER BY
            m.date,
            e.minute
        """,
        (BRANN_ID,)
    ).fetchall()


    print()
    print("#" * 80)
    print("MODERNE MANGLENDE INNBYTTERE")
    print("#" * 80)

    print(
        f"Antall: {len(modern_missing_subs)}"
    )


    for row in modern_missing_subs:

        inspect_case(
            row,
            "sub_on_id"
        )


    # ========================================================
    # SUB-OFF SOM FORTSATT IKKE KAN FORKLARES AV
    # ET TIDLIGERE SUB-ON I SAMME KAMP
    # ========================================================

    unresolved_sub_off = conn.execute(
        """
        SELECT
            m.date,
            m.score,
            m.source_filename,

            ht.name AS home_team,
            at.name AS away_team,

            e.minute,
            e.sub_off_id,

            p.name AS player_name

        FROM events e

        JOIN matches m
            ON m.id = e.match_id

        JOIN teams ht
            ON ht.id = m.home_team_id

        JOIN teams at
            ON at.id = m.away_team_id

        LEFT JOIN players p
            ON p.id = e.sub_off_id

        LEFT JOIN appearances a
            ON a.match_id = e.match_id
            AND a.team_id = e.team_id
            AND a.player_id = e.sub_off_id

        WHERE
            e.team_id = ?
            AND e.event_type = 'subApp'
            AND e.sub_off_id IS NOT NULL
            AND a.player_id IS NULL

            AND NOT EXISTS (
                SELECT 1

                FROM events earlier

                WHERE
                    earlier.match_id = e.match_id
                    AND earlier.team_id = e.team_id
                    AND earlier.event_type = 'subApp'
                    AND earlier.sub_on_id = e.sub_off_id
                    AND earlier.minute <= e.minute
            )

        ORDER BY
            m.date,
            e.minute
        """,
        (BRANN_ID,)
    ).fetchall()


    print()
    print()
    print("#" * 80)
    print("UFORKLARTE SUB-OFF")
    print("#" * 80)

    print(
        f"Antall: {len(unresolved_sub_off)}"
    )


    for row in unresolved_sub_off:

        inspect_case(
            row,
            "sub_off_id"
        )


    conn.close()


if __name__ == "__main__":
    main()