from pathlib import Path


OUTPUT_FILE = Path("docs/tenable/questions.json")
QUESTION_SOURCE_DIR = Path("data/tenable/questions")

PERIODS = [
    {
        "id": "since-1963",
        "label": "Siden 1963",
        "start_year": 1963,
        "end_year": 2026,
    },
    {
        "id": "since-2000",
        "label": "Siden 2000",
        "start_year": 2000,
        "end_year": 2026,
    },
]

GENERAL_THEMES = [
    "kamper",
    "starter",
    "innhopp",
    "maal",
    "seire",
    "utlendinger-kamper",
    "utlendinger-maal",
    "brannspillere-mot-brann",
]

OPPONENT_THEMES = [
    {
        "theme_id": "kamper-mot",
        "opponent": "Rosenborg",
    },
    {
        "theme_id": "kamper-mot",
        "opponent": "Lillestrøm",
    },
    {
        "theme_id": "kamper-mot",
        "opponent": "Viking",
    },
    {
        "theme_id": "kamper-mot",
        "opponent": "Vålerenga",
    },
]
