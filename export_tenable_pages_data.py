import json
from datetime import datetime, timezone

import tenable
from tenable_pages_config import (
    OUTPUT_FILE,
    QUESTION_SOURCE_DIR,
)

try:
    import yaml

except ImportError as error:
    raise SystemExit(
        "PyYAML mangler. Kjør: python -m pip install -r requirements.txt"
    ) from error


def year_phrase(start_year, end_year):

    if end_year == tenable.MAX_YEAR:
        return f"siden {start_year}"

    return f"i perioden {start_year}-{end_year}"


def add_period_to_description(description, start_year, end_year):

    phrase = year_phrase(
        start_year,
        end_year
    )

    text = description.strip()

    if phrase in text:
        return text

    if text.endswith("."):
        text = text[:-1]

    return f"{text} {phrase}."


def answer_name(answer, source_file):

    name = answer.get("name")

    if not name:
        raise ValueError(
            f"Mangler answer.name i {source_file}"
        )

    return name


def answer_id(answer, question_id, fallback_ids, source_file):

    explicit_id = (
        answer.get("id")
        or answer.get("player_id")
    )

    if explicit_id:
        return explicit_id

    key = tenable.normalize_text(
        answer_name(
            answer,
            source_file
        )
    )

    if key not in fallback_ids:
        fallback_ids[key] = (
            f"custom:{question_id}:"
            f"{len(fallback_ids) + 1}"
        )

    return fallback_ids[key]


def serialize_answer(answer, value, question_id, fallback_ids, source_file):

    aliases = answer.get(
        "aliases",
        []
    )

    if aliases is None:
        aliases = []

    if not isinstance(aliases, list):
        raise ValueError(
            f"aliases må være en liste i {source_file}"
        )

    return {
        "id": answer_id(
            answer,
            question_id,
            fallback_ids,
            source_file
        ),
        "name": answer_name(
            answer,
            source_file
        ),
        "fullName": (
            answer.get("fullName")
            or answer.get("full_name")
        ),
        "aliases": aliases,
        "value": value,
    }


def serialize_question(source):

    source_file = source["_source_file"]
    question_id = source.get("id")

    if not question_id:
        raise ValueError(
            f"Mangler id i {source_file}"
        )

    slots = source.get("slots")

    if not isinstance(slots, list):
        raise ValueError(
            f"slots må være en liste i {source_file}"
        )

    if len(slots) != tenable.ANSWER_COUNT:
        raise ValueError(
            f"{source_file} har {len(slots)} slots. "
            f"Forventet {tenable.ANSWER_COUNT}."
        )

    start_year = source.get("start_year")
    end_year = source.get("end_year")

    if not isinstance(start_year, int) or not isinstance(end_year, int):
        raise ValueError(
            f"{source_file} må ha start_year og end_year som årstall."
        )

    if start_year > end_year:
        raise ValueError(
            f"{source_file} har start_year etter end_year."
        )

    fallback_ids = {}
    serialized_slots = []

    for slot in slots:

        value = slot.get("value")
        answers = slot.get("answers")

        if not isinstance(answers, list) or not answers:
            raise ValueError(
                f"Slot mangler answers-liste i {source_file}"
            )

        serialized_slots.append(
            {
                "value": value,
                "players": [
                    serialize_answer(
                        answer,
                        value,
                        question_id,
                        fallback_ids,
                        source_file
                    )
                    for answer in answers
                ],
            }
        )

    eligible_by_id = {}

    for slot in serialized_slots:

        for player in slot["players"]:
            eligible_by_id[player["id"]] = player

    return {
        "id": question_id,
        "themeId": source.get(
            "theme_id",
            "custom"
        ),
        "title": source["title"],
        "description": add_period_to_description(
            source["description"],
            start_year,
            end_year
        ),
        "metric": source["metric"],
        "startYear": start_year,
        "endYear": end_year,
        "yearLabel": year_phrase(
            start_year,
            end_year
        ),
        "playerPoolId": player_pool_id(
            start_year,
            end_year
        ),
        "cutoffValue": source.get(
            "cutoff_value",
            serialized_slots[-1]["value"]
        ),
        "opponent": source.get(
            "opponent"
        ),
        "slots": serialized_slots,
        "eligibleAnswers": list(
            eligible_by_id.values()
        ),
    }


def load_question_file(path):

    with path.open(
        "r",
        encoding="utf-8"
    ) as file:

        data = yaml.safe_load(file)

    if not isinstance(data, dict):
        raise ValueError(
            f"{path} må inneholde ett YAML-objekt."
        )

    data["_source_file"] = str(path)

    return data


def load_question_sources():

    if not QUESTION_SOURCE_DIR.exists():
        raise FileNotFoundError(
            f"Fant ikke Tenable-mappen: {QUESTION_SOURCE_DIR}. "
            "Kjør python export_tenable_yaml_questions.py først."
        )

    sources = []

    for path in sorted(
        QUESTION_SOURCE_DIR.glob("*.yaml")
    ):

        source = load_question_file(
            path
        )

        if source.get("active", True):
            sources.append(source)

    if not sources:
        raise ValueError(
            f"Fant ingen aktive YAML-oppgaver i {QUESTION_SOURCE_DIR}."
        )

    return sources


def player_pool_id(start_year, end_year):

    return f"{start_year}-{end_year}"


def serialize_player_option(player):

    return {
        "id": player["player_id"],
        "name": player["name"],
        "fullName": player["full_name"],
    }


def query_player_pool(start_year, end_year):

    databases = tenable.connect_databases(
        start_year,
        end_year
    )

    start_date, end_date = tenable.date_bounds(
        start_year,
        end_year
    )

    players_by_id = {}

    try:

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

    finally:

        tenable.close_databases(
            databases
        )

    return sorted(
        players_by_id.values(),
        key=lambda player: (
            tenable.normalize_text(player["name"]),
            player["player_id"]
        )
    )


def build_player_pools(questions):

    ranges = sorted(
        {
            (
                question["startYear"],
                question["endYear"]
            )
            for question in questions
        }
    )

    pools = {}

    for start_year, end_year in ranges:

        pools[
            player_pool_id(
                start_year,
                end_year
            )
        ] = [
            serialize_player_option(
                player
            )
            for player in query_player_pool(
                start_year,
                end_year
            )
        ]

    return pools


def main():

    sources = load_question_sources()
    questions = [
        serialize_question(
            source
        )
        for source in sources
    ]

    data = {
        "generatedAt": datetime.now(
            timezone.utc
        ).isoformat(),
        "answerCount": tenable.ANSWER_COUNT,
        "startingLives": tenable.STARTING_LIVES,
        "playerPools": build_player_pools(
            questions
        ),
        "questions": questions,
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

    print(
        f"Exported {len(questions)} Tenable questions "
        f"to {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
