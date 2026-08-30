import argparse
import json
import sys
from pathlib import Path

import tenable
from export_tenable_yaml_questions import NoAliasDumper
from tenable_pages_config import QUESTION_SOURCE_DIR

try:
    import yaml

except ImportError as error:
    raise SystemExit(
        "PyYAML mangler. Kjor: python -m pip install -r requirements.txt"
    ) from error


DEFAULT_START_YEAR = tenable.DEFAULT_START_YEAR
DEFAULT_END_YEAR = tenable.MAX_YEAR
DEFAULT_SHIRT_NUMBERS = [
    *range(1, 13),
    14,
    15,
    16,
    18,
    19,
    20,
    22,
    23,
    25,
    26,
]
SHIRT_NUMBER_CORRECTIONS_FILE = Path(
    "data/shirt_number_corrections.json"
)


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(
        encoding="utf-8",
        errors="replace"
    )


def load_shirt_number_corrections():

    if not SHIRT_NUMBER_CORRECTIONS_FILE.exists():
        return {}

    with SHIRT_NUMBER_CORRECTIONS_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:
        data = json.load(file)

    corrections = {}

    for correction in data.get("corrections", []):

        key = (
            correction["source_filename"],
            correction["match_date"],
            correction["team_id"],
            correction["player_id"],
            correction["raw_shirt_number"],
        )

        if key in corrections:
            raise ValueError(
                "Duplicate shirt-number correction: "
                f"{correction['id']}"
            )

        corrections[key] = correction["corrected_shirt_number"]

    return corrections


def corrected_shirt_number(row, corrections):

    key = (
        row["source_filename"],
        row["match_date"],
        row["team_id"],
        row["player_id"],
        row["shirt_number"],
    )

    return corrections.get(
        key,
        row["shirt_number"]
    )


def query_database(database, start_date, end_date):

    return database["conn"].execute(
        """
        SELECT
            p.id AS player_id,
            p.name,
            p.full_name,
            m.date AS match_date,
            m.source_filename,
            a.team_id,
            a.shirt_number

        FROM appearances a

        JOIN matches m
            ON m.id = a.match_id

        JOIN players p
            ON p.id = a.player_id

        WHERE
            a.team_id = ?
            AND a.appeared = 1
            AND a.shirt_number IS NOT NULL
            AND m.date >= ?
            AND m.date <= ?
        """,
        (
            tenable.BRANN_ID,
            start_date,
            end_date,
        )
    ).fetchall()


def combine_player_rows(rows, shirt_number, corrections):

    players = {}

    for row in rows:

        if corrected_shirt_number(
            row,
            corrections
        ) != shirt_number:
            continue

        player_id = row["player_id"]

        if player_id not in players:
            players[player_id] = {
                "player_id": player_id,
                "name": row["name"],
                "full_name": row["full_name"],
                "latest_date": row["match_date"],
                "match_count": 0,
            }

        player = players[player_id]
        player["match_count"] += 1

        if row["match_date"] > player["latest_date"]:
            player["latest_date"] = row["match_date"]

    return sorted(
        players.values(),
        key=lambda player: (
            player["latest_date"],
            tenable.normalize_text(player["name"]),
            player["player_id"],
        ),
        reverse=True
    )


def build_shirt_number_question(shirt_number, start_year, end_year):

    databases = tenable.connect_databases(
        start_year,
        end_year
    )

    start_date, end_date = tenable.date_bounds(
        start_year,
        end_year
    )

    rows = []
    corrections = load_shirt_number_corrections()

    try:

        for database in databases:
            rows.extend(
                query_database(
                    database,
                    start_date,
                    end_date
                )
            )

    finally:

        tenable.close_databases(
            databases
        )

    players = combine_player_rows(
        rows,
        shirt_number,
        corrections
    )

    if len(players) < tenable.ANSWER_COUNT:
        raise ValueError(
            f"Fant bare {len(players)} unike spillere med "
            f"draktnummer {shirt_number} i {start_year}-{end_year}."
        )

    selected = players[:tenable.ANSWER_COUNT]

    return {
        "id": (
            f"draktnummer-{shirt_number}:"
            f"{start_year}:{end_year}"
        ),
        "active": True,
        "source": "database",
        "theme_id": f"draktnummer-{shirt_number}",
        "title": (
            "De 10 siste Brann-spillerne med "
            f"draktnummer {shirt_number}"
        ),
        "description": (
            "Finn de 10 siste unike Brann-spillerne "
            f"som har spilt med draktnummer {shirt_number}."
        ),
        "metric": "",
        "start_year": start_year,
        "end_year": end_year,
        "cutoff_value": selected[-1]["latest_date"],
        "opponent": None,
        "slots": [
            {
                "value": player["latest_date"],
                "answers": [
                    {
                        "player_id": player["player_id"],
                        "name": player["name"],
                        "full_name": player["full_name"],
                    }
                ],
            }
            for player in selected
        ],
    }


def question_filename(shirt_number, start_year, end_year):

    if end_year == tenable.MAX_YEAR:
        range_label = f"since-{start_year}"
    else:
        range_label = f"{start_year}-{end_year}"

    return QUESTION_SOURCE_DIR / (
        f"{range_label}__draktnummer-{shirt_number}.yaml"
    )


def write_question(question, shirt_number, start_year, end_year, overwrite):

    QUESTION_SOURCE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    path = question_filename(
        shirt_number,
        start_year,
        end_year
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


def parse_shirt_numbers(values):

    numbers = []

    for value in values:

        number = int(value)

        if number < 1:
            raise ValueError(
                "Draktnummer ma vaere 1 eller hoyere."
            )

        numbers.append(number)

    return numbers


def parse_args():

    parser = argparse.ArgumentParser(
        description=(
            "Eksporter Tenable-oppgaver for siste unike "
            "Brann-spillere med et gitt draktnummer."
        )
    )

    parser.add_argument(
        "shirt_numbers",
        nargs="*",
        help=(
            "Draktnummer som skal eksporteres. "
            "Standard er dagens publiserte draktnummerserie."
        )
    )
    parser.add_argument(
        "--start-year",
        type=int,
        default=DEFAULT_START_YEAR,
        help=f"Startar. Standard: {DEFAULT_START_YEAR}."
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=DEFAULT_END_YEAR,
        help=f"Sluttar. Standard: {DEFAULT_END_YEAR}."
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Skriv over eksisterende YAML-filer med samme navn."
    )

    return parser.parse_args()


def main():

    args = parse_args()

    if args.start_year > args.end_year:
        raise ValueError(
            "--start-year kan ikke vaere etter --end-year."
        )

    shirt_numbers = (
        parse_shirt_numbers(
            args.shirt_numbers
        )
        if args.shirt_numbers
        else DEFAULT_SHIRT_NUMBERS
    )

    for shirt_number in shirt_numbers:

        question = build_shirt_number_question(
            shirt_number,
            args.start_year,
            args.end_year
        )

        path = write_question(
            question,
            shirt_number,
            args.start_year,
            args.end_year,
            args.overwrite
        )

        first_answer = question["slots"][0]["answers"][0]["name"]

        print(
            f"Skrev {path}: #1 er {first_answer} "
            f"({question['slots'][0]['value']})"
        )


if __name__ == "__main__":
    main()
