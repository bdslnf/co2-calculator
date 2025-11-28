# CO₂ Neutrality Path Calculator

**HSLU Digital Twin Programming** | Nicola Beeli, Manuel Flühler, Domenic Zogg, Fabrice Bachofner Sarn

Vollständiges Tool für CO₂-Emissionsanalyse und Sanierungsplanung von Gebäuden.

---

## 🎯 Features

### ✅ Kern-Funktionen
- **CO₂-Emissionsberechnung** nach KBOB-Faktoren
- **Sanierungsszenarien** mit realistischen Schweizer Kosten
- **Wirtschaftlichkeitsanalyse**: ROI, NPV, Amortisation
- **Automatische Empfehlungen** und Priorisierung
- **Fördergelder-Integration** (Gebäudeprogramm, Kantone)

### ✅ Erweiterte Analysen
- **Portfolio-Management** für mehrere Gebäude
- **Benchmark-Vergleiche** (Minergie, SIA 380/1, CH-Durchschnitt)
- **Sensitivitätsanalysen** (Energiepreise, CO₂-Abgaben)
- **CO₂-Preis-Szenarien** (0-500 CHF/t)

### ✅ Outputs
- **Interaktive Plotly-Visualisierungen** (HTML)
- **Excel-Reports** (mehrere Sheets, Management-tauglich)
- **Text-Reports** (Empfehlungen, Benchmarks)
- **Streamlit Web-App** (interaktives Dashboard)

---

## 🚀 Quick Start

### 1. Installation

```bash
# In Projektordner navigieren
cd co2_calculator

# Dependencies installieren
pip install -r requirements.txt
```

### 2. CLI-Version ausführen

```bash
cd src
python main.py
```

**Output:**
- `plots/` → HTML-Visualisierungen
- `reports/` → Text- und Excel-Reports

### 3. Streamlit Web-App starten

```bash
streamlit run app.py
```

**Öffnet automatisch im Browser:** `http://localhost:8501`

---

## 📁 Projektstruktur

```
co2_calculator/
├── data/
│   └── beispiel_emissionen_mit_jahr.csv    # Input-Daten
├── src/
│   ├── main.py                             # CLI Hauptprogramm
│   ├── emissionen.py                       # CO₂-Berechnungen
│   ├── visualisierung.py                   # Plotly-Diagramme
│   ├── sanierungen.py                      # Sanierungsszenarien
│   ├── wirtschaftlichkeit.py               # ROI, NPV, Amortisation
│   ├── empfehlungen.py                     # Priorisierung
│   ├── benchmarks.py                       # Standards-Vergleiche
│   ├── portfolio.py                        # Multi-Gebäude-Analyse
│   └── excel_export.py                     # Excel-Reports
├── plots/                                  # Output: Visualisierungen
├── reports/                                # Output: Reports
├── app.py                                  # Streamlit Web-App
├── requirements.txt
└── README.md
```

---

## 📊 Input-Datenformat

**CSV mit folgenden Spalten:**

| Spalte | Typ | Erforderlich | Beschreibung |
|--------|-----|--------------|--------------|
| `gebaeude_id` | string | ✅ | Eindeutige Gebäude-ID |
| `jahr` | int | ✅ | Jahr |
| `heizung_typ` | string | ✅ | Gas, Öl, Fernwärme, Wärmepumpe, Pellets |
| `jahresverbrauch_kwh` | float | ✅ | Heizenergie-Verbrauch |
| `strom_kwh_jahr` | float | ✅ | Strom-Verbrauch |
| `flaeche_m2` | float | ⭕ | Energiebezugsfläche (für Benchmarks) |
| `baujahr` | int | ⭕ | Baujahr (für Vergleiche) |

**Beispiel:**
```csv
gebaeude_id,jahr,heizung_typ,jahresverbrauch_kwh,strom_kwh_jahr,flaeche_m2,baujahr
MFH_Hauptstrasse_12,2024,Gas,165000,46500,1200,1975
MFH_Bahnhofstr_5,2024,Öl,205000,39500,1400,1968
```

---

## 💡 Verwendung

### CLI-Workflow

```bash
cd src
python main.py
```

**Das Programm:**
1. Validiert Eingabedaten
2. Berechnet CO₂-Emissionen (KBOB)
3. Erstellt alle Sanierungsszenarien
4. Berechnet Wirtschaftlichkeit (ROI, NPV, Amortisation)
5. Generiert Empfehlungen mit Ranking
6. Erstellt Benchmarks (Minergie, SIA, CH-Durchschnitt)
7. Exportiert Visualisierungen (Plotly HTML)
8. Exportiert Excel-Report

