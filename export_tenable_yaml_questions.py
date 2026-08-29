import argparse
from copy import deepcopy

import tenable
from tenable_pages_config import (
    GENERAL_THEMES,
    OPPONENT_THEMES,
    PERIODS,
    QUESTION_SOURCE_DIR,
)

try:
    import yaml

except ImportError as error:
    raise SystemExit(
        "PyYAML mangler. Kjør: python -m pip install -r requirements.txt"
    ) from error


class NoAliasDumper(yaml.SafeDumper):

    def ignore_aliases(self, data):
        return True

    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(
            flow,
            False
        )


def player_to_answer(player):

    return {
        "player_id": player["player_id"],
        "name": player["name"],
        "full_name": player["full_name"],
    }


def question_filename(question, period):

    if question["end_year"] == tenable.MAX_YEAR:
        range_label = f"since-{question['start_year']}"
    else:
        range_label = (
            f"{question['start_year']}-"
            f"{question['end_year']}"
        )

    parts = [
        range_label,
        question["theme_id"].replace("_", "-"),
    ]

    if question["opponent"]:
        parts.append(
            question["opponent"]["slug"]
        )

    return QUESTION_SOURCE_DIR / ("__".join(parts) + ".yaml")


def build_question_id(question):

    parts = [
        question["theme_id"],
        str(question["start_year"]),
        str(question["end_year"]),
    ]

    if question["opponent"]:
        parts.append(
            question["opponent"]["slug"]
        )

    return ":".join(
        parts
    )


def question_to_yaml_data(question, period):

    data = {
        "id": build_question_id(
            question
        ),
        "active": True,
        "source": "database",
        "theme_id": question["theme_id"],
        "title": question["title"],
        "description": question["description"],
        "metric": question["metric"],
        "start_year": question["start_year"],
        "end_year": question["end_year"],
        "cutoff_value": question["cutoff_value"],
        "opponent": deepcopy(question["opponent"]),
        "slots": [],
    }

    for slot in question["slots"]:

        data["slots"].append(
            {
                "value": slot["value"],
                "answers": [
                    player_to_answer(
                        player
                    )
                    for player in slot["players"]
                ],
            }
        )

    return data


def build_selected_questions(period):

    databases = tenable.connect_databases(
        period["start_year"],
        period["end_year"]
    )

    questions = []

    try:

        for theme_id in GENERAL_THEMES:

            question = tenable.build_question(
                databases,
                theme_id,
                period["start_year"],
                period["end_year"]
            )

            if question["playable"]:
                questions.append(question)

        for theme in OPPONENT_THEMES:

            opponent = tenable.find_opponent(
                databases,
                theme["opponent"],
                period["start_year"],
                period["end_year"]
            )

            question = tenable.build_question(
                databases,
                theme["theme_id"],
                period["start_year"],
                period["end_year"],
                opponent
            )

            if question["playable"]:
                questions.append(question)

    finally:

        tenable.close_databases(
            databases
        )

    return questions


def write_question_file(question, period, overwrite):

    path = question_filename(
        question,
        period
    )

    if path.exists() and not overwrite:

        raise FileExistsError(
            f"Filen finnes allerede: {path}. "
            "Bruk --overwrite for å skrive den på nytt."
        )

    data = question_to_yaml_data(
        question,
        period
    )

    with path.open(
        "w",
        encoding="utf-8",
        newline="\n"
    ) as file:

        yaml.dump(
            data,
            file,
            Dumper=NoAliasDumper,
            allow_unicode=True,
            sort_keys=False,
            width=1000,
        )


def parse_args():

    parser = argparse.ArgumentParser(
        description=(
            "Eksporter dagens databasegenererte Tenable-betaoppgaver "
            "til redigerbare YAML-filer."
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

    QUESTION_SOURCE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    total = 0

    for period in PERIODS:

        questions = build_selected_questions(
            period
        )

        for question in questions:

            write_question_file(
                question,
                period,
                args.overwrite
            )
            total += 1

        print(
            f"{period['label']}: skrev {len(questions)} YAML-filer"
        )

    print(
        f"Ferdig. Skrev {total} filer til {QUESTION_SOURCE_DIR}"
    )


if __name__ == "__main__":
    main()
