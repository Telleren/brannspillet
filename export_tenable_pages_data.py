import json
from datetime import datetime, timezone
from pathlib import Path

import tenable


OUTPUT_FILE = Path("docs/tenable/questions.json")

PERIODS = [
    {
        "id": "classic",
        "label": "Classic",
        "start_year": 1963,
        "end_year": 2026,
    },
    {
        "id": "modern",
        "label": "Moderne",
        "start_year": 2000,
        "end_year": 2026,
    },
]

GENERAL_THEMES = [
    "kamper",
    "starter",
    "innhopp",
    "maal",
    "seire",
    "utlendinger-kamper",
    "utlendinger-maal",
    "brannspillere-mot-brann",
]

OPPONENT_THEMES = [
    {
        "theme_id": "kamper-mot",
        "opponent": "Rosenborg",
    },
    {
        "theme_id": "kamper-mot",
        "opponent": "Lillestrøm",
    },
    {
        "theme_id": "kamper-mot",
        "opponent": "Viking",
    },
    {
        "theme_id": "kamper-mot",
        "opponent": "Vålerenga",
    },
]


def serialize_player(player):

    return {
        "id": player["player_id"],
        "name": player["name"],
        "fullName": player["full_name"],
        "value": player["value"],
    }


def serialize_player_option(player):

    return {
        "id": player["player_id"],
        "name": player["name"],
        "fullName": player["full_name"],
    }


def add_period_to_description(description, start_year, end_year):

    text = description.strip()

    if text.endswith("."):
        text = text[:-1]

    return f"{text} i perioden {start_year}-{end_year}."


def serialize_question(question):

    return {
        "id": build_question_id(
            question
        ),
        "themeId": question["theme_id"],
        "title": question["title"],
        "description": add_period_to_description(
            question["description"],
            question["start_year"],
            question["end_year"]
        ),
        "metric": question["metric"],
        "startYear": question["start_year"],
        "endYear": question["end_year"],
        "cutoffValue": question["cutoff_value"],
        "opponent": question["opponent"],
        "slots": [
            {
                "value": slot["value"],
                "players": [
                    serialize_player(
                        player
                    )
                    for player in slot["players"]
                ],
            }
            for slot in question["slots"]
        ],
        "eligibleAnswers": [
            serialize_player(
                player
            )
            for player in question["eligible_answers"]
        ],
    }


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


def query_player_pool(databases, start_year, end_year):

    start_date, end_date = tenable.date_bounds(
        start_year,
        end_year
    )

    players_by_id = {}

    for database in databases:

        rows = database["conn"].execute(
            """
            SELECT DISTINCT
                p.id AS player_id,
                p.name,
                p.full_name

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
            """,
            (
                tenable.BRANN_ID,
                start_date,
                end_date
            )
        ).fetchall()

        for row in rows:
            players_by_id[row["player_id"]] = row

    return sorted(
        players_by_id.values(),
        key=lambda player: (
            tenable.normalize_text(player["name"]),
            player["player_id"]
        )
    )


def build_period(period):

    databases = tenable.connect_databases(
        period["start_year"],
        period["end_year"]
    )

    questions = []
    player_pool = []

    try:

        player_pool = query_player_pool(
            databases,
            period["start_year"],
            period["end_year"]
        )

        for theme_id in GENERAL_THEMES:

            question = tenable.build_question(
                databases,
                theme_id,
                period["start_year"],
                period["end_year"]
            )

            if question["playable"]:
                questions.append(
                    serialize_question(
                        question
                    )
                )

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
                questions.append(
                    serialize_question(
                        question
                    )
                )

    finally:

        tenable.close_databases(
            databases
        )

    return {
        **period,
        "playerPool": [
            serialize_player_option(
                player
            )
            for player in player_pool
        ],
        "questions": questions,
    }


def main():

    data = {
        "generatedAt": datetime.now(
            timezone.utc
        ).isoformat(),
        "answerCount": tenable.ANSWER_COUNT,
        "startingLives": tenable.STARTING_LIVES,
        "periods": [
            build_period(
                period
            )
            for period in PERIODS
        ],
    }

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

    total = sum(
        len(period["questions"])
        for period in data["periods"]
    )

    print(
        f"Exported {total} Tenable questions "
        f"to {OUTPUT_FILE}"
    )

    for period in data["periods"]:

        print(
            f"{period['label']}: "
            f"{len(period['questions'])} questions"
        )


if __name__ == "__main__":
    main()
