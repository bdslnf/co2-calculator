# CO₂ Portfolio Calculator

**HSLU Digital Twin Programmieren**  
Nicola Beeli & Mattia Rohrer

Vollständiges Tool zur CO₂-Emissionsanalyse und Sanierungsplanung von Gebäuden.

---

## Funktionen

### Kernfunktionen
- CO₂-Emissionsberechnung nach KBOB-Faktoren  
- Sanierungsszenarien mit realistischen Schweizer Kosten  
- Wirtschaftlichkeitsanalyse (ROI, NPV, Amortisation)  
- Automatische Empfehlungen und Priorisierung  
- Integration von Fördergeldern (Gebäudeprogramm, Kantone)

### Erweiterte Analysen
- Portfolio-Management für mehrere Gebäude  
- Benchmark-Vergleiche (Minergie, SIA 380/1, CH-Durchschnitt)  
- Sensitivitätsanalysen (Energiepreise, CO₂-Abgaben)  
- CO₂-Preis-Szenarien (0–500 CHF/t)

### Outputs
- Interaktive Plotly-Visualisierungen (HTML)  
- Excel-Reports (mehrere Sheets, managementtauglich)  
- Text-Reports (Empfehlungen, Benchmarks)  
- Streamlit Web-App (interaktives Dashboard)

---

## Quick Start

### 1. Installation
```bash
cd co2_calculator
pip install -r requirements.txt

2. CLI-Version ausführen
cd src
python main.py


Output:

plots/ → HTML-Visualisierungen

reports/ → Text- und Excel-Reports

3. Streamlit Web-App starten
streamlit run app.py


Die App öffnet sich im Browser unter:
http://localhost:8501

Projektstruktur
co2_calculator/
├── data/
│   └── beispiel_emissionen_mit_jahr.csv
│   └── images/
├── src/
│   ├── main.py
│   ├── emissionen.py
│   ├── visualisierung.py
│   ├── sanierungen.py
│   ├── wirtschaftlichkeit.py
│   ├── empfehlungen.py
│   ├── benchmarks.py
│   ├── portfolio.py
│   └── excel_export.py
├── plots/
├── reports/
├── app.py
├── requirements.txt
└── README.md

Input-Datenformat

CSV mit folgenden Spalten:

Spalte	Typ	Erforderlich	Beschreibung
gebaeude_id	String	ja	Eindeutige Gebäude-ID
jahr	Integer	ja	Jahr
heizung_typ	String	ja	Gas, Öl, Fernwärme, Wärmepumpe, Pellets
jahresverbrauch_kwh	Float	ja	Heizenergie-Verbrauch
strom_kwh_jahr	Float	ja	Strom-Verbrauch
flaeche_m2	Float	optional	Energiebezugsfläche
baujahr	Integer	optional	Baujahr

Beispiel:

gebaeude_id,jahr,heizung_typ,jahresverbrauch_kwh,strom_kwh_jahr,flaeche_m2,baujahr
MFH_Hauptstrasse_12,2024,Gas,165000,46500,1200,1975
MFH_Bahnhofstr_5,2024,Öl,205000,39500,1400,1968

Gebäude-Bilder

Optional kann pro Gebäude ein Bild angezeigt werden.

Pfad:

data/images/


Namensschema:

<gebaeude_id>.jpg
<gebaeude_id>.jpeg
<gebaeude_id>.png


Beispiel:

data/images/MFH_Lindenweg_14.jpeg

Wirtschaftliche Annahmen (Beispiele)

Energiepreise und Emissionsfaktoren gemäss vereinfachten Annahmen

Förderungen als pauschale oder prozentuale Beiträge

Investitionen in CHF (Schweizer Format)

Beispiel:

Investition: CHF 33'000.-

Förderung: CHF 8'000.-

CO₂-Reduktion: 4.2 t/Jahr

Konfiguration
KBOB-Faktoren anpassen

Datei: src/emissionen.py

KBOB_FAKTOREN = {
    "Gas": 0.228,
    "Öl": 0.302,
    "Fernwärme": 0.095,
}

Sanierungskosten anpassen

Datei: src/sanierungen.py

SANIERUNGSKATALOG = {
    "heizung_gas_zu_wp": {
        "investition_chf": 45_000,
    }
}

Fördergelder anpassen

Datei: src/sanierungen.py

FOERDERGELDER = {
    "heizung_gas_zu_wp": {
        "gebaeudeprogramm_chf": 12_000,
        "kanton_zusatz_prozent": 20,
    }
}

Beispiel-Resultat (CLI)
EXECUTIVE SUMMARY
Portfolio: 5 Gebäude
Aktuell: 140.5 t CO₂e/Jahr

Beste Sanierung: Heizungsersatz Gas → Wärmepumpe
→ Investition: CHF 33'000.- (netto)
→ CO₂-Reduktion: 34.2 t/Jahr
→ ROI: 42.5 %
→ Amortisation: 8.2 Jahre

Hinweise

Studienprojekt im Rahmen der HSLU

Resultate sind indikativ

Kein Ersatz für Fachplanung

Team

Nicola Beeli
Mattia Rohrer

HSLU Digital Twin Programmieren (HS25)
