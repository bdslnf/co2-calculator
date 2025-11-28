"""
Empfehlungssystem für Sanierungsmassnahmen
Priorisiert Massnahmen nach verschiedenen Kriterien
"""

from typing import List, Dict
import pandas as pd


def berechne_prioritaets_score(
    sanierung: Dict,
    gewichtung: Dict = None
) -> float:
    """
    Berechnet Gesamt-Score für Priorisierung.
    
    Args:
        sanierung: Sanierungsszenario mit Wirtschaftlichkeits-Daten
        gewichtung: Optional, Custom-Gewichtung der Kriterien
        
    Returns:
        Score (0-100, höher = besser)
    """
    if gewichtung is None:
        # Standard-Gewichtung
        gewichtung = {
            "co2_effizienz": 0.35,      # CO₂-Reduktion pro CHF
            "amortisation": 0.25,       # Schnelle Amortisation
            "npv": 0.20,                # Nettobarwert
            "co2_absolut": 0.20,        # Absolute CO₂-Reduktion
        }
    
    scores = {}
    
    # CO₂-Effizienz (kg CO₂ pro CHF Investition)
    inv = sanierung.get("investition_netto_chf", 1)
    co2 = sanierung.get("co2_einsparung_kg_jahr", 0)
    if inv > 0:
        co2_effizienz = (co2 * sanierung.get("lebensdauer_jahre", 20)) / inv
        scores["co2_effizienz"] = min(co2_effizienz * 10, 100)  # Normalisiert
    else:
        scores["co2_effizienz"] = 0
    
    # Amortisation (je kürzer, desto besser)
    amort = sanierung.get("amortisation_jahre", float('inf'))
    if amort < float('inf'):
        # Score: 100 bei 5 Jahren, 0 bei 30+ Jahren
        scores["amortisation"] = max(0, 100 - (amort - 5) * 4)
    else:
        scores["amortisation"] = 0
    
    # NPV (normalisiert auf Investition)
    npv = sanierung.get("npv_chf", 0)
    if inv > 0:
        npv_ratio = (npv / inv) * 100
        scores["npv"] = min(max(npv_ratio, 0), 100)
    else:
        scores["npv"] = 0
    
    # Absolute CO₂-Reduktion
    # Score: 100 bei 20t/Jahr, linear skaliert
    co2_absolut_t = co2 / 1000
    scores["co2_absolut"] = min(co2_absolut_t * 5, 100)
    
    # Gewichteter Gesamt-Score
    gesamt_score = sum(scores[k] * gewichtung[k] for k in gewichtung.keys())
    
    return gesamt_score


def priorisiere_sanierungen(
    sanierungen: List[Dict],
    kriterium: str = "score",
    gewichtung: Dict = None
) -> pd.DataFrame:
    """
    Sortiert Sanierungen nach gewähltem Kriterium.
    
    Args:
        sanierungen: Liste mit Sanierungsszenarien (mit Wirtschaftlichkeits-Daten)
        kriterium: "score", "co2", "roi", "amortisation", "npv"
        gewichtung: Optional, Custom-Gewichtung für Score
        
    Returns:
        Sortierter DataFrame mit Ranking
    """
    # Scores berechnen
    for san in sanierungen:
        san["prioritaets_score"] = berechne_prioritaets_score(san, gewichtung)
    
    df = pd.DataFrame(sanierungen)
    
    # Sortieren
    if kriterium == "score":
        df = df.sort_values("prioritaets_score", ascending=False)
    elif kriterium == "co2":
        df = df.sort_values("co2_einsparung_kg_jahr", ascending=False)
    elif kriterium == "roi":
        df = df.sort_values("roi_prozent", ascending=False)
    elif kriterium == "amortisation":
        df = df.sort_values("amortisation_jahre", ascending=True)
    elif kriterium == "npv":
        df = df.sort_values("npv_chf", ascending=False)
    
    # Ranking hinzufügen
    df["rang"] = range(1, len(df) + 1)
    
    return df.reset_index(drop=True)


