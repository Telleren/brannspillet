import csv
import json
import time
from pathlib import Path

import requests


# ============================================================
# INNSTILLINGER
# ============================================================

BASE_URL = "https://branntall.no"

START_PATH = "/2000/04/09/brann-viking/"

# I denne testfasen henter vi til og med 2026.
END_DATE = "2026-12-31"

REQUEST_DELAY = 1.0

BRANN_ID = "05bb57f9-3430-5a18-b77c-96b578525b9c"

DATA_DIR = Path("data/raw")
INDEX_FILE = Path("data/matches.csv")
VALIDATION_FILE = Path("data/validation_warnings.csv")

DATA_DIR.mkdir(parents=True, exist_ok=True)


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
                f"Feil ved forsøk "
                f"{attempt}/{attempts}:"
            )

            print(error)

            if attempt < attempts:
                print(
                    "Prøver igjen om "
                    "5 sekunder..."
                )

                time.sleep(5)

            else:
                raise


# ============================================================
# INDEKS
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


def load_index():

    if not INDEX_FILE.exists():
        return []

    with INDEX_FILE.open(
        "r",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        reader = csv.DictReader(file)

        return list(reader)


def save_index(rows):

    INDEX_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with INDEX_FILE.open(
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=INDEX_FIELDS
        )

        writer.writeheader()
        writer.writerows(rows)


# ============================================================
# VALIDERING
# ============================================================

VALIDATION_FIELDS = [
    "date",
    "match",
    "match_id",
    "severity",
    "message"
]


def save_validation(issues):

    VALIDATION_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with VALIDATION_FILE.open(
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=VALIDATION_FIELDS
        )

        writer.writeheader()
        writer.writerows(issues)


def validate_match(match, next_match):

    issues = []

    date = match.get("date", "UKJENT")

    home = (
        match.get("homeTeam", {})
        .get("name", "UKJENT")
    )

    away = (
        match.get("awayTeam", {})
        .get("name", "UKJENT")
    )

    match_id = match.get("_id", "UKJENT")

    match_name = f"{home}–{away}"


    def add_issue(severity, message):

        issues.append({
            "date": date,
            "match": match_name,
            "match_id": match_id,
            "severity": severity,
            "message": message
        })


    # --------------------------------------------------------
    # Grunnleggende felter
    # --------------------------------------------------------

    if not match.get("_id"):
        add_issue(
            "ERROR",
            "Kampen mangler _id."
        )

    if not match.get("date"):
        add_issue(
            "ERROR",
            "Kampen mangler dato."
        )

    if not match.get("homeTeam"):
        add_issue(
            "ERROR",
            "Kampen mangler hjemmelag."
        )

    if not match.get("awayTeam"):
        add_issue(
            "ERROR",
            "Kampen mangler bortelag."
        )

    if match.get("score") is None:
        add_issue(
            "WARNING",
            "Kampen mangler resultat."
        )


    # --------------------------------------------------------
    # Er Brann faktisk med?
    # --------------------------------------------------------

    home_id = (
        match.get("homeTeam", {})
        .get("_id")
    )

    away_id = (
        match.get("awayTeam", {})
        .get("_id")
    )

    if (
        home_id != BRANN_ID
        and away_id != BRANN_ID
    ):
        add_issue(
            "ERROR",
            "Ingen av lagene er Brann."
        )


    # --------------------------------------------------------
    # Branns tropp
    # --------------------------------------------------------

    if home_id == BRANN_ID:
        brann_squad = (
            match.get("homeSquad") or []
        )

    elif away_id == BRANN_ID:
        brann_squad = (
            match.get("awaySquad") or []
        )

    else:
        brann_squad = []


    starters = []

    for entry in brann_squad:

        role = entry.get("role")

        if (
            role
            and role.get("starting") is True
        ):
            starters.append(entry)


        player = entry.get("player")

        if not player:
            add_issue(
                "WARNING",
                "Troppsoppføring mangler spiller."
            )

        elif not player.get("_id"):
            add_issue(
                "WARNING",
                "Spiller mangler unik _id."
            )


    if len(starters) != 11:

        add_issue(
            "WARNING",
            (
                "Brann har "
                f"{len(starters)} registrerte "
                "startere, ikke 11."
            )
        )


    # --------------------------------------------------------
    # Kontroll av next
    # --------------------------------------------------------

    if next_match:

        next_date = next_match.get("date")

        if (
            next_date
            and match.get("date")
            and next_date < match["date"]
        ):
            add_issue(
                "ERROR",
                (
                    "Neste kamp har tidligere "
                    "dato enn denne kampen."
                )
            )


        home_slug = (
            next_match
            .get("homeTeam", {})
            .get("slug")
        )

        away_slug = (
            next_match
            .get("awayTeam", {})
            .get("slug")
        )


        if (
            not home_slug
            or not home_slug.get("current")
        ):
            add_issue(
                "ERROR",
                (
                    "Neste kamps hjemmelag "
                    "mangler slug."
                )
            )


        if (
            not away_slug
            or not away_slug.get("current")
        ):
            add_issue(
                "ERROR",
                (
                    "Neste kamps bortelag "
                    "mangler slug."
                )
            )


    return issues


# ============================================================
# FINN UT HVOR VI SKAL STARTE
# ============================================================

def determine_start(existing_rows):

    if not existing_rows:

        print(
            "Ingen eksisterende kamper funnet."
        )

        print(
            f"Starter fra {START_PATH}"
        )

        return START_PATH


    last_row = existing_rows[-1]

    last_file = (
        DATA_DIR / last_row["filename"]
    )


    if not last_file.exists():

        raise RuntimeError(
            "Siste kamp i matches.csv "
            "finnes ikke i data/raw."
        )


    with last_file.open(
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)


    page_data = data["result"]["data"]

    match = page_data["model"]
    next_match = page_data.get("next")


    print(
        f"Fant {len(existing_rows)} "
        "eksisterende kamper."
    )

    print(
        "Siste lokale kamp:"
    )

    print(
        f"{match['date']} – "
        f"{match['homeTeam']['name']}–"
        f"{match['awayTeam']['name']} "
        f"{match.get('score')}"
    )


    if next_match is None:

        print(
            "Denne kampen har ingen "
            "registrert neste kamp."
        )

        return None


    next_path = make_match_path(
        next_match
    )

    print(
        f"Fortsetter fra: {next_path}"
    )

    return next_path


# ============================================================
# HOVEDPROGRAM
# ============================================================

def main():

    rows = load_index()

    seen_match_ids = {
        row["match_id"]
        for row in rows
        if row.get("match_id")
    }

    validation_issues = []

    current_path = determine_start(rows)

    if current_path is None:
        return


    session = requests.Session()

    session.headers.update({
        "User-Agent":
            "Brannspillet research project"
    })


    downloaded_this_run = 0


    try:

        while current_path:

            url = get_page_data_url(
                current_path
            )

            print()
            print("=" * 60)

            print(
                f"Ny kamp "
                f"({len(rows) + 1})"
            )

            print(
                f"Henter: {url}"
            )


            data = download_json(
                session,
                url
            )


            page_data = data[
                "result"
            ]["data"]

            match = page_data["model"]
            next_match = page_data.get("next")


            date = match["date"]


            # ------------------------------------------------
            # Stopp ved sluttdato
            # ------------------------------------------------

            if date > END_DATE:

                print()
                print(
                    f"Nådde {date}."
                )

                print(
                    f"Dette er etter "
                    f"{END_DATE}."
                )

                print(
                    "Stopper uten å lagre "
                    "denne kampen."
                )

                break


            match_id = match["_id"]


            # ------------------------------------------------
            # Duplikatkontroll
            # ------------------------------------------------

            if match_id in seen_match_ids:

                raise RuntimeError(
                    (
                        "Duplikat oppdaget: "
                        f"{match_id}"
                    )
                )


            seen_match_ids.add(
                match_id
            )


            home = (
                match["homeTeam"]["name"]
            )

            away = (
                match["awayTeam"]["name"]
            )

            score = match.get("score")


            print(
                f"Fant: {date} – "
                f"{home}–{away} {score}"
            )


            # ------------------------------------------------
            # Valider kampen
            # ------------------------------------------------

            new_issues = validate_match(
                match,
                next_match
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

                save_validation(
                    validation_issues
                )

            else:

                print(
                    "Validering: OK"
                )


            # ------------------------------------------------
            # Lagre rå JSON
            # ------------------------------------------------

            filename = make_filename(
                match
            )

            filepath = (
                DATA_DIR / filename
            )


            if filepath.exists():

                print(
                    "JSON finnes allerede."
                )

            else:

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

                print(
                    f"Lagret: {filepath}"
                )


            # ------------------------------------------------
            # Registrer i indeks
            # ------------------------------------------------

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


            rows.append({
                "date": date,
                "home_team": home,
                "away_team": away,
                "score": score,
                "competition": competition,
                "season": season,
                "path": current_path,
                "match_id": match_id,
                "filename": filename
            })


            # Checkpoint etter hver kamp
            save_index(rows)

            downloaded_this_run += 1


            # ------------------------------------------------
            # Finn neste kamp
            # ------------------------------------------------

            if next_match is None:

                print(
                    "Ingen neste kamp registrert."
                )

                break


            try:

                current_path = (
                    make_match_path(
                        next_match
                    )
                )

            except (
                KeyError,
                TypeError
            ):

                raise RuntimeError(
                    (
                        "Kunne ikke bygge URL "
                        "til neste kamp."
                    )
                )


            time.sleep(
                REQUEST_DELAY
            )


    except KeyboardInterrupt:

        print()
        print()
        print(
            "Crawleren ble stoppet "
            "manuelt."
        )

        print(
            "Alt som var ferdig hentet "
            "er allerede lagret."
        )


    finally:

        save_index(rows)

        save_validation(
            validation_issues
        )

        print()
        print("=" * 60)

        print("KJØRING FERDIG")

        print("=" * 60)

        print(
            f"Kamper totalt: "
            f"{len(rows)}"
        )

        print(
            f"Nye kamper denne kjøringen: "
            f"{downloaded_this_run}"
        )

        print(
            f"Valideringsadvarsler: "
            f"{len(validation_issues)}"
        )

        print(
            f"Indeks: {INDEX_FILE}"
        )

        print(
            f"Validering: "
            f"{VALIDATION_FILE}"
        )


if __name__ == "__main__":
    main()