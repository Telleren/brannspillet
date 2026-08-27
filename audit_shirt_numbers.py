import sqlite3
from collections import Counter
from pathlib import Path


DB_FILE = Path("data/brannspillet_v2.db")

BRANN_ID = "05bb57f9-3430-5a18-b77c-96b578525b9c"


def main():

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row


    missing = conn.execute(
        """
        SELECT
            m.id AS match_id,
            m.date,
            m.season_name,

            ht.name AS home_team,
            at.name AS away_team,

            p.id AS player_id,
            p.name AS player_name

        FROM appearances a

        JOIN matches m
            ON m.id = a.match_id

        JOIN players p
            ON p.id = a.player_id

        JOIN teams ht
            ON ht.id = m.home_team_id

        JOIN teams at
            ON at.id = m.away_team_id

        WHERE
            a.team_id = ?
            AND a.starting = 1
            AND a.shirt_number IS NULL

        ORDER BY
            m.date,
            p.name
        """,
        (BRANN_ID,)
    ).fetchall()


    print()
    print("=" * 80)
    print("MANGLENDE DRAKTNUMMER – BRANN-STARTERE")
    print("=" * 80)

    print()
    print(
        f"Starteropptredener uten nummer: "
        f"{len(missing)}"
    )


    years = Counter(
        row["date"][:4]
        for row in missing
    )


    print()
    print("FORDELT PÅ ÅR")
    print("-" * 80)

    for year in sorted(years):

        print(
            f"{year}: {years[year]}"
        )


    unresolved = []


    for row in missing:

        numbers = conn.execute(
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
                row["player_id"],
                row["season_name"]
            )
        ).fetchall()


        known_numbers = {
            number["shirt_number"]
            for number in numbers
        }


        if len(known_numbers) != 1:

            unresolved.append(
                (
                    row,
                    known_numbers
                )
            )


    print()
    print("=" * 80)
    print("FORTSATT ULØST ETTER SESONG-INFERENS")
    print("=" * 80)

    print()
    print(
        f"Antall: {len(unresolved)}"
    )


    for row, known_numbers in unresolved:

        if not known_numbers:
            number_text = (
                "ingen kjente numre "
                "i sesongen"
            )

        else:
            number_text = (
                "flere mulige: "
                + ", ".join(
                    str(number)
                    for number
                    in sorted(known_numbers)
                )
            )


        print(
            f"{row['date']} | "
            f"{row['home_team']}–"
            f"{row['away_team']} | "
            f"{row['player_name']} | "
            f"{number_text}"
        )


    conn.close()


if __name__ == "__main__":
    main()