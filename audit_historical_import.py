import csv
import sqlite3
from collections import Counter
from pathlib import Path


DB_FILE = Path("data/brannspillet_historical_sandbox.db")
REPORT_FILE = Path("data/historical_import_audit.csv")

BRANN_ID = "05bb57f9-3430-5a18-b77c-96b578525b9c"

EXPECTED_MATCHES = 1589
EXPECTED_FIRST_DATE = "1911-06-21"
EXPECTED_LAST_DATE = "1999-10-30"
EXPECTED_SQUAD_CORRECTIONS = 9


def print_header(text):

    print()
    print("=" * 72)
    print(text)
    print("=" * 72)


def print_check(label, ok, detail):

    status = "OK" if ok else "AVVIK"

    print(f"{status:<8} {label}")
    print(f"         {detail}")


def match_label(home_team, away_team, score):

    if score:
        return f"{home_team}-{away_team} {score}"

    return f"{home_team}-{away_team}"


def add_issue(
    issues,
    severity,
    code,
    date,
    match,
    match_id,
    detail,
    source_filename
):

    issues.append(
        {
            "severity": severity,
            "code": code,
            "date": date,
            "match": match,
            "match_id": match_id,
            "detail": detail,
            "source_filename": source_filename,
        }
    )


def fetch_single(conn, sql, params=()):

    return conn.execute(
        sql,
        params
    ).fetchone()[0]


