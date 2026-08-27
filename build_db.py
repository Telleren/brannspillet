import json
import sqlite3
from pathlib import Path


# ============================================================
# INNSTILLINGER
# ============================================================

DATA_DIR = Path("data/raw")

DB_FILE = Path("data/brannspillet.db")
TEMP_DB_FILE = Path("data/brannspillet_new.db")

BRANN_ID = "05bb57f9-3430-5a18-b77c-96b578525b9c"


# ============================================================
# SMÅ HJELPEFUNKSJONER
# ============================================================

def get_slug(obj):
    if not obj:
        return None

    slug = obj.get("slug")

    if not slug:
        return None

    return slug.get("current")


def parse_score(score):
    """
    Forsøker å gjøre f.eks. "4-1" om til:
    (4, 1)

    Hvis formatet er ukjent, returnerer vi:
    (None, None)
    """

    if not score:
        return None, None

    try:
        home, away = score.split("-", 1)

        return int(home), int(away)

    except (ValueError, AttributeError):
        return None, None


# ============================================================
# OPPRETT TABELLER
# ============================================================

def create_tables(conn):

    conn.executescript(
        """
        PRAGMA foreign_keys = ON;


        CREATE TABLE players (
            id TEXT PRIMARY KEY,

            name TEXT NOT NULL,
            full_name TEXT,
            slug TEXT,

            birthdate TEXT,
            birthplace TEXT,
            country_code TEXT
        );


        CREATE TABLE teams (
            id TEXT PRIMARY KEY,

            name TEXT NOT NULL,
            abbr TEXT,
            full_name TEXT,
            slug TEXT,
            country_code TEXT
        );


        CREATE TABLE competitions (
            id TEXT PRIMARY KEY,

            name TEXT NOT NULL,
            abbr TEXT,
            slug TEXT,

            sort REAL,
            level INTEGER,
            official INTEGER,
            count_as TEXT,

            parent_id TEXT
        );


        CREATE TABLE grounds (
            id TEXT PRIMARY KEY,

            name TEXT NOT NULL,
            full_name TEXT,
            slug TEXT,
            country_code TEXT,

            latitude REAL,
            longitude REAL
        );


        CREATE TABLE matches (
            id TEXT PRIMARY KEY,

            branntall_id TEXT,

            date TEXT NOT NULL,
            time TEXT,

            season_id TEXT,
            season_name TEXT,

            competition_id TEXT,

            round_id TEXT,
            round_name TEXT,
            round_abbr TEXT,
            round_sort REAL,

            leg TEXT,

            ground_id TEXT,

            home_team_id TEXT NOT NULL,
            away_team_id TEXT NOT NULL,

            score TEXT,
            home_score INTEGER,
            away_score INTEGER,

            aggregate_score TEXT,
            shootout_score TEXT,

            attendance INTEGER,

            source_filename TEXT NOT NULL,

            FOREIGN KEY (competition_id)
                REFERENCES competitions(id),

            FOREIGN KEY (ground_id)
                REFERENCES grounds(id),

            FOREIGN KEY (home_team_id)
                REFERENCES teams(id),

            FOREIGN KEY (away_team_id)
                REFERENCES teams(id)
        );


        CREATE TABLE appearances (
            match_id TEXT NOT NULL,
            team_id TEXT NOT NULL,
            player_id TEXT NOT NULL,

            shirt_number INTEGER,

            role_id TEXT,
            role_abbr TEXT,
            role_sort REAL,

            starting INTEGER NOT NULL DEFAULT 0,

            appeared INTEGER NOT NULL DEFAULT 0,
            unused_substitute INTEGER NOT NULL DEFAULT 0,

            entered_minute INTEGER,
            exited_minute INTEGER,

            PRIMARY KEY (
                match_id,
                team_id,
                player_id
            ),

            FOREIGN KEY (match_id)
                REFERENCES matches(id),

            FOREIGN KEY (team_id)
                REFERENCES teams(id),

            FOREIGN KEY (player_id)
                REFERENCES players(id)
        );


        CREATE TABLE events (
            match_id TEXT NOT NULL,
            event_index INTEGER NOT NULL,

            minute INTEGER,

            event_name TEXT,
            event_type TEXT,

            team_id TEXT,

            player_id TEXT,
            scorer_id TEXT,
            assist_id TEXT,

            sub_on_id TEXT,
            sub_off_id TEXT,

            PRIMARY KEY (
                match_id,
                event_index
            ),

            FOREIGN KEY (match_id)
                REFERENCES matches(id),

            FOREIGN KEY (team_id)
                REFERENCES teams(id),

            FOREIGN KEY (player_id)
                REFERENCES players(id),

            FOREIGN KEY (scorer_id)
                REFERENCES players(id),

            FOREIGN KEY (assist_id)
                REFERENCES players(id),

            FOREIGN KEY (sub_on_id)
                REFERENCES players(id),

            FOREIGN KEY (sub_off_id)
                REFERENCES players(id)
        );


        CREATE INDEX idx_matches_date
        ON matches(date);


        CREATE INDEX idx_appearances_player
        ON appearances(player_id);


        CREATE INDEX idx_appearances_team
        ON appearances(team_id);


        CREATE INDEX idx_events_type
        ON events(event_type);


        CREATE INDEX idx_events_scorer
        ON events(scorer_id);


        CREATE INDEX idx_events_team
        ON events(team_id);
        """
    )


