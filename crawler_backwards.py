import csv
import json
import time
from pathlib import Path

import requests


# ============================================================
# INNSTILLINGER
# ============================================================

BASE_URL = "https://branntall.no"

MAX_DATE = "1999-12-31"

REQUEST_DELAY = 1.0

BRANN_ID = "05bb57f9-3430-5a18-b77c-96b578525b9c"

DATA_DIR = Path("data/raw")
INDEX_FILE = Path("data/matches_backfill_pre2000.csv")
VALIDATION_FILE = Path("data/validation_backfill_pre2000.csv")


# ============================================================
# URL-HJELPERE
# ============================================================

def get_page_data_url(match_path):

    clean_path = match_path.strip("/")

    return (
        f"{BASE_URL}/page-data/"
        f"{clean_path}/page-data.json"
    )


def make_match_path(match):

    date = match["date"]
    year, month, day = date.split("-")

    home_slug = match["homeTeam"]["slug"]["current"]
    away_slug = match["awayTeam"]["slug"]["current"]

    return (
        f"/{year}/{month}/{day}/"
        f"{home_slug}-{away_slug}/"
    )


def make_filename(match):

    date = match["date"]

    home_slug = match["homeTeam"]["slug"]["current"]
    away_slug = match["awayTeam"]["slug"]["current"]

    return (
        f"{date}_"
        f"{home_slug}-{away_slug}.json"
    )


# ============================================================
# NEDLASTING
# ============================================================

def download_json(session, url, attempts=3):

    for attempt in range(1, attempts + 1):

        try:
            response = session.get(
                url,
                timeout=30
            )

            response.raise_for_status()

            return response.json()

        except (
            requests.RequestException,
            ValueError
        ) as error:

            print()
            print(
                f"Feil ved forsok "
                f"{attempt}/{attempts}:"
            )

            print(error)

            if attempt < attempts:
                print(
                    "Prover igjen om "
                    "5 sekunder..."
                )

                time.sleep(5)

            else:
                raise


# ============================================================
# INDEKS / RAPPORTER
# ============================================================

INDEX_FIELDS = [
    "date",
    "home_team",
    "away_team",
    "score",
    "competition",
    "season",
    "path",
    "match_id",
    "filename"
]


VALIDATION_FIELDS = [
    "date",
    "match",
    "match_id",
    "severity",
    "message",
    "filename"
]