def audit():

    if not DB_FILE.exists():
        raise FileNotFoundError(
            f"Fant ikke historisk database: {DB_FILE}"
        )

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row

    issues = []

    print_header("BRANNSPILLET - HISTORISK IMPORTAUDIT")

    integrity = fetch_single(
        conn,
        "PRAGMA integrity_check"
    )

    print_check(
        "SQLite integrity_check",
        integrity == "ok",
        integrity
    )

    foreign_key_errors = len(
        conn.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()
    )

    print_check(
        "Foreign keys",
        foreign_key_errors == 0,
        f"{foreign_key_errors} feil"
    )


    match_count = fetch_single(
        conn,
        "SELECT COUNT(*) FROM matches"
    )

    first_date, last_date = conn.execute(
        """
        SELECT
            MIN(date),
            MAX(date)
        FROM matches
        """
    ).fetchone()

    print_check(
        "Historiske kamper importert",
        match_count == EXPECTED_MATCHES,
        f"{match_count}/{EXPECTED_MATCHES}"
    )

    print_check(
        "Historisk datointervall",
        (
            first_date == EXPECTED_FIRST_DATE
            and last_date == EXPECTED_LAST_DATE
        ),
        f"{first_date}..{last_date}"
    )


    squad_corrections = fetch_single(
        conn,
        """
        SELECT COUNT(*)
        FROM data_squad_corrections
        """
    )

    print_check(
        "Troppskorreksjoner brukt",
        squad_corrections == EXPECTED_SQUAD_CORRECTIONS,
        f"{squad_corrections}/{EXPECTED_SQUAD_CORRECTIONS}"
    )

    duplicate_appearances = fetch_single(
        conn,
        """
        SELECT COUNT(*)
        FROM (
            SELECT
                match_id,
                team_id,
                player_id,
                COUNT(*) AS rows
            FROM appearances
            GROUP BY
                match_id,
                team_id,
                player_id
            HAVING rows > 1
        )
        """
    )

    print_check(
        "Ingen dupliserte appearance-rader",
        duplicate_appearances == 0,
        f"{duplicate_appearances} avvik"
    )


    brann_starts = fetch_single(
        conn,
        """
        SELECT COUNT(*)
        FROM appearances
        WHERE
            team_id = ?
            AND starting = 1
        """,
        (BRANN_ID,)
    )

    brann_sub_apps = fetch_single(
        conn,
        """
        SELECT COUNT(*)
        FROM appearances
        WHERE
            team_id = ?
            AND starting = 0
            AND appeared = 1
        """,
        (BRANN_ID,)
    )

    brann_apps = fetch_single(
        conn,
        """
        SELECT COUNT(*)
        FROM appearances
        WHERE
            team_id = ?
            AND appeared = 1
        """,
        (BRANN_ID,)
    )

    reconstructed_brann = fetch_single(
        conn,
        """
        SELECT COUNT(*)
        FROM appearances
        WHERE
            team_id = ?
            AND appeared = 1
            AND listed_in_squad = 0
        """,
        (BRANN_ID,)
    )

    unknown_brann_starts = fetch_single(
        conn,
        """
        SELECT COUNT(*)
        FROM appearances
        WHERE
            team_id = ?
            AND appeared = 1
            AND starting IS NULL
        """,
        (BRANN_ID,)
    )

    print()
    print("-" * 72)
    print(f"Brann-startere:            {brann_starts}")
    print(f"Brann-innbytteropptred.:   {brann_sub_apps}")
    print(f"Brann-opptredener totalt:  {brann_apps}")
    print(f"Rekonstruert fra events:   {reconstructed_brann}")
    print(f"Ukjent Brann-startstatus:  {unknown_brann_starts}")
    print("-" * 72)


    starter_rows = conn.execute(
        """
        SELECT
            m.id AS match_id,
            m.date,
            ht.name AS home_team,
            at.name AS away_team,
            m.score,
            m.source_filename,
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
            m.id,
            m.date,
            ht.name,
            at.name,
            m.score,
            m.source_filename
        ORDER BY
            m.date
        """,
        (BRANN_ID,)
    ).fetchall()

    starter_distribution = Counter(
        row["starters"]
        for row in starter_rows
    )

    eligible_matches = starter_distribution[11]

    print()
    print("BRANN-STARTERE PER KAMP")
    print("-" * 72)

    for starters in sorted(starter_distribution):
        print(f"{starters:>2}: {starter_distribution[starters]}")

    print()
    print(
        "Game-eligible for Hvem mangler "
        f"(noyaktig 11 Brann-startere): {eligible_matches}"
    )

    for row in starter_rows:

        if row["starters"] == 11:
            continue

        add_issue(
            issues,
            "WARNING",
            "BRANN_STARTERS_NOT_11",
            row["date"],
            match_label(
                row["home_team"],
                row["away_team"],
                row["score"]
            ),
            row["match_id"],
            (
                f"Brann har {row['starters']} "
                "registrerte startere, ikke 11."
            ),
            row["source_filename"]
        )


    for row in conn.execute(
        """
        SELECT
            m.id AS match_id,
            m.date,
            ht.name AS home_team,
            at.name AS away_team,
            m.score,
            m.source_filename,
            p.name AS player_name
        FROM appearances a
        JOIN matches m
            ON m.id = a.match_id
        JOIN teams ht
            ON ht.id = m.home_team_id
        JOIN teams at
            ON at.id = m.away_team_id
        JOIN players p
            ON p.id = a.player_id
        WHERE
            a.team_id = ?
            AND a.appeared = 1
            AND a.starting IS NULL
        ORDER BY
            m.date,
            p.name
        """,
        (BRANN_ID,)
    ):

        add_issue(
            issues,
            "WARNING",
            "BRANN_UNKNOWN_START_STATUS",
            row["date"],
            match_label(
                row["home_team"],
                row["away_team"],
                row["score"]
            ),
            row["match_id"],
            (
                "Brann-spiller med opptreden, "
                f"men ukjent startstatus: {row['player_name']}"
            ),
            row["source_filename"]
        )


    event_checks = [
        (
            "REAL_EVENT_MISSING_TEAM",
            """
            SELECT
                m.id AS match_id,
                m.date,
                ht.name AS home_team,
                at.name AS away_team,
                m.score,
                m.source_filename,
                e.event_index,
                e.minute,
                e.event_name,
                e.event_type
            FROM events e
            JOIN matches m
                ON m.id = e.match_id
            JOIN teams ht
                ON ht.id = m.home_team_id
            JOIN teams at
                ON at.id = m.away_team_id
            WHERE
                e.event_type IS NOT NULL
                AND e.team_id IS NULL
            ORDER BY
                m.date,
                e.event_index
            """,
            "Kamphendelse mangler normalisert lag",
        ),
        (
            "GOAL_MISSING_SCORER",
            """
            SELECT
                m.id AS match_id,
                m.date,
                ht.name AS home_team,
                at.name AS away_team,
                m.score,
                m.source_filename,
                e.event_index,
                e.minute,
                e.event_name,
                e.event_type
            FROM events e
            JOIN matches m
                ON m.id = e.match_id
            JOIN teams ht
                ON ht.id = m.home_team_id
            JOIN teams at
                ON at.id = m.away_team_id
            WHERE
                e.event_type IN (
                    'goal',
                    'penaltyGoal',
                    'ownGoal'
                )
                AND e.scorer_id IS NULL
            ORDER BY
                m.date,
                e.event_index
            """,
            "Mal mangler malscorer",
        ),
        (
            "SUB_MISSING_SUB_ON",
            """
            SELECT
                m.id AS match_id,
                m.date,
                ht.name AS home_team,
                at.name AS away_team,
                m.score,
                m.source_filename,
                e.event_index,
                e.minute,
                e.event_name,
                e.event_type
            FROM events e
            JOIN matches m
                ON m.id = e.match_id
            JOIN teams ht
                ON ht.id = m.home_team_id
            JOIN teams at
                ON at.id = m.away_team_id
            WHERE
                e.event_type = 'subApp'
                AND e.sub_on_id IS NULL
            ORDER BY
                m.date,
                e.event_index
            """,
            "Bytte mangler subOn",
        ),
        (
            "SUB_MISSING_SUB_OFF",
            """
            SELECT
                m.id AS match_id,
                m.date,
                ht.name AS home_team,
                at.name AS away_team,
                m.score,
                m.source_filename,
                e.event_index,
                e.minute,
                e.event_name,
                e.event_type
            FROM events e
            JOIN matches m
                ON m.id = e.match_id
            JOIN teams ht
                ON ht.id = m.home_team_id
            JOIN teams at
                ON at.id = m.away_team_id
            WHERE
                e.event_type = 'subApp'
                AND e.sub_off_id IS NULL
            ORDER BY
                m.date,
                e.event_index
            """,
            "Bytte mangler subOff",
        ),
    ]

    for code, sql, text in event_checks:

        for row in conn.execute(sql):

            add_issue(
                issues,
                "WARNING",
                code,
                row["date"],
                match_label(
                    row["home_team"],
                    row["away_team"],
                    row["score"]
                ),
                row["match_id"],
                (
                    f"{text}. Event #{row['event_index']}, "
                    f"minutt {row['minute']}, "
                    f"type {row['event_type']}."
                ),
                row["source_filename"]
            )


    with REPORT_FILE.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "severity",
                "code",
                "date",
                "match",
                "match_id",
                "detail",
                "source_filename",
            ]
        )

        writer.writeheader()
        writer.writerows(issues)


    issue_counts = Counter(
        issue["code"]
        for issue in issues
    )

    print()
    print("AUDITFUNN")
    print("-" * 72)
    print(f"Rapport: {REPORT_FILE}")
    print(f"Funn totalt: {len(issues)}")

    for code, count in issue_counts.most_common():
        print(f"{count:>4} {code}")

    conn.close()


if __name__ == "__main__":
    audit()
