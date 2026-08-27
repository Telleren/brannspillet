import csv
import json
from collections import Counter
from pathlib import Path


DATA_DIR = Path("data/raw")
REPORT_FILE = Path("data/full_validation.csv")

BRANN_ID = "05bb57f9-3430-5a18-b77c-96b578525b9c"


issues = []
match_ids = set()

stats = Counter()


def add_issue(match, severity, message, filename):
    home = match.get("homeTeam", {}).get("name", "UKJENT")
    away = match.get("awayTeam", {}).get("name", "UKJENT")

    issues.append({
        "date": match.get("date", "UKJENT"),
        "match": f"{home}–{away}",
        "match_id": match.get("_id", "UKJENT"),
        "severity": severity,
        "message": message,
        "filename": filename
    })


files = sorted(DATA_DIR.glob("*.json"))

print()
print("=" * 60)
print("FULL VALIDERING AV BRANNTALL-DATA")
print("=" * 60)
print()
print(f"Fant {len(files)} JSON-filer.")
print()


for number, filepath in enumerate(files, start=1):

    print(
        f"[{number}/{len(files)}] "
        f"{filepath.name}"
    )

    try:
        with filepath.open(
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

    except Exception as error:
        issues.append({
            "date": "UKJENT",
            "match": "UKJENT",
            "match_id": "UKJENT",
            "severity": "ERROR",
            "message": f"Kunne ikke lese JSON: {error}",
            "filename": filepath.name
        })

        continue

    try:
        page_data = data["result"]["data"]
        match = page_data["model"]

    except (KeyError, TypeError) as error:
        issues.append({
            "date": "UKJENT",
            "match": "UKJENT",
            "match_id": "UKJENT",
            "severity": "ERROR",
            "message": f"Mangler forventet datastruktur: {error}",
            "filename": filepath.name
        })

        continue


    stats["matches"] += 1

    match_id = match.get("_id")

    # --------------------------------------------------------
    # Kamp-ID
    # --------------------------------------------------------

    if not match_id:
        add_issue(
            match,
            "ERROR",
            "Kampen mangler _id.",
            filepath.name
        )

    elif match_id in match_ids:
        add_issue(
            match,
            "ERROR",
            "Samme kamp-ID finnes i flere filer.",
            filepath.name
        )

    else:
        match_ids.add(match_id)


    # --------------------------------------------------------
    # Grunnleggende felt
    # --------------------------------------------------------

    if not match.get("date"):
        add_issue(
            match,
            "ERROR",
            "Kampen mangler dato.",
            filepath.name
        )

    if match.get("score") is None:
        add_issue(
            match,
            "WARNING",
            "Kampen mangler resultat.",
            filepath.name
        )

    home_team = match.get("homeTeam")
    away_team = match.get("awayTeam")

    if not home_team:
        add_issue(
            match,
            "ERROR",
            "Kampen mangler hjemmelag.",
            filepath.name
        )

    if not away_team:
        add_issue(
            match,
            "ERROR",
            "Kampen mangler bortelag.",
            filepath.name
        )


    # --------------------------------------------------------
    # Brann-kontroll
    # --------------------------------------------------------

    home_id = (
        home_team.get("_id")
        if home_team
        else None
    )

    away_id = (
        away_team.get("_id")
        if away_team
        else None
    )

    if (
        home_id != BRANN_ID
        and away_id != BRANN_ID
    ):
        add_issue(
            match,
            "ERROR",
            "Ingen av lagene er Brann.",
            filepath.name
        )

        continue


    # --------------------------------------------------------
    # Finn Branns tropp
    # --------------------------------------------------------

    if home_id == BRANN_ID:
        squad = match.get("homeSquad") or []

    else:
        squad = match.get("awaySquad") or []


    starters = []
    squad_player_ids = set()


    for entry in squad:

        player = entry.get("player")

        if not player:
            add_issue(
                match,
                "WARNING",
                "Troppsoppføring mangler spiller.",
                filepath.name
            )

            continue


        player_id = player.get("_id")

        if not player_id:
            add_issue(
                match,
                "WARNING",
                (
                    f"Spiller {player.get('name')} "
                    "mangler _id."
                ),
                filepath.name
            )

        elif player_id in squad_player_ids:
            add_issue(
                match,
                "ERROR",
                (
                    f"Spiller {player.get('name')} "
                    "er registrert flere ganger "
                    "i Brann-troppen."
                ),
                filepath.name
            )

        else:
            squad_player_ids.add(player_id)


        role = entry.get("role")

        if (
            role
            and role.get("starting") is True
        ):
            starters.append(entry)


    if len(starters) != 11:
        add_issue(
            match,
            "WARNING",
            (
                f"Brann har {len(starters)} "
                "registrerte startere, ikke 11."
            ),
            filepath.name
        )


    stats["squad_entries"] += len(squad)
    stats["starters"] += len(starters)


    # --------------------------------------------------------
    # Kamp-events
    # --------------------------------------------------------

    for event in match.get("events", []):

        stats["events"] += 1

        event_type = (
            event.get("type", {})
            .get("countAs")
        )

        event_name = (
            event.get("type", {})
            .get("name")
        )

        stats[f"event_{event_type}"] += 1


        # "Straffekonk" er bare en markør for at kampen
        # gikk til straffesparkkonkurranse.
        # Den trenger derfor ikke lag-ID eller spiller.
        is_shootout_marker = (
            event_name == "Straffekonk"
            and event_type is None
        )


        team = event.get("team")

        if (
            not is_shootout_marker
            and (
                not team
                or not team.get("_id")
            )
        ):
            add_issue(
                match,
                "WARNING",
                "Kamphendelse mangler lag-ID.",
                filepath.name
            )


        # ----------------------------------------------------
        # Bytte
        # ----------------------------------------------------

        if event_type == "subApp":

            if not event.get("subOn"):
                add_issue(
                    match,
                    "WARNING",
                    "Bytte mangler subOn.",
                    filepath.name
                )

            if not event.get("subOff"):
                add_issue(
                    match,
                    "WARNING",
                    "Bytte mangler subOff.",
                    filepath.name
                )


        # ----------------------------------------------------
        # Mål
        # ----------------------------------------------------

        if event_type in (
            "goal",
            "penaltyGoal"
        ):

            scorer = (
                event.get("scoredBy")
                or event.get("player")
            )

            if not scorer:
                add_issue(
                    match,
                    "WARNING",
                    "Mål mangler målscorer.",
                    filepath.name
                )
# ============================================================
# LAGRE RAPPORT
# ============================================================

fields = [
    "date",
    "match",
    "match_id",
    "severity",
    "message",
    "filename"
]


with REPORT_FILE.open(
    "w",
    newline="",
    encoding="utf-8-sig"
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=fields
    )

    writer.writeheader()
    writer.writerows(issues)


# ============================================================
# RESULTAT
# ============================================================

errors = [
    issue
    for issue in issues
    if issue["severity"] == "ERROR"
]

warnings = [
    issue
    for issue in issues
    if issue["severity"] == "WARNING"
]


print()
print("=" * 60)
print("VALIDERING FERDIG")
print("=" * 60)

print()
print(f"JSON-filer:             {len(files)}")
print(f"Gyldige kampobjekter:   {stats['matches']}")
print(f"Unike kamp-ID-er:       {len(match_ids)}")
print(f"Troppsoppføringer:      {stats['squad_entries']}")
print(f"Registrerte startere:   {stats['starters']}")
print(f"Kamphendelser:          {stats['events']}")

print()
print(f"ERROR:                   {len(errors)}")
print(f"WARNING:                 {len(warnings)}")

print()
print("HENDELSESTYPER")
print("-" * 60)

for key, count in sorted(stats.items()):

    if key.startswith("event_"):
        event_name = key.replace(
            "event_",
            ""
        )

        print(
            f"{event_name:<30} "
            f"{count:>5}"
        )

print()
print(f"Rapport: {REPORT_FILE}")

if not issues:
    print()
    print(
        "Alle kontroller bestått "
        "uten avvik."
    )