def load_csv(filepath):

    if not filepath.exists():
        return []

    with filepath.open(
        "r",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        reader = csv.DictReader(file)

        return list(reader)


def save_csv(filepath, fields, rows):

    filepath.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with filepath.open(
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fields
        )

        writer.writeheader()
        writer.writerows(rows)


def load_existing_raw_matches():

    matches = []

    for filepath in sorted(DATA_DIR.glob("*.json")):

        with filepath.open(
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        match = data["result"]["data"]["model"]

        matches.append(
            {
                "filepath": filepath,
                "filename": filepath.name,
                "match": match
            }
        )

    return matches


# ============================================================
# VALIDERING
# ============================================================

def add_issue(issues, match, severity, message, filename):

    home = (
        match.get("homeTeam", {})
        .get("name", "UKJENT")
    )

    away = (
        match.get("awayTeam", {})
        .get("name", "UKJENT")
    )

    issues.append(
        {
            "date": match.get("date", "UKJENT"),
            "match": f"{home}-{away}",
            "match_id": match.get("_id", "UKJENT"),
            "severity": severity,
            "message": message,
            "filename": filename
        }
    )


def validate_match(match, prev_match, filename):

    issues = []

    if not match.get("_id"):
        add_issue(
            issues,
            match,
            "ERROR",
            "Kampen mangler _id.",
            filename
        )

    if not match.get("date"):
        add_issue(
            issues,
            match,
            "ERROR",
            "Kampen mangler dato.",
            filename
        )

    if match.get("score") is None:
        add_issue(
            issues,
            match,
            "WARNING",
            "Kampen mangler resultat.",
            filename
        )

    home_team = match.get("homeTeam")
    away_team = match.get("awayTeam")

    if not home_team:
        add_issue(
            issues,
            match,
            "ERROR",
            "Kampen mangler hjemmelag.",
            filename
        )

    if not away_team:
        add_issue(
            issues,
            match,
            "ERROR",
            "Kampen mangler bortelag.",
            filename
        )

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
            issues,
            match,
            "ERROR",
            "Ingen av lagene er Brann.",
            filename
        )

    if home_id == BRANN_ID:
        brann_squad = match.get("homeSquad") or []

    elif away_id == BRANN_ID:
        brann_squad = match.get("awaySquad") or []

    else:
        brann_squad = []

    starters = []
    squad_player_ids = set()

    for entry in brann_squad:

        player = entry.get("player")

        if not player:
            add_issue(
                issues,
                match,
                "WARNING",
                "Troppsoppforing mangler spiller.",
                filename
            )

            continue

        player_id = player.get("_id")

        if not player_id:
            add_issue(
                issues,
                match,
                "WARNING",
                (
                    f"Spiller {player.get('name')} "
                    "mangler _id."
                ),
                filename
            )

        elif player_id in squad_player_ids:
            add_issue(
                issues,
                match,
                "ERROR",
                (
                    f"Spiller {player.get('name')} "
                    "er registrert flere ganger "
                    "i Brann-troppen."
                ),
                filename
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
            issues,
            match,
            "WARNING",
            (
                f"Brann har {len(starters)} "
                "registrerte startere, ikke 11."
            ),
            filename
        )

    for event in match.get("events", []):

        event_type_data = event.get("type") or {}

        event_type = event_type_data.get("countAs")
        event_name = event_type_data.get("name")

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
                issues,
                match,
                "WARNING",
                "Kamphendelse mangler lag-ID.",
                filename
            )

        if event_type == "subApp":

            if not event.get("subOn"):
                add_issue(
                    issues,
                    match,
                    "WARNING",
                    "Bytte mangler subOn.",
                    filename
                )

            if not event.get("subOff"):
                add_issue(
                    issues,
                    match,
                    "WARNING",
                    "Bytte mangler subOff.",
                    filename
                )

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
                    issues,
                    match,
                    "WARNING",
                    "Mal mangler malscorer.",
                    filename
                )

    if prev_match:

        prev_date = prev_match.get("date")
        match_date = match.get("date")

        if (
            prev_date
            and match_date
            and prev_date > match_date
        ):
            add_issue(
                issues,
                match,
                "ERROR",
                "Forrige kamp har senere dato enn denne kampen.",
                filename
            )

        for team_field, label in [
            ("homeTeam", "hjemmelag"),
            ("awayTeam", "bortelag")
        ]:

            slug = (
                prev_match
                .get(team_field, {})
                .get("slug")
            )

            if (
                not slug
                or not slug.get("current")
            ):
                add_issue(
                    issues,
                    match,
                    "ERROR",
                    (
                        "Forrige kamps "
                        f"{label} mangler slug."
                    ),
                    filename
                )

    return issues


# ============================================================
# STARTPUNKT
# ============================================================

def find_earliest_local_match(raw_matches):

    if not raw_matches:
        raise RuntimeError(
            "Fant ingen lokale raw-filer."
        )

    return min(
        raw_matches,
        key=lambda item: item["match"]["date"]
    )


def determine_start(raw_matches):

    earliest = find_earliest_local_match(
        raw_matches
    )

    match = earliest["match"]
    prev_match = (
        json.loads(
            earliest["filepath"].read_text(
                encoding="utf-8"
            )
        )["result"]["data"].get("prev")
    )

    print(
        "Tidligste lokale kamp:"
    )

    print(
        f"{match['date']} - "
        f"{match['homeTeam']['name']}-"
        f"{match['awayTeam']['name']} "
        f"{match.get('score')}"
    )

    if prev_match is None:

        print(
            "Denne kampen har ingen "
            "registrert forrige kamp."
        )

        return None

    prev_path = make_match_path(
        prev_match
    )

    print(
        f"Starter bakover fra: {prev_path}"
    )

    return prev_path


# ============================================================
# HOVEDPROGRAM
# ============================================================

