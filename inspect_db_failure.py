import json
from pathlib import Path


FILE = Path(
    "data/raw/2019-05-01_arna-bjornar-brann.json"
)


with FILE.open("r", encoding="utf-8") as file:
    data = json.load(file)


match = data["result"]["data"]["model"]

home = match["homeTeam"]
away = match["awayTeam"]


print()
print("=" * 80)
print(
    f"{match['date']} – "
    f"{home['name']}–{away['name']} "
    f"{match.get('score')}"
)
print("=" * 80)

print()
print("LAGENE I KAMPEN")
print("-" * 80)

print(
    f"Hjemme: {home['name']}"
)
print(
    f"ID:     {home['_id']}"
)

print()

print(
    f"Borte:  {away['name']}"
)
print(
    f"ID:     {away['_id']}"
)


valid_team_ids = {
    home["_id"],
    away["_id"]
}


print()
print("EVENTS")
print("-" * 80)


for index, event in enumerate(
    match.get("events", [])
):

    event_type = (
        event.get("type", {})
        .get("countAs")
    )

    event_name = (
        event.get("type", {})
        .get("name")
    )

    team = event.get("team")

    team_id = (
        team.get("_id")
        if team
        else None
    )


    print()
    print(f"Event #{index}")

    print(
        f"Minutt: {event.get('time')}"
    )

    print(
        f"Type:   {event_name} "
        f"({event_type})"
    )

    print(
        f"Team-ID: {team_id}"
    )


    if (
        team_id
        and team_id not in valid_team_ids
    ):

        print()
        print(
            ">>> PROBLEM: "
            "Denne Team-ID-en er verken "
            "hjemmelaget eller bortelaget!"
        )


    for field in [
        "player",
        "scoredBy",
        "assistedBy",
        "subOn",
        "subOff"
    ]:

        player = event.get(field)

        if player:

            print(
                f"{field}: "
                f"{player.get('name')} "
                f"[{player.get('_id')}]"
            )


    print()
    print("Rådata:")

    print(
        json.dumps(
            event,
            ensure_ascii=False,
            indent=2
        )
    )