def generiere_empfehlung(
    sanierung: Dict,
    rang: int,
    gesamt_anzahl: int
) -> str:
    """
    Generiert textuelle Empfehlung für eine Sanierung.
    
    Args:
        sanierung: Sanierungsszenario mit allen Daten
        rang: Rang im Ranking (1 = beste)
        gesamt_anzahl: Gesamtzahl betrachteter Sanierungen
        
    Returns:
        Empfehlungstext
    """
    name = sanierung["name"]
    score = sanierung.get("prioritaets_score", 0)
    
    # Prioritätsstufe
    if rang == 1:
        prioritaet = "🟢 HÖCHSTE PRIORITÄT"
    elif rang <= gesamt_anzahl * 0.3:
        prioritaet = "🟡 HOHE PRIORITÄT"
    elif rang <= gesamt_anzahl * 0.7:
        prioritaet = "🟠 MITTLERE PRIORITÄT"
    else:
        prioritaet = "⚪ NIEDRIGE PRIORITÄT"
    
    # Hauptempfehlung
    empfehlung = f"{prioritaet} - Rang {rang} von {gesamt_anzahl}\n"
    empfehlung += f"Massnahme: {name}\n"
    empfehlung += f"Prioritäts-Score: {score:.1f}/100\n\n"
    
    # Wirtschaftliche Kennzahlen
    amort = sanierung.get("amortisation_jahre", 0)
    npv = sanierung.get("npv_chf", 0)
    roi = sanierung.get("roi_prozent", 0)
    co2 = sanierung.get("co2_einsparung_kg_jahr", 0) / 1000
    
    empfehlung += "WIRTSCHAFTLICHKEIT:\n"
    empfehlung += f"  • Amortisation: {amort:.1f} Jahre\n"
    empfehlung += f"  • ROI: {roi:.1f}% über Lebensdauer\n"
    empfehlung += f"  • Nettobarwert: CHF {npv:,.0f}\n\n"
    
    empfehlung += "UMWELT:\n"
    empfehlung += f"  • CO₂-Reduktion: {co2:.1f} t/Jahr\n"
    
    lebensdauer = sanierung.get("lebensdauer_jahre", 20)
    co2_gesamt = co2 * lebensdauer
    empfehlung += f"  • CO₂-Reduktion gesamt: {co2_gesamt:.0f} t über {lebensdauer} Jahre\n\n"
    
    # Kosten
    inv_brutto = sanierung.get("investition_brutto_chf", 0)
    foerderung = sanierung.get("foerderung_chf", 0)
    inv_netto = sanierung.get("investition_netto_chf", 0)
    
    empfehlung += "KOSTEN:\n"
    empfehlung += f"  • Investition brutto: CHF {inv_brutto:,.0f}\n"
    empfehlung += f"  • Fördergelder: CHF {foerderung:,.0f}\n"
    empfehlung += f"  • Investition netto: CHF {inv_netto:,.0f}\n\n"
    
    # Begründung
    empfehlung += "BEGRÜNDUNG:\n"
    
    if score >= 70:
        empfehlung += "  ✓ Hervorragendes Kosten-Nutzen-Verhältnis\n"
    elif score >= 50:
        empfehlung += "  ✓ Gutes Kosten-Nutzen-Verhältnis\n"
    else:
        empfehlung += "  ⚠ Moderates Kosten-Nutzen-Verhältnis\n"
    
    if amort < 10:
        empfehlung += f"  ✓ Schnelle Amortisation ({amort:.1f} Jahre)\n"
    elif amort < 20:
        empfehlung += f"  ~ Moderate Amortisation ({amort:.1f} Jahre)\n"
    else:
        empfehlung += f"  ⚠ Lange Amortisation ({amort:.1f} Jahre)\n"
    
    if npv > 0:
        empfehlung += f"  ✓ Positiver Nettobarwert (CHF {npv:,.0f})\n"
    else:
        empfehlung += f"  ⚠ Negativer Nettobarwert (CHF {npv:,.0f})\n"
    
    if co2 > 5:
        empfehlung += f"  ✓ Hohe CO₂-Reduktion ({co2:.1f} t/Jahr)\n"
    elif co2 > 2:
        empfehlung += f"  ~ Moderate CO₂-Reduktion ({co2:.1f} t/Jahr)\n"
    else:
        empfehlung += f"  ⚠ Geringe CO₂-Reduktion ({co2:.1f} t/Jahr)\n"
    
    empfehlung += "\n" + "="*60 + "\n"
    
    return empfehlung


def erstelle_empfehlungsbericht(
    sanierungen_df: pd.DataFrame,
    top_n: int = 3
) -> str:
    """
    Erstellt vollständigen Empfehlungsbericht.
    
    Args:
        sanierungen_df: Priorisierter DataFrame mit Sanierungen
        top_n: Anzahl Top-Empfehlungen
        
    Returns:
        Vollständiger Berichtstext
    """
    bericht = "="*60 + "\n"
    bericht += "SANIERUNGSEMPFEHLUNG - EXECUTIVE SUMMARY\n"
    bericht += "="*60 + "\n\n"
    
    # Übersicht
    gesamt_co2 = sanierungen_df["co2_einsparung_kg_jahr"].sum() / 1000
    gesamt_inv = sanierungen_df["investition_netto_chf"].sum()
    
    bericht += f"Analysierte Massnahmen: {len(sanierungen_df)}\n"
    bericht += f"Gesamt CO₂-Potential: {gesamt_co2:.1f} t/Jahr\n"
    bericht += f"Gesamt Investition (netto): CHF {gesamt_inv:,.0f}\n\n"
    
    # Top-Empfehlungen
    bericht += f"TOP {top_n} EMPFEHLUNGEN:\n"
    bericht += "="*60 + "\n\n"
    
    for idx, row in sanierungen_df.head(top_n).iterrows():
        bericht += generiere_empfehlung(row.to_dict(), row["rang"], len(sanierungen_df))
    
    # Weitere Optionen
    if len(sanierungen_df) > top_n:
        bericht += "\nWEITERE OPTIONEN:\n"
        bericht += "-"*60 + "\n"
        for idx, row in sanierungen_df.iloc[top_n:].iterrows():
            bericht += f"{row['rang']}. {row['name']}: "
            bericht += f"Amortisation {row['amortisation_jahre']:.1f}J, "
            bericht += f"CO₂ {row['co2_einsparung_kg_jahr']/1000:.1f}t/J, "
            bericht += f"Score {row['prioritaets_score']:.0f}/100\n"
    
    bericht += "\n" + "="*60 + "\n"
    bericht += "HINWEIS: Alle Berechnungen basieren auf Annahmen.\n"
    bericht += "Für detaillierte Planung Fachperson konsultieren.\n"
    bericht += "="*60 + "\n"
    
    return bericht


