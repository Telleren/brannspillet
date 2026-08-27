import json
import sqlite3
from collections import Counter
from pathlib import Path


DB_FILE = Path("data/brannspillet.db")
RAW_DIR = Path("data/raw")

BRANN_ID = "05bb57f9-3430-5a18-b77c-96b578525b9c"


def get_brann_squad_from_raw(filename):

    filepath = RAW_DIR / filename

    with filepath.open(
        "r",
        encoding="utf-8"
    ) as file:
        data = json.load(file)

    match = data["result"]["data"]["model"]

    if match["homeTeam"]["_id"] == BRANN_ID:
        squad = match.get("homeSquad") or []
    else:
        squad = match.get("awaySquad") or []

    return squad


def find_same_name_in_squad(
    squad,
    player_name,
    player_id
):

    matches = []

    if not player_name:
        return matches

    wanted = player_name.casefold().strip()

    for entry in squad:

        player = entry.get("player")

        if not player:
            continue

        name = (
            player.get("name")
            or ""
        ).casefold().strip()

        if (
            name == wanted
            and player.get("_id") != player_id
        ):
            matches.append(player)

    return matches


def main():

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row


    # ========================================================
    # INNBYTTERE SOM IKKE FINNES I TROPPSTABELLEN
    # ========================================================

    missing_subs = conn.execute(
        """
        SELECT
            m.id AS match_id,
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

        ORDER BY
            m.date,
            e.minute
        """,
        (BRANN_ID,)
    ).fetchall()


    print()
    print("=" * 80)
    print("MANGLENDE BRANN-INNBYTTERE")
    print("=" * 80)
    print()

    print(
        f"Totalt: {len(missing_subs)}"
    )


    years = Counter(
        row["date"][:4]
        for row in missing_subs
    )

    print()
    print("FORDELT PÅ ÅR")
    print("-" * 80)

    for year in sorted(years):
        print(
            f"{year}: {years[year]}"
        )


    print()
    print("FØRSTE 25 EKSEMPLER")
    print("-" * 80)


    for row in missing_subs[:25]:

        squad = get_brann_squad_from_raw(
            row["source_filename"]
        )

        alternate = find_same_name_in_squad(
            squad,
            row["player_name"],
            row["sub_on_id"]
        )

        print()

        print(
            f"{row['date']} "
            f"{row['home_team']}–"
            f"{row['away_team']} "
            f"{row['score']}"
        )

        print(
            f"{row['minute']}' "
            f"INN: {row['player_name']}"
        )

        print(
            f"Event-ID: "
            f"{row['sub_on_id']}"
        )

        if alternate:

            print(
                ">>> SAMME NAVN FINNES I TROPPEN "
                "MED ANNEN ID:"
            )

            for player in alternate:
                print(
                    f"    {player.get('name')} "
                    f"[{player.get('_id')}]"
                )

        else:
            print(
                "Ikke oppført i Brann-troppen "
                "med samme navn."
            )


    # ========================================================
    # UTBYTTEDE SPILLERE SOM IKKE FINNES I TROPPEN
    # ========================================================

    missing_off = conn.execute(
        """
        SELECT
            m.id AS match_id,
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

        ORDER BY
            m.date,
            e.minute
        """,
        (BRANN_ID,)
    ).fetchall()


    print()
    print()
    print("=" * 80)
    print("MANGLENDE UTBYTTEDE BRANN-SPILLERE")
    print("=" * 80)

    print(
        f"\nTotalt: {len(missing_off)}"
    )


    for row in missing_off:

        squad = get_brann_squad_from_raw(
            row["source_filename"]
        )

        alternate = find_same_name_in_squad(
            squad,
            row["player_name"],
            row["sub_off_id"]
        )

        print()
        print(
            f"{row['date']} "
            f"{row['home_team']}–"
            f"{row['away_team']} "
            f"{row['score']}"
        )

        print(
            f"{row['minute']}' "
            f"UT: {row['player_name']}"
        )

        print(
            f"Event-ID: "
            f"{row['sub_off_id']}"
        )

        if alternate:

            print(
                ">>> SAMME NAVN FINNES I TROPPEN "
                "MED ANNEN ID:"
            )

            for player in alternate:

                print(
                    f"    {player.get('name')} "
                    f"[{player.get('_id')}]"
                )

        else:

            print(
                "Ikke oppført i Brann-troppen "
                "med samme navn."
            )


    conn.close()


if __name__ == "__main__":
    main()