# ============================================================
# PLAYERS
# ============================================================

def upsert_player(conn, player):

    if not player:
        return None

    player_id = player.get("_id")

    if not player_id:
        return None

    name = player.get("name")

    if not name:
        name = "Ukjent spiller"

    conn.execute(
        """
        INSERT INTO players (
            id,
            name,
            full_name,
            slug,
            birthdate,
            birthplace,
            country_code
        )

        VALUES (?, ?, ?, ?, ?, ?, ?)

        ON CONFLICT(id) DO UPDATE SET

            name =
                COALESCE(
                    excluded.name,
                    players.name
                ),

            full_name =
                COALESCE(
                    excluded.full_name,
                    players.full_name
                ),

            slug =
                COALESCE(
                    excluded.slug,
                    players.slug
                ),

            birthdate =
                COALESCE(
                    excluded.birthdate,
                    players.birthdate
                ),

            birthplace =
                COALESCE(
                    excluded.birthplace,
                    players.birthplace
                ),

            country_code =
                COALESCE(
                    excluded.country_code,
                    players.country_code
                )
        """,
        (
            player_id,
            name,
            player.get("fullName"),
            get_slug(player),
            player.get("birthdate"),
            player.get("birthplace"),
            player.get("countryCode")
        )
    )

    return player_id


# ============================================================
# TEAMS
# ============================================================

def upsert_team(conn, team):

    if not team:
        return None

    team_id = team.get("_id")

    if not team_id:
        return None

    name = team.get("name")

    if not name:
        name = "Ukjent lag"

    conn.execute(
        """
        INSERT INTO teams (
            id,
            name,
            abbr,
            full_name,
            slug,
            country_code
        )

        VALUES (?, ?, ?, ?, ?, ?)

        ON CONFLICT(id) DO UPDATE SET

            name =
                COALESCE(
                    excluded.name,
                    teams.name
                ),

            abbr =
                COALESCE(
                    excluded.abbr,
                    teams.abbr
                ),

            full_name =
                COALESCE(
                    excluded.full_name,
                    teams.full_name
                ),

            slug =
                COALESCE(
                    excluded.slug,
                    teams.slug
                ),

            country_code =
                COALESCE(
                    excluded.country_code,
                    teams.country_code
                )
        """,
        (
            team_id,
            name,
            team.get("abbr"),
            team.get("fullName"),
            get_slug(team),
            team.get("countryCode")
        )
    )

    return team_id


# ============================================================
# COMPETITIONS
# ============================================================

