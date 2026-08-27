import sqlite3
from pathlib import Path


DB_FILE = Path("data/brannspillet_v2.db")

BRANN_ID = "05bb57f9-3430-5a18-b77c-96b578525b9c"


def print_check(name, ok, details=""):

    status = "OK" if ok else "PROBLEM"

    print(
        f"{status:<8} {name}"
    )

    if details:
        print(
            f"         {details}"
        )


def main():

    conn = sqlite3.connect(DB_FILE)

    conn.row_factory = sqlite3.Row

    appearance_columns = {
        row["name"]
        for row in conn.execute(
            """
            PRAGMA table_info(appearances)
            """
        )
    }


    print()
    print("=" * 70)
    print("BRANNSPILLET – DATABASEAUDIT")
    print("=" * 70)
    print()


    # ========================================================
    # SQLITE-INTEGRITET
    # ========================================================

    integrity = conn.execute(
        "PRAGMA integrity_check"
    ).fetchone()[0]

    print_check(
        "SQLite integrity_check",
        integrity == "ok",
        str(integrity)
    )


    fk_errors = conn.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()

    print_check(
        "Foreign keys",
        len(fk_errors) == 0,
        f"{len(fk_errors)} feil"
    )


    # ========================================================
    # KAMPER
    # ========================================================

    matches = conn.execute(
        """
        SELECT COUNT(*)
        FROM matches
        """
    ).fetchone()[0]


    brann_matches = conn.execute(
        """
        SELECT COUNT(*)

        FROM matches

        WHERE
            home_team_id = ?
            OR away_team_id = ?
        """,
        (
            BRANN_ID,
            BRANN_ID
        )
    ).fetchone()[0]


    print_check(
        "Alle kamper involverer Brann",
        matches == brann_matches,
        f"{brann_matches}/{matches}"
    )


    # ========================================================
    # 11 STARTERE I ALLE KAMPER
    # ========================================================

    bad_starter_matches = conn.execute(
        """
        SELECT
            m.date,
            ht.name AS home_team,
            at.name AS away_team,
            COUNT(a.player_id) AS starters

        FROM matches m

        JOIN teams ht
            ON ht.id = m.home_team_id

        JOIN teams at
            ON at.id = m.away_team_id

        LEFT JOIN appearances a
            ON a.match_id = m.id
            AND a.team_id = ?
            AND a.starting = 1

        GROUP BY
            m.id

        HAVING
            COUNT(a.player_id) != 11
        """,
        (BRANN_ID,)
    ).fetchall()


    print_check(
        "11 Brann-startere i alle kamper",
        len(bad_starter_matches) == 0,
        f"{len(bad_starter_matches)} avvik"
    )


    # ========================================================
    # FORVENTEDE OPPTREDENER
    #
    # En spiller har spilt hvis vedkommende:
    #
    # 1. startet
    # ELLER
    # 2. ble byttet inn
    # ========================================================

    starters = {
        (
            row["match_id"],
            row["player_id"]
        )

        for row in conn.execute(
            """
            SELECT
                match_id,
                player_id

            FROM appearances

            WHERE
                team_id = ?
                AND starting = 1
            """,
            (BRANN_ID,)
        )
    }


    subs_on = {
        (
            row["match_id"],
            row["sub_on_id"]
        )

        for row in conn.execute(
            """
            SELECT
                match_id,
                sub_on_id

            FROM events

            WHERE
                team_id = ?
                AND event_type = 'subApp'
                AND sub_on_id IS NOT NULL
            """,
            (BRANN_ID,)
        )
    }


    expected_appearances = (
        starters | subs_on
    )


    actual_appearances = {
        (
            row["match_id"],
            row["player_id"]
        )

        for row in conn.execute(
            """
            SELECT
                match_id,
                player_id

            FROM appearances

            WHERE
                team_id = ?
                AND appeared = 1
            """,
            (BRANN_ID,)
        )
    }


    missing_appearances = (
        expected_appearances
        - actual_appearances
    )

    extra_appearances = (
        actual_appearances
        - expected_appearances
    )


    print_check(
        "Brann-opptredener stemmer med startere + innbyttere",
        (
            not missing_appearances
            and not extra_appearances
        ),
        (
            f"Forventet {len(expected_appearances)}, "
            f"database {len(actual_appearances)}, "
            f"mangler {len(missing_appearances)}, "
            f"ekstra {len(extra_appearances)}"
        )
    )


    # ========================================================
    # INNBYTTERE SOM MANGLER I TROPPEN
    # ========================================================

    missing_subs = conn.execute(
        """
        SELECT
            e.match_id,
            e.minute,
            e.sub_on_id

        FROM events e

        LEFT JOIN appearances a
            ON a.match_id = e.match_id
            AND a.team_id = e.team_id
            AND a.player_id = e.sub_on_id

        WHERE
            e.team_id = ?
            AND e.event_type = 'subApp'
            AND e.sub_on_id IS NOT NULL
            AND a.player_id IS NULL
        """,
        (BRANN_ID,)
    ).fetchall()


    print_check(
        "Alle Brann-innbyttere finnes i kamptroppen",
        len(missing_subs) == 0,
        f"{len(missing_subs)} avvik"
    )


    # ========================================================
    # SPILLERE SOM GÅR UT, MEN MANGLER I TROPPEN
    # ========================================================

    missing_sub_off = conn.execute(
        """
        SELECT
            e.match_id,
            e.minute,
            e.sub_off_id

        FROM events e

        LEFT JOIN appearances a
            ON a.match_id = e.match_id
            AND a.team_id = e.team_id
            AND a.player_id = e.sub_off_id

        WHERE
            e.team_id = ?
            AND e.event_type = 'subApp'
            AND e.sub_off_id IS NOT NULL
            AND a.player_id IS NULL
        """,
        (BRANN_ID,)
    ).fetchall()


    print_check(
        "Alle utbyttede Brann-spillere finnes i kamptroppen",
        len(missing_sub_off) == 0,
        f"{len(missing_sub_off)} avvik"
    )


    # ========================================================
    # BRANN-MÅL UTEN MÅLSCORER
    # ========================================================

    missing_scorers = conn.execute(
        """
        SELECT COUNT(*)

        FROM events

        WHERE
            team_id = ?
            AND event_type IN (
                'goal',
                'penaltyGoal'
            )
            AND scorer_id IS NULL
        """,
        (BRANN_ID,)
    ).fetchone()[0]


    print_check(
        "Alle ordinære Brann-mål har målscorer",
        missing_scorers == 0,
        f"{missing_scorers} mangler"
    )


    # ========================================================
    # BRANN-BYTTER UTEN INNBYTTER
    # ========================================================

    missing_sub_on = conn.execute(
        """
        SELECT COUNT(*)

        FROM events

        WHERE
            team_id = ?
            AND event_type = 'subApp'
            AND sub_on_id IS NULL
        """,
        (BRANN_ID,)
    ).fetchone()[0]


    print_check(
        "Alle Brann-bytter har innbytter",
        missing_sub_on == 0,
        f"{missing_sub_on} mangler"
    )


    # ========================================================
    # EVENTS UTEN NORMALISERT LAG
    #
    # countAs=NULL inkluderer de kjente
    # Straffekonk-markørene og ignoreres her.
    # ========================================================

    missing_event_teams = conn.execute(
        """
        SELECT COUNT(*)

        FROM events

        WHERE
            event_type IS NOT NULL
            AND team_id IS NULL
        """
    ).fetchone()[0]


    print_check(
        "Alle reelle events har normalisert lag",
        missing_event_teams == 0,
        f"{missing_event_teams} mangler"
    )


    # ========================================================
    # OPPSUMMERING
    # ========================================================

    print()
    print("-" * 70)

    print(
        f"Kamper:                    {matches}"
    )

    print(
        f"Brann-starteropptredener: {len(starters)}"
    )

    print(
        f"Brann-innbytteropptred.:   {len(subs_on)}"
    )

    print(
        f"Brann-opptredener totalt:  {len(expected_appearances)}"
    )

    print("-" * 70)


    # Hvis noe feilet i appeared-kontrollen,
    # vis de første eksemplene.
    if missing_appearances:

        print()
        print(
            "FØRSTE MANGLENDE OPPTREDENER"
        )

        for item in sorted(
            missing_appearances
        )[:10]:

            print(item)


    if extra_appearances:

        print()
        print(
            "FØRSTE EKSTRA OPPTREDENER"
        )

        for item in sorted(
            extra_appearances
        )[:10]:

            print(item)


    correction_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM data_corrections
        """
    ).fetchone()[0]

    has_squad_corrections_table = conn.execute(
        """
        SELECT COUNT(*)
        FROM sqlite_master
        WHERE
            type = 'table'
            AND name = 'data_squad_corrections'
        """
    ).fetchone()[0] == 1

    squad_correction_count = None

    if has_squad_corrections_table:

        squad_correction_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM data_squad_corrections
            """
        ).fetchone()[0]


    reconstructed_brann = conn.execute(
        """
        SELECT COUNT(*)

        FROM appearances

        WHERE
            team_id = ?
            AND appeared = 1
            AND listed_in_squad = 0
        """,
        (BRANN_ID,)
    ).fetchone()[0]


    unknown_brann_starts = conn.execute(
        """
        SELECT COUNT(*)

        FROM appearances

        WHERE
            team_id = ?
            AND appeared = 1
            AND starting IS NULL
        """,
        (BRANN_ID,)
    ).fetchone()[0]

    has_squad_index = (
        "squad_index"
        in appearance_columns
    )

    missing_squad_indexes = None
    duplicate_squad_indexes = None
    event_only_squad_indexes = None

    if has_squad_index:

        missing_squad_indexes = conn.execute(
            """
            SELECT COUNT(*)

            FROM appearances

            WHERE
                listed_in_squad = 1
                AND squad_index IS NULL
            """
        ).fetchone()[0]


        duplicate_squad_indexes = conn.execute(
            """
            SELECT COUNT(*)

            FROM (
                SELECT
                    match_id,
                    team_id,
                    squad_index,
                    COUNT(*) AS rows_with_index

                FROM appearances

                WHERE
                    listed_in_squad = 1
                    AND squad_index IS NOT NULL

                GROUP BY
                    match_id,
                    team_id,
                    squad_index

                HAVING
                    COUNT(*) > 1
            )
            """
        ).fetchone()[0]


        event_only_squad_indexes = conn.execute(
            """
            SELECT COUNT(*)

            FROM appearances

            WHERE
                listed_in_squad = 0
                AND squad_index IS NOT NULL
            """
        ).fetchone()[0]


    print()
    print("V2-KONTROLLER")
    print("-" * 70)


    print_check(
        "Eksplisitte datakorreksjoner",
        correction_count == 2,
        f"{correction_count}/2"
    )

    print_check(
        "Ingen v2-troppskorreksjoner",
        (
            has_squad_corrections_table
            and squad_correction_count == 0
        ),
        (
            f"{squad_correction_count}/0"
            if has_squad_corrections_table
            else "tabell mangler"
        )
    )


    print_check(
        "Rekonstruerte Brann-opptredener",
        reconstructed_brann == 93,
        f"{reconstructed_brann}/93"
    )


    print_check(
        "Ingen Brann-spillere med ukjent startstatus",
        unknown_brann_starts == 0,
        f"{unknown_brann_starts} avvik"
    )


    print_check(
        "Squad index finnes i appearances",
        has_squad_index,
        (
            "kolonne finnes"
            if has_squad_index
            else "kolonne mangler"
        )
    )


    if has_squad_index:

        print_check(
            "Alle troppsførte rader har squad_index",
            missing_squad_indexes == 0,
            f"{missing_squad_indexes} mangler"
        )


        print_check(
            "Ingen dupliserte squad_index per kamp/lag",
            duplicate_squad_indexes == 0,
            f"{duplicate_squad_indexes} avvik"
        )


        print_check(
            "Event-rekonstruerte rader har ikke squad_index",
            event_only_squad_indexes == 0,
            f"{event_only_squad_indexes} avvik"
        )
    conn.close()


if __name__ == "__main__":
    main()
