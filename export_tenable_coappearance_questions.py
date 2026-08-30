import argparse
import sys
from collections import Counter, defaultdict

import tenable
from export_tenable_yaml_questions import NoAliasDumper, player_to_answer
from tenable_pages_config import QUESTION_SOURCE_DIR

try:
    import yaml

except ImportError as error:
    raise SystemExit(
        "PyYAML mangler. Kjor: python -m pip install -r requirements.txt"
    ) from error


DEFAULT_START_YEAR = tenable.DEFAULT_START_YEAR
DEFAULT_END_YEAR = tenable.MAX_YEAR
THEME_ID = "samspill-kamper"

TARGET_PLAYERS = [
    {
        "id": "erik-huseklepp",
        "player_id": "78f3154a-f1ee-5f8a-b869-8fedc39152de",
        "name": "Erik Huseklepp",
    },
    {
        "id": "erlend-hanstveit",
        "player_id": "514e9489-e37c-542d-aef9-c342394b4ed6",
        "name": "Erlend Hanstveit",
    },
    {
        "id": "hakon-opdal",
        "player_id": "83130615-4862-572c-9b4d-6f4b60ffc4aa",
        "name": "Håkon Opdal",
    },
    {
        "id": "fredrik-haugen",
        "player_id": "550adf62-a6ec-52e1-ae2d-f76c37d768f2",
        "name": "Fredrik Haugen",
    },
    {
        "id": "azar-karadas",
        "player_id": "e496d013-003d-50de-ab5a-007a70ce1ff6",
        "name": "Azar Karadas",
    },
    {
        "id": "ruben-kristiansen",
        "player_id": "22318baf-0826-5332-b876-46fbba0ca4dc",
        "name": "Ruben Kristiansen",
    },
    {
        "id": "geirmund-brendesater",
        "player_id": "9d7eedd0-2210-5e70-9b63-f001f676f56e",
        "name": "Geirmund Brendesæter",
    },
    {
        "id": "roy-wassberg",
        "player_id": "661d8b55-dfd8-5649-b812-805dc0a1b62a",
        "name": "Roy Wassberg",
    },
    {
        "id": "cato-guntveit",
        "player_id": "c8703a99-9114-52c6-9d4c-b32f58cad728",
        "name": "Cato Guntveit",
    },
]


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(
        encoding="utf-8",
        errors="replace"
    )


def query_appearances(database, start_date, end_date):

    return database["conn"].execute(
        """
        SELECT
            m.id AS match_id,
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
            end_date,
        )
    ).fetchall()


def load_appearance_index(start_year, end_year):

    databases = tenable.connect_databases(
        start_year,
        end_year
    )

    start_date, end_date = tenable.date_bounds(
        start_year,
        end_year
    )

    players = {}
    match_players = defaultdict(set)

    try:

        for database in databases:

            rows = query_appearances(
                database,
                start_date,
                end_date
            )

            for row in rows:

                player_id = row["player_id"]

                players[player_id] = {
                    "player_id": player_id,
                    "name": row["name"],
                    "full_name": row["full_name"],
                    "value": 0,
                }

                match_key = (
                    database["name"],
                    row["match_id"]
                )

                match_players[match_key].add(
                    player_id
                )

    finally:

        tenable.close_databases(
            databases
        )

    return players, match_players


def build_coappearance_rows(target_player_id, players, match_players):

    counts = Counter()
    target_match_count = 0

    for player_ids in match_players.values():

        if target_player_id not in player_ids:
            continue

        target_match_count += 1

        for player_id in player_ids:

            if player_id != target_player_id:
                counts[player_id] += 1

    rows = []

    for player_id, value in counts.items():

        if player_id not in players:
            raise ValueError(
                f"Mangler spillerdata for {player_id}."
            )

        row = dict(
            players[player_id]
        )
        row["value"] = value
        rows.append(row)

    return rows, target_match_count


def build_question(target, players, match_players, start_year, end_year):

    if target["player_id"] not in players:
        raise ValueError(
            f"Fant ikke {target['name']} i valgt periode."
        )

    rows, target_match_count = build_coappearance_rows(
        target["player_id"],
        players,
        match_players
    )

    answer_data = tenable.build_answer_slots(
        rows
    )

    if not answer_data["playable"]:
        raise ValueError(
            f"{target['name']}: {answer_data['reason']}"
        )

    return {
        "id": (
            f"{THEME_ID}:{target['id']}:"
            f"{start_year}:{end_year}"
        ),
        "active": True,
        "source": "database",
        "theme_id": THEME_ID,
        "title": (
            "Flest kamper sammen med "
            f"{target['name']}"
        ),
        "description": (
            "Finn de 10 Brann-spillerne som har spilt "
            f"flest kamper sammen med {target['name']}."
        ),
        "metric": "kamper",
        "start_year": start_year,
        "end_year": end_year,
        "coappearance_target": {
            "id": target["id"],
            "player_id": target["player_id"],
            "name": target["name"],
            "match_count": target_match_count,
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


def question_filename(target, start_year, end_year):

    if end_year == tenable.MAX_YEAR:
        range_label = f"since-{start_year}"
    else:
        range_label = f"{start_year}-{end_year}"

    return QUESTION_SOURCE_DIR / (
        f"{range_label}__samspill-med-{target['id']}.yaml"
    )


def write_question(question, target, start_year, end_year, overwrite):

    QUESTION_SOURCE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    path = question_filename(
        target,
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


def parse_args():

    parser = argparse.ArgumentParser(
        description=(
            "Eksporter Tenable-oppgaver for flest Brann-kamper "
            "sammen med en valgt Brann-spiller."
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

    players, match_players = load_appearance_index(
        args.start_year,
        args.end_year
    )

    total = 0

    for target in TARGET_PLAYERS:

        question = build_question(
            target,
            players,
            match_players,
            args.start_year,
            args.end_year
        )

        path = write_question(
            question,
            target,
            args.start_year,
            args.end_year,
            args.overwrite
        )

        first_answer = question["slots"][0]["answers"][0]["name"]

        print(
            f"Skrev {path}: #1 er {first_answer} "
            f"({question['slots'][0]['value']} kamper)"
        )

        total += 1

    print(
        f"Ferdig. Skrev {total} samspilloppgaver."
    )


if __name__ == "__main__":
    main()