def vergleiche_szenarien(
    szenarien: List[Dict],
    kriterien: List[str] = None
) -> pd.DataFrame:
    """
    Erstellt Vergleichstabelle für Szenarien.
    
    Args:
        szenarien: Liste mit Szenarien
        kriterien: Zu vergleichende Kriterien
        
    Returns:
        Vergleichs-DataFrame
    """
    if kriterien is None:
        kriterien = [
            "name",
            "investition_netto_chf",
            "co2_einsparung_kg_jahr",
            "amortisation_jahre",
            "roi_prozent",
            "npv_chf",
            "prioritaets_score",
        ]
    
    vergleich = []
    
    for san in szenarien:
        zeile = {k: san.get(k, 0) for k in kriterien}
        vergleich.append(zeile)
    
    df = pd.DataFrame(vergleich)
    
    # Formatierung
    if "investition_netto_chf" in df.columns:
        df["investition_netto_chf"] = df["investition_netto_chf"].round(0)
    if "co2_einsparung_kg_jahr" in df.columns:
        df["co2_einsparung_t_jahr"] = (df["co2_einsparung_kg_jahr"] / 1000).round(2)
        df = df.drop("co2_einsparung_kg_jahr", axis=1)
    if "amortisation_jahre" in df.columns:
        df["amortisation_jahre"] = df["amortisation_jahre"].round(1)
    if "roi_prozent" in df.columns:
        df["roi_prozent"] = df["roi_prozent"].round(1)
    if "npv_chf" in df.columns:
        df["npv_chf"] = df["npv_chf"].round(0)
    if "prioritaets_score" in df.columns:
        df["prioritaets_score"] = df["prioritaets_score"].round(0)
    
    return df


def portfolio_optimierung(
    gebaeude_liste: List[pd.Series],
    budget_chf: float,
    emissionsfaktoren: Dict
) -> Dict:
    """
    Optimiert Sanierungsstrategie für Portfolio unter Budgetrestriktion.
    
    Args:
        gebaeude_liste: Liste mit Gebäude-Series
        budget_chf: Verfügbares Budget
        emissionsfaktoren: CO₂-Faktoren
        
    Returns:
        Dictionary mit optimaler Allokation
    """
    from sanierungen import erstelle_alle_szenarien
    from wirtschaftlichkeit import wirtschaftlichkeitsanalyse
    
    # Alle Sanierungen für alle Gebäude sammeln
    alle_optionen = []
    
    for geb in gebaeude_liste:
        geb_id = geb["gebaeude_id"]
        szenarien = erstelle_alle_szenarien(geb, emissionsfaktoren)
        
        for san in szenarien:
            # Wirtschaftlichkeit berechnen
            san_wirtschaft = wirtschaftlichkeitsanalyse(san, geb)
            san_wirtschaft["gebaeude_id"] = geb_id
            san_wirtschaft["prioritaets_score"] = berechne_prioritaets_score(san_wirtschaft)
            alle_optionen.append(san_wirtschaft)
    
    # Nach Score sortieren
    df = pd.DataFrame(alle_optionen)
    df = df.sort_values("prioritaets_score", ascending=False)
    
    # Greedy-Auswahl unter Budget
    ausgewaehlte = []
    restbudget = budget_chf
    
    for idx, row in df.iterrows():
        inv = row["investition_netto_chf"]
        if inv <= restbudget:
            ausgewaehlte.append(row.to_dict())
            restbudget -= inv
    
    # Zusammenfassung
    if ausgewaehlte:
        gesamt_inv = sum(s["investition_netto_chf"] for s in ausgewaehlte)
        gesamt_co2 = sum(s["co2_einsparung_kg_jahr"] for s in ausgewaehlte) / 1000
        
        return {
            "anzahl_massnahmen": len(ausgewaehlte),
            "massnahmen": ausgewaehlte,
            "gesamt_investition_chf": gesamt_inv,
            "verbleibendes_budget_chf": restbudget,
            "gesamt_co2_reduktion_t_jahr": gesamt_co2,
            "budget_ausnutzung_prozent": (gesamt_inv / budget_chf) * 100,
        }
    else:
        return {
            "anzahl_massnahmen": 0,
            "massnahmen": [],
            "gesamt_investition_chf": 0,
            "verbleibendes_budget_chf": budget_chf,
            "gesamt_co2_reduktion_t_jahr": 0,
            "budget_ausnutzung_prozent": 0,
        }
