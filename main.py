"""
CO₂ Portfolio Calculator - Hauptprogramm
HSLU Digital Twin Programming
Autoren: Nicola, Mattia

Vollständige Analyse inkl.:
- CO₂-Emissionsberechnung
- Sanierungsszenarien mit Kosten-Nutzen
- Wirtschaftlichkeitsanalyse (ROI, NPV, Amortisation)
- Empfehlungen und Priorisierung
- Benchmark-Vergleiche
- Portfolio-Optimierung
"""

from pathlib import Path
import sys
import logging

import pandas as pd

# Lokale Module
from emissionen import (
    validiere_eingabedaten,
    berechne_emissionen,
    aggregiere_jaehrlich,
    berechne_kumulierte_emissionen,
    KBOB_FAKTOREN
)
from visualisierung import erstelle_alle_visualisierungen
from sanierungen import erstelle_alle_szenarien, erstelle_kombinationsszenarien
from wirtschaftlichkeit import wirtschaftlichkeitsanalyse
from empfehlungen import priorisiere_sanierungen, erstelle_empfehlungsbericht
from benchmarks import erstelle_benchmark_report
from portfolio import analysiere_portfolio, erstelle_portfolio_report, priorisiere_gebaeude_fuer_sanierung
from excel_export import exportiere_portfolio_excel, exportiere_empfehlungsbericht


# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


# Pfade
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PLOTS_DIR = ROOT / "plots"
REPORTS_DIR = ROOT / "reports"
CSV_INPUT = DATA_DIR / "beispiel_emissionen_mit_jahr.csv"


