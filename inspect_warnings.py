import json
from pathlib import Path


FILES = [
    "2002-08-08_brann-aalesund.json",
    "2004-06-24_glimt-brann.json",
    "2005-03-10_ifk-goeteborg-brann.json",
]

DATA_DIR = Path("data/raw")


for filename in FILES:

    filepath = DATA_DIR / filename

    print()
    print("=" * 80)
    print(filename)
    print("=" * 80)

    with filepath.open(
        "r",
        encoding="utf-8"
    ) as file:
        data = json.load(file)

    match = data["result"]["data"]["model"]

    print(
        f"{match['date']} – "
        f"{match['homeTeam']['name']}–"
        f"{match['awayTeam']['name']} "
        f"{match.get('score')}"
    )

    print()

    for event in match.get("events", []):

        event_type = (
            event.get("type", {})
            .get("countAs")
        )

        team = event.get("team")
        scored_by = event.get("scoredBy")

        problem = False

        if not team or not team.get("_id"):
            problem = True

        if event_type is None:
            print("HENDELSE UTEN countAs:")
            print(
                json.dumps(
                    event,
                    ensure_ascii=False,
                    indent=2
                )
            )
            print()    

        if (
            event_type in ["goal", "penaltyGoal"]
            and not scored_by
        ):
            problem = True

        if problem:
            print("PROBLEMATISK HENDELSE:")
            print(
                json.dumps(
                    event,
                    ensure_ascii=False,
                    indent=2
                )
            )
            print()