def upsert_competition(conn, competition):

    if not competition:
        return None

    competition_id = competition.get("_id")

    if not competition_id:
        return None

    parent = competition.get("isPartOf")
    parent_id = None

    if parent:
        parent_id = upsert_competition(
            conn,
            parent
        )

    name = (
        competition.get("name")
        or "Ukjent turnering"
    )

    conn.execute(
        """
        INSERT INTO competitions (
            id,
            name,
            abbr,
            slug,
            sort,
            level,
            official,
            count_as,
            parent_id
        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)

        ON CONFLICT(id) DO UPDATE SET

            name =
                COALESCE(
                    excluded.name,
                    competitions.name
                ),

            abbr =
                COALESCE(
                    excluded.abbr,
                    competitions.abbr
                ),

            slug =
                COALESCE(
                    excluded.slug,
                    competitions.slug
                ),

            sort =
                COALESCE(
                    excluded.sort,
                    competitions.sort
                ),

            level =
                COALESCE(
                    excluded.level,
                    competitions.level
                ),

            official =
                COALESCE(
                    excluded.official,
                    competitions.official
                ),

            count_as =
                COALESCE(
                    excluded.count_as,
                    competitions.count_as
                ),

            parent_id =
                COALESCE(
                    excluded.parent_id,
                    competitions.parent_id
                )
        """,
        (
            competition_id,
            name,
            competition.get("abbr"),
            get_slug(competition),
            competition.get("sort"),
            competition.get("level"),

            (
                int(competition["official"])
                if competition.get("official")
                is not None
                else None
            ),

            competition.get("countAs"),
            parent_id
        )
    )

    return competition_id


# ============================================================
# GROUNDS
# ============================================================

def upsert_ground(conn, ground):

    if not ground:
        return None

    ground_id = ground.get("_id")

    if not ground_id:
        return None

    location = ground.get("location") or {}

    name = (
        ground.get("name")
        or "Ukjent stadion"
    )

    conn.execute(
        """
        INSERT INTO grounds (
            id,
            name,
            full_name,
            slug,
            country_code,
            latitude,
            longitude
        )

        VALUES (?, ?, ?, ?, ?, ?, ?)

        ON CONFLICT(id) DO UPDATE SET

            name =
                COALESCE(
                    excluded.name,
                    grounds.name
                ),

            full_name =
                COALESCE(
                    excluded.full_name,
                    grounds.full_name
                ),

            slug =
                COALESCE(
                    excluded.slug,
                    grounds.slug
                ),

            country_code =
                COALESCE(
                    excluded.country_code,
                    grounds.country_code
                ),

            latitude =
                COALESCE(
                    excluded.latitude,
                    grounds.latitude
                ),

            longitude =
                COALESCE(
                    excluded.longitude,
                    grounds.longitude
                )
        """,
        (
            ground_id,
            name,
            ground.get("fullName"),
            get_slug(ground),
            ground.get("countryCode"),
            location.get("lat"),
            location.get("lng")
        )
    )

    return ground_id


# ============================================================
# KAMP
# ============================================================

def insert_match(conn, match, filename):

    home_team_id = upsert_team(
        conn,
        match.get("homeTeam")
    )

    away_team_id = upsert_team(
        conn,
        match.get("awayTeam")
    )

    competition_id = upsert_competition(
        conn,
        match.get("competition")
    )

    ground_id = upsert_ground(
        conn,
        match.get("ground")
    )

    season = match.get("season") or {}
    round_data = match.get("round") or {}

    home_score, away_score = parse_score(
        match.get("score")
    )

    conn.execute(
        """
        INSERT INTO matches (
            id,
            branntall_id,
            date,
            time,

            season_id,
            season_name,

            competition_id,

            round_id,
            round_name,
            round_abbr,
            round_sort,

            leg,

            ground_id,

            home_team_id,
            away_team_id,

            score,
            home_score,
            away_score,

            aggregate_score,
            shootout_score,

            attendance,

            source_filename
        )

        VALUES (
            ?, ?, ?, ?,
            ?, ?,
            ?,
            ?, ?, ?, ?,
            ?,
            ?,
            ?, ?,
            ?, ?, ?,
            ?, ?,
            ?,
            ?
        )
        """,
        (
            match["_id"],
            match.get("id"),
            match["date"],
            match.get("time"),

            season.get("_id"),
            season.get("name"),

            competition_id,

            round_data.get("_id"),
            round_data.get("name"),
            round_data.get("abbr"),
            round_data.get("sort"),

            str(match.get("leg"))
            if match.get("leg") is not None
            else None,

            ground_id,

            home_team_id,
            away_team_id,

            match.get("score"),
            home_score,
            away_score,

            match.get("aggregateScore"),
            match.get("shootoutScore"),

            match.get("attendance"),

            filename
        )
    )


# ============================================================
# TROPPER / APPEARANCES
# ============================================================

