import json
from pathlib import Path


DATA_DIR = Path("data/raw")

FILES = [
    "2005-03-10_ifk-goeteborg-brann.json",
    "2011-06-27_sarpsborg-brann.json",
    "2020-06-17_haugesund-brann.json",
    "2020-07-05_glimt-brann.json",
    "2020-09-27_kristiansund-bk-brann.json",
    "2021-05-27_stabaek-brann.json",
]


for filename in FILES:

    filepath = DATA_DIR / filename

    with filepath.open("r", encoding="utf-8") as file:
        data = json.load(file)

    match = data["result"]["data"]["model"]

    print()
    print("=" * 80)
    print(
        f"{match['date']} – "
        f"{match['homeTeam']['name']}–"
        f"{match['awayTeam']['name']} "
        f"{match.get('score')}"
    )
    print("=" * 80)

    teams = {
        match["homeTeam"]["_id"]: match["homeTeam"]["name"],
        match["awayTeam"]["_id"]: match["awayTeam"]["name"],
    }

    for event in match.get("events", []):

        event_type = (
            event.get("type", {})
            .get("countAs")
        )

        problem = False

        if (
            event_type in ("goal", "penaltyGoal")
            and not event.get("scoredBy")
        ):
            problem = True

        if (
            event_type == "subApp"
            and not event.get("subOn")
        ):
            problem = True

        if not problem:
            continue

        team = event.get("team")
        team_id = team.get("_id") if team else None
        team_name = teams.get(team_id, "UKJENT LAG")

        print()
        print("PROBLEMHENDELSE")
        print(f"Type:    {event.get('type', {}).get('name')}")
        print(f"countAs: {event_type}")
        print(f"Minutt:  {event.get('time')}")
        print(f"Lag:     {team_name}")

        if event.get("scoredBy"):
            print(f"Mål:     {event['scoredBy']['name']}")
        else:
            print("Mål:     MANGLER")

        if event.get("subOn"):
            print(f"Inn:     {event['subOn']['name']}")
        else:
            print("Inn:     MANGLER")

        if event.get("subOff"):
            print(f"Ut:      {event['subOff']['name']}")
        else:
            print("Ut:      MANGLER")

        print()
        print("Rådata:")
        print(
            json.dumps(
                event,
                ensure_ascii=False,
                indent=2
            )
        )