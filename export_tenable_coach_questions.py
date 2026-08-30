import argparse
import sys
from pathlib import Path

import tenable
from export_tenable_yaml_questions import NoAliasDumper, player_to_answer
from tenable_pages_config import QUESTION_SOURCE_DIR

try:
    import yaml

except ImportError as error:
    raise SystemExit(
        "PyYAML mangler. Kjor: python -m pip install -r requirements.txt"
    ) from error


COACH_SOURCE_FILE = Path("data/tenable/coaches.yaml")
DEFAULT_THEMES = ["kamper", "maal"]


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(
        encoding="utf-8",
        errors="replace"
    )


def load_coaches():

    with COACH_SOURCE_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:
        data = yaml.safe_load(file)

    coaches = data.get(
        "coaches",
        []
    )

    if not coaches:
        raise ValueError(
            f"Fant ingen trenere i {COACH_SOURCE_FILE}."
        )

    return coaches


def match_by_source_filename(databases, source_filename):

    matches = []

    for database in databases:

        rows = database["conn"].execute(
            """
            SELECT
                id,
                date,
                source_filename

            FROM matches

            WHERE source_filename = ?
            """,
            (
                source_filename,
            )
        ).fetchall()

        matches.extend(
            rows
        )

    if len(matches) != 1:
        raise ValueError(
            f"Forventet ett treff for {source_filename}, "
            f"fant {len(matches)}."
        )

    return matches[0]


def latest_match(databases):

    matches = []

    for database in databases:

        row = database["conn"].execute(
            """
            SELECT
                id,
                date,
                source_filename

            FROM matches

            ORDER BY
                date DESC,
                source_filename DESC

            LIMIT 1
            """
        ).fetchone()

        if row:
            matches.append(row)

    if not matches:
        raise ValueError(
            "Fant ingen kamper i databasene."
        )

    return sorted(
        matches,
        key=lambda match: (
            match["date"],
            match["source_filename"]
        ),
        reverse=True
    )[0]


def raw_coach_periods(coach):

    periods = coach.get(
        "periods"
    )

    if periods is None:
        periods = [
            {
                "id": "main",
                "from_match": coach["from_match"],
                "to_match": coach["to_match"],
            }
        ]

    if not isinstance(periods, list) or not periods:
        raise ValueError(
            f"{coach['name']} mangler trenerperioder."
        )

    return periods


def coach_date_bounds(coach):

    databases = tenable.connect_databases(
        tenable.MIN_YEAR,
        tenable.MAX_YEAR
    )

    try:

        latest = latest_match(
            databases
        )
        periods = []

        for period in raw_coach_periods(
            coach
        ):

            from_match = match_by_source_filename(
                databases,
                period["from_match"]
            )

            if period.get("to_match"):
                to_match = match_by_source_filename(
                    databases,
                    period["to_match"]
                )
            else:
                to_match = latest

            if from_match["date"] > to_match["date"]:
                raise ValueError(
                    f"Trenerperioden for {coach['name']} starter "
                    "etter sluttkampen."
                )

            periods.append(
                {
                    "id": period.get("id", "main"),
                    "from_match": period["from_match"],
                    "to_match": period.get("to_match"),
                    "from_date": from_match["date"],
                    "to_date": to_match["date"],
                    "current": bool(
                        period.get("current")
                        or not period.get("to_match")
                    ),
                }
            )

    finally:

        tenable.close_databases(
            databases
        )

    return periods


def query_appearances(database, start_date, end_date):

    return database["conn"].execute(
        """
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
        (
            tenable.BRANN_ID,
            start_date,
            end_date,
        )
    ).fetchall()


def query_goals(database, start_date, end_date):

    return database["conn"].execute(
        """
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
        (
            tenable.BRANN_ID,
            start_date,
            end_date,
        )
    ).fetchall()


def query_theme(database, theme_id, start_date, end_date):

    if theme_id == "kamper":
        return query_appearances(
            database,
            start_date,
            end_date
        )

    if theme_id == "maal":
        return query_goals(
            database,
            start_date,
            end_date
        )

    raise ValueError(
        f"Ukjent coach-tema: {theme_id}"
    )


def build_slots(rows):

    answer_data = tenable.build_answer_slots(
        tenable.combine_rows(
            rows
        )
    )

    if not answer_data["playable"]:
        raise ValueError(
            "Treneroppgaven har faerre enn 10 svar."
        )

    return answer_data


