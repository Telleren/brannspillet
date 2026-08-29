# Tenable YAML-oppgaver

Alle publiserbare Tenable-oppgaver ligger i `data/tenable/questions/`.

Hver `.yaml`-fil er én oppgave. For å publisere endringer til GitHub Pages:

```powershell
python -m pip install -r requirements.txt
python export_tenable_pages_data.py
```

Databasegenererte betaoppgaver kan fryses på nytt med:

```powershell
python export_tenable_yaml_questions.py --overwrite
```

Vær forsiktig med `--overwrite` hvis du har håndredigert databasegenererte filer.

## Minste format

```yaml
id: mitt-sporsmal
active: true
source: custom
period: modern
theme_id: custom
title: Min egen topp 10
description: Finn de 10 spillerne i min egen kategori.
metric: treff
start_year: 2000
end_year: 2026
cutoff_value: 1
opponent: null
slots:
  - value: 10
    answers:
      - name: Eksempelspiller
        aliases:
          - Etternavn
```

`period` må foreløpig være `classic` eller `modern`.

Hvis en plass er delt, legg flere spillere under samme `answers`-liste. Alle blir godkjent, men spillet viser fortsatt bare én synlig plass.