def insert_squad(
    conn,
    match_id,
    team,
    squad
):

    if not team:
        return

    team_id = upsert_team(
        conn,
        team
    )

    # Holder styr på spillere vi allerede har sett
    # i dette lagets tropp i denne kampen.
    seen_players = {}


    for entry in squad or []:

        player = entry.get("player")

        if not player:
            continue

        player_id = player.get("_id")

        if not player_id:
            continue


        role = entry.get("role") or {}


        # Signaturen beskriver selve troppsoppføringen.
        # Hvis samme spiller dukker opp igjen med nøyaktig
        # samme informasjon, er det bare et rådataduplikat.
        signature = (
            entry.get("shirt"),
            role.get("_id"),
            role.get("name"),
            role.get("abbr"),
            role.get("sort"),
            role.get("starting")
        )


        if player_id in seen_players:

            previous_signature = (
                seen_players[player_id]
            )

            if signature == previous_signature:

                print(
                    "  MERK: Ignorerer identisk "
                    f"troppsduplikat: "
                    f"{player.get('name')} "
                    f"({team.get('name')})"
                )

                continue


            # Samme spiller finnes to ganger,
            # men oppføringene sier forskjellige ting.
            # Da skal vi IKKE gjette hvilken som er riktig.
            raise ValueError(
                "\nMotstridende troppsduplikat funnet:\n"
                f"Kamp-ID: {match_id}\n"
                f"Lag: {team.get('name')}\n"
                f"Spiller: {player.get('name')}\n"
                f"Spiller-ID: {player_id}\n"
                f"Første oppføring: "
                f"{previous_signature}\n"
                f"Andre oppføring: "
                f"{signature}"
            )


        seen_players[player_id] = signature


        # Først nå lagrer vi spilleren.
        upsert_player(
            conn,
            player
        )


        starting = (
            role.get("starting") is True
        )


        # Startere har spilt.
        appeared = (
            1 if starting else 0
        )


        # En ikke-starter regnes foreløpig
        # som ubrukt reserve.
        #
        # Hvis events senere viser at spilleren
        # kom inn, korrigerer insert_events()
        # dette automatisk.
        unused_substitute = (
            0 if starting else 1
        )


        conn.execute(
            """
            INSERT INTO appearances (
                match_id,
                team_id,
                player_id,

                shirt_number,

                role_id,
                role_abbr,
                role_sort,

                starting,
                appeared,
                unused_substitute
            )

            VALUES (
                ?, ?, ?,
                ?,
                ?, ?, ?,
                ?, ?, ?
            )
            """,
            (
                match_id,
                team_id,
                player_id,

                entry.get("shirt"),

                role.get("_id"),
                role.get("abbr"),
                role.get("sort"),

                int(starting),
                appeared,
                unused_substitute
            )
        )


# ============================================================
# EVENTS
# ============================================================

def get_squad_player_ids(squad):

    player_ids = set()

    for entry in squad or []:

        player = entry.get("player")

        if player and player.get("_id"):
            player_ids.add(
                player["_id"]
            )

    return player_ids


def resolve_event_team_id(match, event):
    """
    Returnerer normalisert lag-ID for en kamphendelse.

    Vanligvis bruker eventen samme lag-ID som homeTeam
    eller awayTeam.

    Enkelte Branntall-kamper bruker imidlertid en gammel
    eller alternativ lag-ID inne i events. Da forsøker vi
    å identifisere laget ut fra spillerne i hendelsen.
    """

    home_team_id = match["homeTeam"]["_id"]
    away_team_id = match["awayTeam"]["_id"]

    team = event.get("team")

    raw_team_id = (
        team.get("_id")
        if team
        else None
    )

    # Vanlig tilfelle:
    # eventen peker allerede på et av lagene i kampen.
    if raw_team_id in (
        home_team_id,
        away_team_id
    ):
        return raw_team_id


    # Lag oversikt over hvilke spillere
    # som tilhører hvert lag i denne kampen.
    home_players = get_squad_player_ids(
        match.get("homeSquad")
    )

    away_players = get_squad_player_ids(
        match.get("awaySquad")
    )


    # Samle alle spiller-ID-er som hendelsen
    # forteller oss noe om.
    event_player_ids = set()

    for field in [
        "player",
        "scoredBy",
        "assistedBy",
        "subOn",
        "subOff"
    ]:

        player = event.get(field)

        if player and player.get("_id"):
            event_player_ids.add(
                player["_id"]
            )


    if not event_player_ids:
        # Vi har ingen trygg måte å vite laget på.
        return None


    home_hits = len(
        event_player_ids & home_players
    )

    away_hits = len(
        event_player_ids & away_players
    )


    # Alle spor peker mot hjemmelaget.
    if (
        home_hits > 0
        and away_hits == 0
    ):
        return home_team_id


    # Alle spor peker mot bortelaget.
    if (
        away_hits > 0
        and home_hits == 0
    ):
        return away_team_id


    # Tvetydig eller ukjent.
    # Ikke gjett.
    return None