def metric_for_theme(theme_id):

    if theme_id == "kamper":
        return "kamper"

    if theme_id == "maal":
        return "mål"

    raise ValueError(
        f"Ukjent coach-tema: {theme_id}"
    )


def title_for_theme(theme_id, coach_name):

    if theme_id == "kamper":
        return f"Flest kamper under {coach_name}"

    if theme_id == "maal":
        return f"Flest mål under {coach_name}"

    raise ValueError(
        f"Ukjent coach-tema: {theme_id}"
    )


def description_for_theme(theme_id, coach_name):

    if theme_id == "kamper":
        return (
            "Finn de 10 spillerne med flest Brann-kamper "
            f"under {coach_name}."
        )

    if theme_id == "maal":
        return (
            "Finn de 10 spillerne med flest Brann-mål "
            f"under {coach_name}."
        )

    raise ValueError(
        f"Ukjent coach-tema: {theme_id}"
    )


def build_question(coach, theme_id):

    periods = coach_date_bounds(
        coach
    )
    start_date = min(
        period["from_date"]
        for period in periods
    )
    end_date = max(
        period["to_date"]
        for period in periods
    )

    start_year = int(
        start_date[:4]
    )
    end_year = int(
        end_date[:4]
    )

    databases = tenable.connect_databases(
        start_year,
        end_year
    )

    rows = []

    try:

        for database in databases:

            for period in periods:
                rows.extend(
                    query_theme(
                        database,
                        theme_id,
                        period["from_date"],
                        period["to_date"]
                    )
                )

    finally:

        tenable.close_databases(
            databases
        )

    answer_data = build_slots(
        rows
    )

    question_theme = f"trener-{theme_id}"

    return {
        "id": (
            f"{question_theme}:{coach['id']}:"
            f"{start_date}:{end_date}"
        ),
        "active": True,
        "source": "database_with_manual_coach_period",
        "theme_id": question_theme,
        "title": title_for_theme(
            theme_id,
            coach["name"]
        ),
        "description": description_for_theme(
            theme_id,
            coach["name"]
        ),
        "metric": metric_for_theme(
            theme_id
        ),
        "start_year": start_year,
        "end_year": end_year,
        "coach": {
            "id": coach["id"],
            "name": coach["name"],
            "from_date": start_date,
            "to_date": end_date,
            "periods": periods,
        },
        "cutoff_value": answer_data["cutoff_value"],
        "opponent": None,
        "slots": [
            {
                "value": slot["value"],
                "answers": [
                    player_to_answer(
                        player
                    )
                    for player in slot["players"]
                ],
            }
            for slot in answer_data["slots"]
        ],
    }


def filename_for_question(question, coach, theme_id):

    return QUESTION_SOURCE_DIR / (
        f"{coach['id']}__trener-{theme_id}.yaml"
    )


def write_question(question, coach, theme_id, overwrite):

    QUESTION_SOURCE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    path = filename_for_question(
        question,
        coach,
        theme_id
    )

    if path.exists() and not overwrite:
        raise FileExistsError(
            f"Filen finnes allerede: {path}. "
            "Bruk --overwrite for a skrive den pa nytt."
        )

    with path.open(
        "w",
        encoding="utf-8",
        newline="\n"
    ) as file:

        yaml.dump(
            question,
            file,
            Dumper=NoAliasDumper,
            allow_unicode=True,
            sort_keys=False,
            width=1000,
        )

    return path


def parse_args():

    parser = argparse.ArgumentParser(
        description=(
            "Eksporter Tenable-oppgaver basert pa "
            "manuelt definerte trenerperioder."
        )
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Skriv over eksisterende YAML-filer med samme navn."
    )

    return parser.parse_args()


def main():

    args = parse_args()
    coaches = load_coaches()

    total = 0

    for coach in coaches:

        if not coach.get(
            "tenable_questions",
            True
        ):
            continue

        for theme_id in DEFAULT_THEMES:

            question = build_question(
                coach,
                theme_id
            )

            path = write_question(
                question,
                coach,
                theme_id,
                args.overwrite
            )

            first_answer = (
                question["slots"][0]["answers"][0]["name"]
            )

            print(
                f"Skrev {path}: #1 er {first_answer} "
                f"({question['slots'][0]['value']} "
                f"{question['metric']})"
            )

            total += 1

    print(
        f"Ferdig. Skrev {total} treneroppgaver."
    )


if __name__ == "__main__":
    main()
