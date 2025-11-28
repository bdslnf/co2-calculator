"""
Portfolio-Analyse für mehrere Gebäude
Vergleicht, priorisiert und optimiert Sanierungsstrategien
"""

from typing import List, Dict
import pandas as pd


def analysiere_portfolio(
    df: pd.DataFrame,
    emissionsfaktoren: Dict
) -> Dict:
    """
    Analysiert gesamtes Gebäude-Portfolio.
    
    Args:
        df: DataFrame mit mehreren Gebäuden (mit berechneten Emissionen)
        emissionsfaktoren: CO₂-Faktoren
        
    Returns:
        Dictionary mit Portfolio-Kennzahlen
    """
    from emissionen import aggregiere_jaehrlich
    
    # Aggregation
    gesamt_emissionen_t = df["emissionen_gesamt_t"].sum()
    anzahl_gebaeude = df["gebaeude_id"].nunique()
    
    # Durchschnitte
    durchschnitt_emissionen_t = gesamt_emissionen_t / anzahl_gebaeude
    
    # Heizungstypen-Verteilung
    heizungstypen = df.groupby("heizung_typ")["gebaeude_id"].nunique().to_dict()
    
    # Flächenanalyse (wenn vorhanden)
    if "flaeche_m2" in df.columns:
        gesamt_flaeche = df["flaeche_m2"].sum()
        durchschnitt_emissionen_pro_m2 = (gesamt_emissionen_t * 1000) / gesamt_flaeche if gesamt_flaeche > 0 else 0
    else:
        gesamt_flaeche = None
        durchschnitt_emissionen_pro_m2 = None
    
    # Top-Emittenten
    top_emittenten = df.nlargest(5, "emissionen_gesamt_t")[["gebaeude_id", "emissionen_gesamt_t"]].to_dict("records")
    
    return {
        "anzahl_gebaeude": anzahl_gebaeude,
        "gesamt_emissionen_t_jahr": gesamt_emissionen_t,
        "durchschnitt_emissionen_t_jahr": durchschnitt_emissionen_t,
        "gesamt_flaeche_m2": gesamt_flaeche,
        "durchschnitt_emissionen_kg_m2": durchschnitt_emissionen_pro_m2,
        "heizungstypen_verteilung": heizungstypen,
        "top_emittenten": top_emittenten,
    }


def priorisiere_gebaeude_fuer_sanierung(
    df: pd.DataFrame,
    emissionsfaktoren: Dict,
    kriterium: str = "emissionen"
) -> pd.DataFrame:
    """
    Priorisiert Gebäude für Sanierung.
    
    Args:
        df: DataFrame mit Gebäuden
        emissionsfaktoren: CO₂-Faktoren
        kriterium: "emissionen", "effizienz", "potential"
        
    Returns:
        Sortierter DataFrame mit Prioritäten
    """
    df = df.copy()
    
    # Kennwerte berechnen
    if "flaeche_m2" in df.columns:
        df["emissionen_kg_m2"] = (df["emissionen_gesamt_kg"] / df["flaeche_m2"])
        df["heizenergie_kwh_m2"] = (df["jahresverbrauch_kwh"] / df["flaeche_m2"])
    
    # Sortierung
    if kriterium == "emissionen":
        # Höchste absolute Emissionen zuerst
        df = df.sort_values("emissionen_gesamt_t", ascending=False)
    elif kriterium == "effizienz":
        # Schlechteste Effizienz (kg/m²) zuerst
        if "emissionen_kg_m2" in df.columns:
            df = df.sort_values("emissionen_kg_m2", ascending=False)
        else:
            df = df.sort_values("emissionen_gesamt_t", ascending=False)
    elif kriterium == "potential":
        # Größtes Sanierungspotential
        # Fossile Heizung + hohe Emissionen = hohes Potential
        df["sanierungspotential_score"] = 0
        
        # Fossil = +100 Punkte
        df.loc[df["heizung_typ"].isin(["Gas", "Öl"]), "sanierungspotential_score"] += 100
        
        # Emissionen normalisiert auf 0-100
        if len(df) > 0:
            max_em = df["emissionen_gesamt_t"].max()
            if max_em > 0:
                df["sanierungspotential_score"] += (df["emissionen_gesamt_t"] / max_em) * 100
        
        df = df.sort_values("sanierungspotential_score", ascending=False)
    
    # Rang hinzufügen
    df["prioritaet_rang"] = range(1, len(df) + 1)
    
    return df.reset_index(drop=True)