def insert_events(conn, match):

    match_id = match["_id"]

    events = match.get("events") or []

    for index, event in enumerate(events):

        event_type_data = (
            event.get("type") or {}
        )

        event_name = (
            event_type_data.get("name")
        )

        event_type = (
            event_type_data.get("countAs")
        )


        # ----------------------------------------------------
        # Spillere som finnes inne i eventet
        # ----------------------------------------------------

        player = event.get("player")
        scored_by = event.get("scoredBy")
        assisted_by = event.get("assistedBy")
        sub_on = event.get("subOn")
        sub_off = event.get("subOff")


        player_id = upsert_player(
            conn,
            player
        )

        scored_by_id = upsert_player(
            conn,
            scored_by
        )

        assist_id = upsert_player(
            conn,
            assisted_by
        )

        sub_on_id = upsert_player(
            conn,
            sub_on
        )

        sub_off_id = upsert_player(
            conn,
            sub_off
        )


        # ----------------------------------------------------
        # Normaliser målscorer
        #
        # Branntall bruker noen ganger:
        # scoredBy
        #
        # og noen ganger:
        # player
        #
        # særlig på straffemål.
        # ----------------------------------------------------

        scorer_id = scored_by_id

        if (
            scorer_id is None
            and event_type in (
                "goal",
                "penaltyGoal",
                "ownGoal"
            )
        ):
            scorer_id = player_id


        # ----------------------------------------------------
        # Lag
        # ----------------------------------------------------

        team_id = resolve_event_team_id(
            match,
            event
        )


        # ----------------------------------------------------
        # Lagre event
        # ----------------------------------------------------

        conn.execute(
            """
            INSERT INTO events (
                match_id,
                event_index,

                minute,

                event_name,
                event_type,

                team_id,

                player_id,
                scorer_id,
                assist_id,

                sub_on_id,
                sub_off_id
            )

            VALUES (
                ?, ?,
                ?,
                ?, ?,
                ?,
                ?, ?, ?,
                ?, ?
            )
            """,
            (
                match_id,
                index,

                event.get("time"),

                event_name,
                event_type,

                team_id,

                player_id,
                scorer_id,
                assist_id,

                sub_on_id,
                sub_off_id
            )
        )


        # ----------------------------------------------------
        # Oppdater appearance hvis noen kommer inn
        # ----------------------------------------------------

        if (
            event_type == "subApp"
            and sub_on_id
            and team_id
        ):

            conn.execute(
                """
                UPDATE appearances

                SET
                    appeared = 1,
                    unused_substitute = 0,
                    entered_minute = ?

                WHERE
                    match_id = ?
                    AND team_id = ?
                    AND player_id = ?
                """,
                (
                    event.get("time"),
                    match_id,
                    team_id,
                    sub_on_id
                )
            )


        # ----------------------------------------------------
        # Registrer tidspunktet en spiller går ut
        # ----------------------------------------------------

        if (
            event_type == "subApp"
            and sub_off_id
            and team_id
        ):

            conn.execute(
                """
                UPDATE appearances

                SET exited_minute = ?

                WHERE
                    match_id = ?
                    AND team_id = ?
                    AND player_id = ?
                """,
                (
                    event.get("time"),
                    match_id,
                    team_id,
                    sub_off_id
                )
            )


# ============================================================
# IMPORTER ÉN JSON-FIL
# ============================================================

def import_file(conn, filepath):

    with filepath.open(
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)

    # Bare model!
    #
    # prev og next finnes også i filen,
    # men skal IKKE importeres her.
    match = data["result"]["data"]["model"]

    insert_match(
        conn,
        match,
        filepath.name
    )


    insert_squad(
        conn,
        match["_id"],
        match["homeTeam"],
        match.get("homeSquad")
    )


    insert_squad(
        conn,
        match["_id"],
        match["awayTeam"],
        match.get("awaySquad")
    )


    insert_events(
        conn,
        match
    )


# ============================================================
# KONTROLLSPØRRINGER
# ============================================================

