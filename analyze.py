import json
from collections import Counter
from pathlib import Path


DATA_DIR = Path("data/raw")

BRANN_ID = "05bb57f9-3430-5a18-b77c-96b578525b9c"


matches = []
players = {}
opponents = {}
competitions = Counter()

starts = Counter()
appearances = Counter()
unused_subs = Counter()
goals = Counter()


for filepath in sorted(DATA_DIR.glob("*.json")):

    with filepath.open(
        "r",
        encoding="utf-8"
    ) as file:
        data = json.load(file)

    # VIKTIG:
    # Vi bruker bare selve kampen under "model".
    # JSON-filen inneholder også prev/next,
    # som ellers ville gitt dobbeltelling.
    match = data["result"]["data"]["model"]

    matches.append(match)

    competition = match.get("competition")

    if competition:
        competitions[competition["name"]] += 1

    home_team = match["homeTeam"]
    away_team = match["awayTeam"]

    if home_team["_id"] == BRANN_ID:
        brann_squad = match["homeSquad"]
        opponent = away_team
    else:
        brann_squad = match["awaySquad"]
        opponent = home_team

    opponents[opponent["_id"]] = opponent["name"]

    #
    # 1. Registrer alle Brann-spillere
    #
    for squad_entry in brann_squad:

        player = squad_entry["player"]
        player_id = player["_id"]

        players[player_id] = {
            "name": player["name"],
            "birthdate": player.get("birthdate"),
            "birthplace": player.get("birthplace"),
            "countryCode": player.get("countryCode"),
        }

        role = squad_entry.get("role")

        if role and role.get("starting") is True:
            starts[player_id] += 1
            appearances[player_id] += 1

        else:
            unused_subs[player_id] += 1

    #
    # 2. Registrer innbyttere og mål
    #
    for event in match.get("events", []):

        event_type = event.get("type", {})
        count_as = event_type.get("countAs")

        team = event.get("team")

        if not team:
            continue

        team_id = team.get("_id")

        #
        # Innbytte for Brann
        #
        if (
            count_as == "subApp"
            and team_id == BRANN_ID
        ):

            sub_on = event.get("subOn")

            if sub_on:
                player_id = sub_on["_id"]

                players[player_id] = {
                    "name": sub_on["name"],
                    "birthdate": sub_on.get("birthdate"),
                    "birthplace": sub_on.get("birthplace"),
                    "countryCode": sub_on.get("countryCode"),
                }

                appearances[player_id] += 1

                # Spilleren var registrert som reserve,
                # men ble faktisk brukt.
                if unused_subs[player_id] > 0:
                    unused_subs[player_id] -= 1

        #
        # Brann-mål
        #
        if (
            count_as in ["goal", "penaltyGoal"]
            and team_id == BRANN_ID
        ):

            scorer = event.get("scoredBy")

            if scorer:
                player_id = scorer["_id"]

                players[player_id] = {
                    "name": scorer["name"],
                    "birthdate": scorer.get("birthdate"),
                    "birthplace": scorer.get("birthplace"),
                    "countryCode": scorer.get("countryCode"),
                }

                goals[player_id] += 1


print()
print("=" * 60)
print("BRANNSPILLET – DATAANALYSE")
print("=" * 60)

print()
print(f"Kamper:                 {len(matches)}")
print(f"Unike Brann-spillere:  {len(players)}")
print(f"Unike motstandere:      {len(opponents)}")
print(f"Turneringer:            {len(competitions)}")


print()
print("TURNERINGER")
print("-" * 60)

for competition, count in competitions.most_common():
    print(f"{competition:<30} {count:>3} kamper")


print()
print("SPILLERE MED FLEST KAMPER")
print("-" * 60)

for player_id, count in appearances.most_common(15):
    name = players[player_id]["name"]

    print(
        f"{name:<30} "
        f"{count:>2} kamper "
        f"({starts[player_id]} starter)"
    )


print()
print("TOPPSCORERE")
print("-" * 60)

for player_id, count in goals.most_common(15):
    name = players[player_id]["name"]

    print(
        f"{name:<30} "
        f"{count:>2} mål"
    )


print()
print("MOTSTANDERE")
print("-" * 60)

for name in sorted(opponents.values()):
    print(name)


print()
print("=" * 60)
print("FERDIG")
print("=" * 60)