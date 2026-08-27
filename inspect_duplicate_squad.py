import json
from collections import defaultdict
from pathlib import Path


FILE = Path(
    "data/raw/2026-08-23_fyllingen-brann.json"
)


with FILE.open("r", encoding="utf-8") as file:
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


for side in ["home", "away"]:

    if side == "home":
        team = match["homeTeam"]
        squad = match.get("homeSquad") or []
    else:
        team = match["awayTeam"]
        squad = match.get("awaySquad") or []

    print()
    print(f"{team['name'].upper()}")
    print("-" * 80)

    by_player = defaultdict(list)

    for index, entry in enumerate(squad):

        player = entry.get("player")

        if not player:
            continue

        player_id = player.get("_id")

        if player_id:
            by_player[player_id].append(
                (index, entry)
            )

    duplicates = {
        player_id: entries
        for player_id, entries in by_player.items()
        if len(entries) > 1
    }

    if not duplicates:
        print("Ingen dupliserte spiller-ID-er.")
        continue

    for player_id, entries in duplicates.items():

        player = entries[0][1]["player"]

        print()
        print(
            f"DUPLIKAT: {player.get('name')}"
        )
        print(
            f"ID:       {player_id}"
        )
        print(
            f"Antall:   {len(entries)}"
        )

        for index, entry in entries:

            role = entry.get("role") or {}

            print()
            print(f"Troppsindeks: {index}")
            print(f"Draktnr:      {entry.get('shirt')}")
            print(f"Role name:    {role.get('name')}")
            print(f"Role abbr:    {role.get('abbr')}")
            print(f"Starting:     {role.get('starting')}")
            print(f"Role sort:    {role.get('sort')}")

            print()
            print("Rå oppføring:")
            print(
                json.dumps(
                    entry,
                    ensure_ascii=False,
                    indent=2
                )
            )