def vergleiche_gebaeude(
    df: pd.DataFrame,
    gebaeude_ids: List[str] = None
) -> pd.DataFrame:
    """
    Erstellt Vergleichstabelle für ausgewählte Gebäude.
    
    Args:
        df: DataFrame mit Gebäuden
        gebaeude_ids: Optional, spezifische Gebäude (sonst alle)
        
    Returns:
        Vergleichs-DataFrame
    """
    if gebaeude_ids:
        df = df[df["gebaeude_id"].isin(gebaeude_ids)]
    
    # Relevante Spalten
    spalten = ["gebaeude_id", "heizung_typ", "jahresverbrauch_kwh", 
               "strom_kwh_jahr", "emissionen_gesamt_t"]
    
    if "flaeche_m2" in df.columns:
        spalten.extend(["flaeche_m2", "emissionen_kg_m2", "heizenergie_kwh_m2"])
    
    if "baujahr" in df.columns:
        spalten.insert(1, "baujahr")
    
    # Nur existierende Spalten
    spalten = [s for s in spalten if s in df.columns]
    
    vergleich = df[spalten].copy()
    
    # Rundungen
    for col in vergleich.columns:
        if col not in ["gebaeude_id", "heizung_typ"] and vergleich[col].dtype in ["float64", "float32"]:
            vergleich[col] = vergleich[col].round(1)
    
    return vergleich


def erstelle_portfolio_report(
    df: pd.DataFrame,
    emissionsfaktoren: Dict
) -> str:
    """
    Erstellt Portfolio-Übersichts-Report.
    
    Args:
        df: DataFrame mit allen Gebäuden
        emissionsfaktoren: CO₂-Faktoren
        
    Returns:
        Formatierter Report
    """
    analyse = analysiere_portfolio(df, emissionsfaktoren)
    
    report = "="*60 + "\n"
    report += "PORTFOLIO-ANALYSE\n"
    report += "="*60 + "\n\n"
    
    report += f"Anzahl Gebäude: {analyse['anzahl_gebaeude']}\n"
    report += f"Gesamt-Emissionen: {analyse['gesamt_emissionen_t_jahr']:,.1f} t CO₂e/Jahr\n"
    report += f"Ø Emissionen pro Gebäude: {analyse['durchschnitt_emissionen_t_jahr']:.1f} t CO₂e/Jahr\n"
    
    if analyse["gesamt_flaeche_m2"]:
        report += f"Gesamt-Fläche: {analyse['gesamt_flaeche_m2']:,.0f} m²\n"
        report += f"Ø Emissionen: {analyse['durchschnitt_emissionen_kg_m2']:.1f} kg CO₂e/m²/Jahr\n"
    
    report += "\n" + "-"*60 + "\n"
    report += "HEIZUNGSTYPEN-VERTEILUNG:\n"
    for typ, anzahl in analyse["heizungstypen_verteilung"].items():
        prozent = (anzahl / analyse["anzahl_gebaeude"]) * 100
        report += f"  {typ}: {anzahl} Gebäude ({prozent:.0f}%)\n"
    
    report += "\n" + "-"*60 + "\n"
    report += "TOP-5 EMITTENTEN:\n"
    for i, em in enumerate(analyse["top_emittenten"], 1):
        report += f"  {i}. {em['gebaeude_id']}: {em['emissionen_gesamt_t']:.1f} t CO₂e/Jahr\n"
    
    report += "\n" + "="*60 + "\n"
    
    return report