def main():
    """Hauptfunktion: Vollständige Analyse mit allen Features."""
    
    logger.info("=" * 70)
    logger.info("CO₂ PORTFOLIO CALCULATOR")
    logger.info("HSLU Digital Twin Programming | Nicola, Mattia")
    logger.info("=" * 70)
    
    # === 1. DATEN LADEN ===
    if not CSV_INPUT.exists():
        logger.error(f"CSV-Datei nicht gefunden: {CSV_INPUT}")
        logger.error("Erforderliche Spalten: gebaeude_id, jahr, heizung_typ,")
        logger.error("                       jahresverbrauch_kwh, strom_kwh_jahr")
        logger.error("Optional: flaeche_m2, baujahr")
        sys.exit(1)
    
    logger.info(f"\n[1/8] Lade Daten: {CSV_INPUT.name}")
    try:
        df = pd.read_csv(CSV_INPUT, encoding="utf-8")
        logger.info(f"{len(df)} Datensätze geladen")
    except Exception as e:
        logger.error(f"      Fehler: {e}")
        sys.exit(1)
    
    # === 2. VALIDIERUNG ===
    logger.info("\n[2/8] Validiere Eingabedaten...")
    fehler = validiere_eingabedaten(df)
    
    if fehler:
        for f in fehler:
            if "Warnung" in f:
                logger.warning(f"      {f}")
            else:
                logger.error(f"      {f}")
        
        kritische_fehler = [f for f in fehler if "Fehlende" in f or "Negative" in f]
        if kritische_fehler:
            logger.error("\n      Abbruch wegen kritischer Fehler.")
            sys.exit(1)
    else:
        logger.info("Validierung erfolgreich")
    
    # === 3. EMISSIONEN BERECHNEN ===
    logger.info("\n[3/8] Berechne CO₂-Emissionen...")
    df_mit_emissionen = berechne_emissionen(df)
    df_yearly = aggregiere_jaehrlich(df_mit_emissionen)
    df_kumuliert = berechne_kumulierte_emissionen(df_yearly)
    
    gesamt_emissionen_t = df_mit_emissionen["emissionen_gesamt_t"].sum()
    anzahl_gebaeude = df["gebaeude_id"].nunique()
    logger.info(f"      ✓ {anzahl_gebaeude} Gebäude analysiert")
    logger.info(f"      ✓ Gesamt: {gesamt_emissionen_t:,.1f} t CO₂e")
    
    # === 4. PORTFOLIO-ANALYSE ===
    logger.info("\n[4/8] Portfolio-Analyse...")
    
    # Aktuelles Jahr (letztes Jahr in Daten)
    aktuelles_jahr = df["jahr"].max()
    df_aktuell = df_mit_emissionen[df_mit_emissionen["jahr"] == aktuelles_jahr].copy()
    
    portfolio_stats = analysiere_portfolio(df_aktuell, KBOB_FAKTOREN)
    logger.info(f"Portfolio-Report erstellt")
    
    # Portfolio-Report speichern
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    portfolio_report_text = erstelle_portfolio_report(df_aktuell, KBOB_FAKTOREN)
    portfolio_txt_path = REPORTS_DIR / "portfolio_analyse.txt"
    with open(portfolio_txt_path, "w", encoding="utf-8") as f:
        f.write(portfolio_report_text)
    logger.info(f"      → {portfolio_txt_path.relative_to(ROOT)}")
    
    # === 5. SANIERUNGSSZENARIEN ERSTELLEN ===
    logger.info("\n[5/8] Erstelle Sanierungsszenarien...")
    
    alle_sanierungen = []
    
    for idx, gebaeude in df_aktuell.iterrows():
        # Alle Szenarien für dieses Gebäude
        szenarien = erstelle_alle_szenarien(gebaeude, KBOB_FAKTOREN)
        
        # Wirtschaftlichkeit berechnen
        for san in szenarien:
            san_wirtschaft = wirtschaftlichkeitsanalyse(san, gebaeude)
            san_wirtschaft["gebaeude_id"] = gebaeude["gebaeude_id"]
            alle_sanierungen.append(san_wirtschaft)
        
        # Kombinationsszenarien
        kombinationen = erstelle_kombinationsszenarien(gebaeude, KBOB_FAKTOREN)
        for kombi in kombinationen:
            kombi_wirtschaft = wirtschaftlichkeitsanalyse(kombi, gebaeude)
            kombi_wirtschaft["gebaeude_id"] = gebaeude["gebaeude_id"]
            alle_sanierungen.append(kombi_wirtschaft)
    
    logger.info(f"{len(alle_sanierungen)} Szenarien berechnet")
    
    # === 6. EMPFEHLUNGEN GENERIEREN ===
    logger.info("\n[6/8] Generiere Empfehlungen...")
    
    sanierungen_priorisiert = priorisiere_sanierungen(alle_sanierungen, kriterium="score")
    
    # Empfehlungsbericht
    empfehlungsbericht = erstelle_empfehlungsbericht(sanierungen_priorisiert, top_n=5)
    empfehlung_path = REPORTS_DIR / "empfehlungen.txt"
    exportiere_empfehlungsbericht(empfehlung_path, empfehlungsbericht)
    
    logger.info(f"Top-5 Empfehlungen erstellt")
    logger.info(f"      → {empfehlung_path.relative_to(ROOT)}")
    
    # Top-Sanierung für Detail-Report
    top_sanierung = sanierungen_priorisiert.iloc[0].to_dict()
    logger.info(f"      → Beste Massnahme: {top_sanierung['name']}")
    logger.info(f"        Amortisation: {top_sanierung['amortisation_jahre']:.1f} Jahre")
    logger.info(f"        CO₂-Reduktion: {top_sanierung['co2_einsparung_kg_jahr']/1000:.1f} t/Jahr")
    
    # === 7. VISUALISIERUNGEN ===
    logger.info("\n[7/8] Erstelle Visualisierungen...")
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    
    plots = erstelle_alle_visualisierungen(df_yearly, df_kumuliert, PLOTS_DIR)
    logger.info(f"{len(plots)} Basis-Diagramme erstellt")
    
    # === 8. EXCEL-EXPORT ===
    logger.info("\n[8/8] Excel-Export...")
    
    excel_path = REPORTS_DIR / "co2_analyse_komplett.xlsx"
    exportiere_portfolio_excel(
        excel_path,
        portfolio_stats,
        df_aktuell,
        sanierungen_priorisiert,
        top_sanierung
    )
    
    logger.info(f"      ✓ Excel-Report erstellt")
    logger.info(f"      → {excel_path.relative_to(ROOT)}")
    
    # === BENCHMARK-REPORTS (Optional für jedes Gebäude) ===
    logger.info("\n[BONUS] Benchmark-Analysen...")
    benchmark_dir = REPORTS_DIR / "benchmarks"
    benchmark_dir.mkdir(exist_ok=True)
    
    for idx, gebaeude in df_aktuell.iterrows():
        emissionen = gebaeude["emissionen_gesamt_kg"]
        report = erstelle_benchmark_report(gebaeude, emissionen)
        
        benchmark_file = benchmark_dir / f"benchmark_{gebaeude['gebaeude_id']}.txt"
        with open(benchmark_file, "w", encoding="utf-8") as f:
            f.write(report)
    
    logger.info(f"{len(df_aktuell)} Benchmark-Reports erstellt")
    logger.info(f"{benchmark_dir.relative_to(ROOT)}")
    
    # === ZUSAMMENFASSUNG ===
    logger.info("\n" + "=" * 70)
    logger.info("EXECUTIVE SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Portfolio: {anzahl_gebaeude} Gebäude")
    logger.info(f"Aktuell: {gesamt_emissionen_t:,.1f} t CO₂e/Jahr")
    logger.info(f"")
    logger.info(f"Beste Sanierung: {top_sanierung['name']}")
    logger.info(f"  → Investition: CHF {top_sanierung['investition_netto_chf']:,.0f} (netto)")
    logger.info(f"  → CO₂-Reduktion: {top_sanierung['co2_einsparung_kg_jahr']/1000:.1f} t/Jahr")
    logger.info(f"  → ROI: {top_sanierung['roi_prozent']:.1f}%")
    logger.info(f"  → Amortisation: {top_sanierung['amortisation_jahre']:.1f} Jahre")
    logger.info("")
    logger.info("ERGEBNISSE:")
    logger.info(f"  📊 Visualisierungen: {PLOTS_DIR.relative_to(ROOT)}")
    logger.info(f"  📄 Reports: {REPORTS_DIR.relative_to(ROOT)}")
    logger.info(f"  📈 Excel: {excel_path.name}")
    logger.info("=" * 70)
    logger.info("✓ Analyse abgeschlossen!")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