def print_database_stats(conn):

    print()
    print("=" * 60)
    print("DATABASE BYGGET")
    print("=" * 60)
    print()

    tables = [
        "matches",
        "players",
        "teams",
        "competitions",
        "grounds",
        "appearances",
        "events"
    ]

    for table in tables:

        count = conn.execute(
            f"""
            SELECT COUNT(*)
            FROM {table}
            """
        ).fetchone()[0]

        print(
            f"{table:<20} {count:>8}"
        )


    print()
    print("BRANN-KONTROLLER")
    print("-" * 60)


    brann_starters = conn.execute(
        """
        SELECT COUNT(*)

        FROM appearances

        WHERE
            team_id = ?
            AND starting = 1
        """,
        (BRANN_ID,)
    ).fetchone()[0]


    brann_appearances = conn.execute(
        """
        SELECT COUNT(*)

        FROM appearances

        WHERE
            team_id = ?
            AND appeared = 1
        """,
        (BRANN_ID,)
    ).fetchone()[0]


    print(
        f"Brann-startere totalt: "
        f"{brann_starters}"
    )

    print(
        f"Brann-opptredener totalt: "
        f"{brann_appearances}"
    )


    print()
    print(
        "15 BRANN-SPILLERE MED "
        "FLEST KAMPER SIDEN 2000"
    )

    print("-" * 60)


    rows = conn.execute(
        """
        SELECT
            p.name,
            COUNT(*) AS matches

        FROM appearances a

        JOIN players p
            ON p.id = a.player_id

        WHERE
            a.team_id = ?
            AND a.appeared = 1

        GROUP BY
            a.player_id,
            p.name

        ORDER BY
            matches DESC,
            p.name ASC

        LIMIT 15
        """,
        (BRANN_ID,)
    ).fetchall()


    for name, matches in rows:

        print(
            f"{name:<35} "
            f"{matches:>4}"
        )


    print()
    print(
        "15 BRANN-SPILLERE MED "
        "FLEST MÅL SIDEN 2000"
    )

    print("-" * 60)


    rows = conn.execute(
        """
        SELECT
            p.name,
            COUNT(*) AS goals

        FROM events e

        JOIN players p
            ON p.id = e.scorer_id

        WHERE
            e.team_id = ?
            AND e.event_type IN (
                'goal',
                'penaltyGoal'
            )

        GROUP BY
            e.scorer_id,
            p.name

        ORDER BY
            goals DESC,
            p.name ASC

        LIMIT 15
        """,
        (BRANN_ID,)
    ).fetchall()


    for name, goals in rows:

        print(
            f"{name:<35} "
            f"{goals:>4}"
        )


# ============================================================
# HOVEDPROGRAM
# ============================================================

def main():

    files = sorted(
        DATA_DIR.glob("*.json")
    )

    print()
    print("=" * 60)
    print("BYGGER BRANNSPILLET-DATABASE")
    print("=" * 60)

    print()
    print(
        f"Fant {len(files)} "
        "JSON-filer."
    )


    if TEMP_DB_FILE.exists():
        TEMP_DB_FILE.unlink()


    conn = sqlite3.connect(
        TEMP_DB_FILE
    )

    try:

        create_tables(conn)


        for number, filepath in enumerate(
            files,
            start=1
        ):

            print(
                f"[{number}/{len(files)}] "
                f"{filepath.name}"
            )

            import_file(
                conn,
                filepath
            )


        conn.commit()


        # SQLite gjør en intern
        # integritetskontroll.
        result = conn.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]


        if result != "ok":
            raise RuntimeError(
                f"SQLite integrity_check: "
                f"{result}"
            )


        print_database_stats(conn)


    except Exception:

        conn.rollback()
        conn.close()

        print()
        print(
            "DATABASEBYGGING FEILET."
        )

        print(
            "Den gamle databasen "
            "er ikke rørt."
        )

        raise


    else:

        conn.close()


        # Først når ALT har fungert,
        # erstatter vi den gamle databasen.
        if DB_FILE.exists():
            DB_FILE.unlink()


        TEMP_DB_FILE.replace(
            DB_FILE
        )


        print()
        print("=" * 60)

        print(
            "FERDIG"
        )

        print("=" * 60)

        print()

        print(
            f"Database lagret som:"
        )

        print(
            DB_FILE
        )


if __name__ == "__main__":
    main()