def berechne_portfolio_szenarien(
    df: pd.DataFrame,
    emissionsfaktoren: Dict,
    szenario: str = "fossil_zu_wp"
) -> Dict:
    """
    Berechnet Portfolio-weite Sanierungsszenarien.
    
    Args:
        df: DataFrame mit Gebäuden
        emissionsfaktoren: CO₂-Faktoren
        szenario: "fossil_zu_wp", "alle_minergie", "netto_null"
        
    Returns:
        Dictionary mit Szenario-Ergebnissen
    """
    from sanierungen import berechne_heizungsersatz
    from wirtschaftlichkeit import wirtschaftlichkeitsanalyse
    
    # Aktueller Zustand
    ist_emissionen = df["emissionen_gesamt_t"].sum()
    
    massnahmen = []
    gesamt_investition = 0
    gesamt_foerderung = 0
    neue_emissionen = 0
    
    for idx, gebaeude in df.iterrows():
        if szenario == "fossil_zu_wp":
            # Nur fossile Heizungen ersetzen
            if gebaeude["heizung_typ"] in ["Gas", "Öl"]:
                san_id = "heizung_gas_zu_wp" if gebaeude["heizung_typ"] == "Gas" else "heizung_oel_zu_wp"
                san = berechne_heizungsersatz(gebaeude, san_id, emissionsfaktoren)
                san_wirtschaft = wirtschaftlichkeitsanalyse(san, gebaeude)
                
                massnahmen.append({
                    "gebaeude_id": gebaeude["gebaeude_id"],
                    "massnahme": san["name"],
                    "investition_netto_chf": san["investition_netto_chf"],
                    "co2_einsparung_kg": san["co2_einsparung_kg_jahr"],
                })
                
                gesamt_investition += san["investition_brutto_chf"]
                gesamt_foerderung += san["foerderung_chf"]
                
                # Neue Emissionen nach Sanierung
                alte_em = gebaeude["emissionen_gesamt_kg"]
                neue_em = alte_em - san["co2_einsparung_kg_jahr"]
                neue_emissionen += neue_em
            else:
                # Gebäude bleibt gleich
                neue_emissionen += gebaeude["emissionen_gesamt_kg"]
    
    neue_emissionen_t = neue_emissionen / 1000
    einsparung_t = ist_emissionen - neue_emissionen_t
    einsparung_prozent = (einsparung_t / ist_emissionen) * 100 if ist_emissionen > 0 else 0
    
    return {
        "szenario": szenario,
        "anzahl_massnahmen": len(massnahmen),
        "massnahmen": massnahmen,
        "ist_emissionen_t": ist_emissionen,
        "neue_emissionen_t": neue_emissionen_t,
        "einsparung_t_jahr": einsparung_t,
        "einsparung_prozent": einsparung_prozent,
        "gesamt_investition_brutto_chf": gesamt_investition,
        "gesamt_foerderung_chf": gesamt_foerderung,
        "gesamt_investition_netto_chf": gesamt_investition - gesamt_foerderung,
    }


def optimiere_sanierungsreihenfolge(
    df: pd.DataFrame,
    emissionsfaktoren: Dict,
    budget_pro_jahr_chf: float = None,
    jahre: int = 10
) -> Dict:
    """
    Optimiert Sanierungsreihenfolge über mehrere Jahre.
    
    Args:
        df: DataFrame mit Gebäuden
        emissionsfaktoren: CO₂-Faktoren
        budget_pro_jahr_chf: Jährliches Budget
        jahre: Planungshorizont
        
    Returns:
        Optimierungsplan
    """
    from empfehlungen import portfolio_optimierung
    
    # Gebäude in Series-Liste umwandeln
    gebaeude_liste = [row for idx, row in df.iterrows()]
    
    if budget_pro_jahr_chf is None:
        # Gesamtbudget für alle
        budget_pro_jahr_chf = float('inf')
    
    jahresplaene = []
    restliche_gebaeude = gebaeude_liste.copy()
    gesamt_emissionsreduktion = 0
    gesamt_investition = 0
    
    for jahr in range(1, jahre + 1):
        if not restliche_gebaeude:
            break
        
        # Optimierung für dieses Jahr
        df_jahr = pd.DataFrame(restliche_gebaeude)
        optimierung = portfolio_optimierung(restliche_gebaeude, budget_pro_jahr_chf, emissionsfaktoren)
        
        if optimierung["anzahl_massnahmen"] == 0:
            break
        
        # Sanierte Gebäude entfernen
        sanierte_ids = [m["gebaeude_id"] for m in optimierung["massnahmen"]]
        restliche_gebaeude = [g for g in restliche_gebaeude if g["gebaeude_id"] not in sanierte_ids]
        
        gesamt_emissionsreduktion += optimierung["gesamt_co2_reduktion_t_jahr"]
        gesamt_investition += optimierung["gesamt_investition_chf"]
        
        jahresplaene.append({
            "jahr": jahr,
            "anzahl_massnahmen": optimierung["anzahl_massnahmen"],
            "investition_chf": optimierung["gesamt_investition_chf"],
            "co2_reduktion_t": optimierung["gesamt_co2_reduktion_t_jahr"],
            "massnahmen": optimierung["massnahmen"],
        })
    
    return {
        "planungshorizont_jahre": jahre,
        "budget_pro_jahr_chf": budget_pro_jahr_chf,
        "jahresplaene": jahresplaene,
        "gesamt_emissionsreduktion_t_jahr": gesamt_emissionsreduktion,
        "gesamt_investition_chf": gesamt_investition,
        "anzahl_sanierte_gebaeude": len(gebaeude_liste) - len(restliche_gebaeude),
        "anzahl_verbleibende_gebaeude": len(restliche_gebaeude),
    }