def main():

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    raw_matches = load_existing_raw_matches()

    seen_match_ids = {
        item["match"]["_id"]
        for item in raw_matches
        if item["match"].get("_id")
    }

    existing_filenames = {
        item["filename"]
        for item in raw_matches
    }

    rows = load_csv(INDEX_FILE)
    validation_issues = load_csv(VALIDATION_FILE)

    current_path = determine_start(raw_matches)

    if current_path is None:
        return

    session = requests.Session()

    session.headers.update(
        {
            "User-Agent":
                "Brannspillet research project"
        }
    )

    downloaded_this_run = 0
    skipped_existing = 0

    try:

        while current_path:

            url = get_page_data_url(
                current_path
            )

            print()
            print("=" * 60)

            print(
                f"Henter bakover: {url}"
            )

            data = download_json(
                session,
                url
            )

            page_data = data["result"]["data"]

            match = page_data["model"]
            prev_match = page_data.get("prev")

            match_id = match["_id"]
            filename = make_filename(match)

            date = match["date"]

            if date > MAX_DATE:
                print(
                    f"Hopper over {date}, "
                    f"etter {MAX_DATE}."
                )

            elif (
                match_id in seen_match_ids
                or filename in existing_filenames
            ):
                print(
                    f"Finnes fra for: {date} "
                    f"{match['homeTeam']['name']}-"
                    f"{match['awayTeam']['name']} "
                    f"{match.get('score')}"
                )

                skipped_existing += 1

            else:
                print(
                    f"Fant: {date} - "
                    f"{match['homeTeam']['name']}-"
                    f"{match['awayTeam']['name']} "
                    f"{match.get('score')}"
                )

                filepath = DATA_DIR / filename

                with filepath.open(
                    "w",
                    encoding="utf-8"
                ) as file:

                    json.dump(
                        data,
                        file,
                        ensure_ascii=False,
                        indent=2
                    )

                new_issues = validate_match(
                    match,
                    prev_match,
                    filename
                )

                if new_issues:
                    print()

                    for issue in new_issues:
                        print(
                            f"{issue['severity']}: "
                            f"{issue['message']}"
                        )

                    validation_issues.extend(
                        new_issues
                    )

                    save_csv(
                        VALIDATION_FILE,
                        VALIDATION_FIELDS,
                        validation_issues
                    )

                else:
                    print(
                        "Validering: OK"
                    )

                competition = (
                    match
                    .get("competition", {})
                    .get("name")
                )

                season = (
                    match
                    .get("season", {})
                    .get("name")
                )

                rows.append(
                    {
                        "date": date,
                        "home_team": match["homeTeam"]["name"],
                        "away_team": match["awayTeam"]["name"],
                        "score": match.get("score"),
                        "competition": competition,
                        "season": season,
                        "path": current_path,
                        "match_id": match_id,
                        "filename": filename
                    }
                )

                save_csv(
                    INDEX_FILE,
                    INDEX_FIELDS,
                    rows
                )

                seen_match_ids.add(
                    match_id
                )

                existing_filenames.add(
                    filename
                )

                downloaded_this_run += 1

            if prev_match is None:
                print(
                    "Ingen forrige kamp registrert."
                )

                break

            current_path = make_match_path(
                prev_match
            )

            time.sleep(
                REQUEST_DELAY
            )

    except KeyboardInterrupt:

        print()
        print()
        print(
            "Crawleren ble stoppet manuelt."
        )

        print(
            "Alt som var ferdig hentet "
            "er allerede lagret."
        )

    finally:

        rows.sort(
            key=lambda row: row["date"],
            reverse=True
        )

        save_csv(
            INDEX_FILE,
            INDEX_FIELDS,
            rows
        )

        save_csv(
            VALIDATION_FILE,
            VALIDATION_FIELDS,
            validation_issues
        )

        print()
        print("=" * 60)
        print("BAKOVER-CRAWL FERDIG")
        print("=" * 60)

        print(
            f"Nye kamper denne kjoringen: "
            f"{downloaded_this_run}"
        )

        print(
            f"Eksisterende hoppet over: "
            f"{skipped_existing}"
        )

        print(
            f"Backfill-indeksrader: "
            f"{len(rows)}"
        )

        print(
            f"Valideringsavvik: "
            f"{len(validation_issues)}"
        )

        print(
            f"Indeks: {INDEX_FILE}"
        )

        print(
            f"Validering: {VALIDATION_FILE}"
        )


if __name__ == "__main__":
    main()