**Output-Dateien:**
```
plots/
├── 01_balken_kumuliert_gesamt.html
├── 02_linien_jaehrlich.html
└── 03_linien_kumuliert.html

reports/
├── co2_analyse_komplett.xlsx        # Excel mit allen Daten
├── portfolio_analyse.txt            # Portfolio-Übersicht
├── empfehlungen.txt                 # Top-5 Empfehlungen
└── benchmarks/                      # Benchmark pro Gebäude
    ├── benchmark_MFH_Hauptstrasse_12.txt
    └── ...
```

### Streamlit Web-App

```bash
streamlit run app.py
```

**Features:**
- 📊 Portfolio-Übersicht mit Kennzahlen
- 🏢 Gebäude-Detail-Analyse
- 💡 Interaktive Sanierungsszenarien
- 🔧 Filter nach Kategorie, Budget
- 📈 Kosten-Nutzen-Diagramme
- 🔬 Sensitivitätsanalysen
- ⚖️ Gebäude-Vergleich

---

## 🔧 Konfiguration

### KBOB-Emissionsfaktoren anpassen

**Datei:** `src/emissionen.py`

```python
KBOB_FAKTOREN = {
    "Gas": 0.228,        # kg CO₂e/kWh
    "Öl": 0.302,
    "Fernwärme": 0.095,
    # ... anpassen
}
```

### Sanierungskosten anpassen

**Datei:** `src/sanierungen.py`

```python
SANIERUNGSKATALOG = {
    "heizung_gas_zu_wp": {
        "investition_chf": 45000,  # Anpassen
        # ...
    }
}
```

### Fördergelder anpassen

**Datei:** `src/sanierungen.py`

```python
FOERDERGELDER = {
    "heizung_gas_zu_wp": {
        "gebaeudeprogramm_chf": 12000,  # Anpassen
        "kanton_zusatz_prozent": 20,
    }
}
```

---

## 📈 Ergebnisse

### Beispiel-Output

**Executive Summary (CLI):**
```
==================================================================
EXECUTIVE SUMMARY
==================================================================
Portfolio: 5 Gebäude
Aktuell: 140.5 t CO₂e/Jahr

Beste Sanierung: Heizungsersatz Gas → Wärmepumpe
  → Investition: CHF 33,000 (netto)
  → CO₂-Reduktion: 34.2 t/Jahr
  → ROI: 42.5%
  → Amortisation: 8.2 Jahre
==================================================================
```

**Excel-Report:**
- Sheet 1: Übersicht (Portfolio-Kennzahlen)
- Sheet 2: Gebäude-Daten (alle Gebäude)
- Sheet 3: Sanierungsempfehlungen (Ranking)
- Sheet 4: Wirtschaftlichkeit Detail (Top-Sanierung mit Cashflow)

---

## 🧪 Tests

```bash
cd tests
pytest test_emissionen.py
pytest test_sanierungen.py
pytest test_wirtschaftlichkeit.py
```

---

## 📚 Hintergrund

### KBOB-Faktoren

Schweizer Ökobilanzdaten im Baubereich (KBOB 2022/1:2022):
- **Gas:** 0.228 kg CO₂e/kWh (inkl. Vorkette)
- **Öl:** 0.302 kg CO₂e/kWh
- **Strom CH-Mix:** 0.122 kg CO₂e/kWh

### Standards

- **Minergie:** ≤ 38 kWh/m²/Jahr Heizwärmebedarf
- **SIA 380/1:2024:** ≤ 30 kWh/m²/Jahr (Neubau)
- **Netto-Null 2050:** 0 kg CO₂e/m²/Jahr

### Fördergelder

- **Gebäudeprogramm:** Pauschal 12'000-15'000 CHF (Heizung)
- **Kantonale Zusätze:** Bis 20% der Investition
- **PV-Einmalvergütung:** 380 CHF/kWp

---

## 🛠️ Entwicklung

### Neue Sanierung hinzufügen

1. **In `sanierungen.py`:**
   ```python
   SANIERUNGSKATALOG["neue_massnahme"] = {
       "name": "Meine Massnahme",
       "kategorie": "...",
       "investition_chf": 10000,
       "lebensdauer_jahre": 20,
   }
   ```

2. **Förderung definieren (optional):**
   ```python
   FOERDERGELDER["neue_massnahme"] = {
       "gebaeudeprogramm_chf": 2000,
   }
   ```

3. **In `erstelle_alle_szenarien()` integrieren**

---

## 📝 To-Do / Erweiterungen

- [ ] API-Integration (Gebäuderegister BFS)
- [ ] Graue Energie (Bau-Emissionen)
- [ ] PDF-Export
- [ ] Mehr Visualisierungen (Sankey, Waterfall)
- [ ] User-Authentication (Multi-User Streamlit)
- [ ] Datenbank-Backend (PostgreSQL)

---

## 📞 Support

**Team:**
- Nicola Beeli
- Manuel Flühler
- Domenic Zogg
- Fabrice Bachofner Sarn

**Projekt:** HSLU Digital Twin Programming (HS25)

---

## 📄 Lizenz

Akademisches Projekt - HSLU 2025
