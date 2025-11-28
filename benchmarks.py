"""
Benchmark-System für Gebäude-Performance
Vergleicht mit Minergie, SIA-Standards, CH-Durchschnitt
"""

from typing import Dict
import pandas as pd


# Benchmark-Werte nach SIA 380/1 und Minergie (kWh/m²/Jahr)
BENCHMARKS_HEIZENERGIE = {
    "Neubau_SIA_2024": {
        "beschreibung": "SIA 380/1:2024 Grenzwert Neubau",
        "heizwaermebedarf_kwh_m2": 30,
        "gesamtenergie_kwh_m2": 45,
    },
    "Minergie": {
        "beschreibung": "Minergie-Standard",
        "heizwaermebedarf_kwh_m2": 38,
        "gesamtenergie_kwh_m2": 55,
    },
    "Minergie_P": {
        "beschreibung": "Minergie-P (Passivhaus)",
        "heizwaermebedarf_kwh_m2": 15,
        "gesamtenergie_kwh_m2": 30,
    },
    "MuKEn_2014": {
        "beschreibung": "MuKEn 2014 (Mustervorschriften)",
        "heizwaermebedarf_kwh_m2": 35,
        "gesamtenergie_kwh_m2": 50,
    },
}

# CH-Durchschnitt nach Baujahr (vereinfacht)
BENCHMARKS_BAUJAHR = {
    "vor_1920": {"heizwaermebedarf_kwh_m2": 180, "beschreibung": "Altbau unsaniert"},
    "1920_1945": {"heizwaermebedarf_kwh_m2": 160, "beschreibung": "Altbau"},
    "1946_1975": {"heizwaermebedarf_kwh_m2": 140, "beschreibung": "Nachkriegsbau"},
    "1976_1990": {"heizwaermebedarf_kwh_m2": 120, "beschreibung": "70er/80er Jahre"},
    "1991_2000": {"heizwaermebedarf_kwh_m2": 100, "beschreibung": "90er Jahre"},
    "2001_2010": {"heizwaermebedarf_kwh_m2": 70, "beschreibung": "2000er Jahre"},
    "2011_2020": {"heizwaermebedarf_kwh_m2": 50, "beschreibung": "2010er Jahre"},
    "ab_2021": {"heizwaermebedarf_kwh_m2": 35, "beschreibung": "Neubau aktuell"},
}

# CO₂-Ziele Schweiz
CO2_ZIELE = {
    "heute_2025": {"kg_co2_m2_jahr": 25, "beschreibung": "Aktueller CH-Durchschnitt"},
    "klimaziel_2030": {"kg_co2_m2_jahr": 12, "beschreibung": "Klimaziel 2030"},
    "klimaziel_2040": {"kg_co2_m2_jahr": 6, "beschreibung": "Klimaziel 2040"},
    "netto_null_2050": {"kg_co2_m2_jahr": 0, "beschreibung": "Netto-Null 2050"},
}


def berechne_kennwerte_pro_m2(
    gebaeude: pd.Series,
    emissionen_kg: float
) -> Dict:
    """
    Berechnet Kennwerte pro m² für Vergleichbarkeit.
    
    Args:
        gebaeude: Gebäudedaten
        emissionen_kg: Jährliche CO₂-Emissionen in kg
        
    Returns:
        Dictionary mit spezifischen Kennwerten
    """
    if "flaeche_m2" not in gebaeude or gebaeude["flaeche_m2"] <= 0:
        return {
            "heizenergie_kwh_m2": None,
            "strom_kwh_m2": None,
            "co2_kg_m2": None,
        }
    
    flaeche = gebaeude["flaeche_m2"]
    
    return {
        "heizenergie_kwh_m2": gebaeude["jahresverbrauch_kwh"] / flaeche,
        "strom_kwh_m2": gebaeude.get("strom_kwh_jahr", 0) / flaeche,
        "co2_kg_m2": emissionen_kg / flaeche,
    }


def bestimme_energieeffizienz_klasse(
    heizenergie_kwh_m2: float
) -> str:
    """
    Bestimmt Energieeffizienzklasse analog EU-Label.
    
    Args:
        heizenergie_kwh_m2: Heizenergiebedarf pro m²
        
    Returns:
        Klasse A-G
    """
    if heizenergie_kwh_m2 < 30:
        return "A"  # Sehr effizient (Minergie-P Niveau)
    elif heizenergie_kwh_m2 < 50:
        return "B"  # Effizient (Minergie Niveau)
    elif heizenergie_kwh_m2 < 80:
        return "C"  # Gut (Neubau-Standard)
    elif heizenergie_kwh_m2 < 120:
        return "D"  # Durchschnitt (sanierter Altbau)
    elif heizenergie_kwh_m2 < 160:
        return "E"  # Unterdurchschnitt
    elif heizenergie_kwh_m2 < 200:
        return "F"  # Schlecht (unsanierter Altbau)
    else:
        return "G"  # Sehr schlecht


def vergleiche_mit_standards(
    gebaeude: pd.Series,
    emissionen_kg: float
) -> pd.DataFrame:
    """
    Vergleicht Gebäude mit verschiedenen Standards.
    
    Args:
        gebaeude: Gebäudedaten
        emissionen_kg: Jährliche CO₂-Emissionen
        
    Returns:
        DataFrame mit Vergleichen
    """
    kennwerte = berechne_kennwerte_pro_m2(gebaeude, emissionen_kg)
    
    if kennwerte["heizenergie_kwh_m2"] is None:
        return pd.DataFrame()
    
    ist_wert = kennwerte["heizenergie_kwh_m2"]
    
    vergleiche = []
    
    # Standards
    for standard, daten in BENCHMARKS_HEIZENERGIE.items():
        soll_wert = daten["heizwaermebedarf_kwh_m2"]
        differenz = ist_wert - soll_wert
        differenz_prozent = (differenz / soll_wert) * 100 if soll_wert > 0 else 0
        
        status = "✓ Erreicht" if differenz <= 0 else "✗ Nicht erreicht"
        
        vergleiche.append({
            "standard": standard,
            "beschreibung": daten["beschreibung"],
            "soll_kwh_m2": soll_wert,
            "ist_kwh_m2": ist_wert,
            "differenz_kwh_m2": differenz,
            "differenz_prozent": differenz_prozent,
            "status": status,
        })
    
    # Baujahr-Benchmark (wenn vorhanden)
    if "baujahr" in gebaeude:
        baujahr_kategorie = bestimme_baujahr_kategorie(gebaeude["baujahr"])
        if baujahr_kategorie in BENCHMARKS_BAUJAHR:
            benchmark = BENCHMARKS_BAUJAHR[baujahr_kategorie]
            soll_wert = benchmark["heizwaermebedarf_kwh_m2"]
            differenz = ist_wert - soll_wert
            differenz_prozent = (differenz / soll_wert) * 100 if soll_wert > 0 else 0
            
            status = "✓ Besser" if differenz < 0 else "≈ Durchschnitt" if abs(differenz) < 20 else "✗ Schlechter"
            
            vergleiche.append({
                "standard": f"Durchschnitt_{baujahr_kategorie}",
                "beschreibung": f"CH-Durchschnitt {benchmark['beschreibung']}",
                "soll_kwh_m2": soll_wert,
                "ist_kwh_m2": ist_wert,
                "differenz_kwh_m2": differenz,
                "differenz_prozent": differenz_prozent,
                "status": status,
            })
    
    df = pd.DataFrame(vergleiche)
    return df


def bestimme_baujahr_kategorie(baujahr: int) -> str:
    """Bestimmt Baujahr-Kategorie."""
    if baujahr < 1920:
        return "vor_1920"
    elif baujahr <= 1945:
        return "1920_1945"
    elif baujahr <= 1975:
        return "1946_1975"
    elif baujahr <= 1990:
        return "1976_1990"
    elif baujahr <= 2000:
        return "1991_2000"
    elif baujahr <= 2010:
        return "2001_2010"
    elif baujahr <= 2020:
        return "2011_2020"
    else:
        return "ab_2021"


def vergleiche_mit_klimazielen(
    gebaeude: pd.Series,
    emissionen_kg: float
) -> pd.DataFrame:
    """
    Vergleicht mit Schweizer Klimazielen.
    
    Args:
        gebaeude: Gebäudedaten
        emissionen_kg: Jährliche CO₂-Emissionen
        
    Returns:
        DataFrame mit Ziel-Vergleichen
    """
    kennwerte = berechne_kennwerte_pro_m2(gebaeude, emissionen_kg)
    
    if kennwerte["co2_kg_m2"] is None:
        return pd.DataFrame()
    
    ist_wert = kennwerte["co2_kg_m2"]
    
    vergleiche = []
    
    for ziel, daten in CO2_ZIELE.items():
        soll_wert = daten["kg_co2_m2_jahr"]
        differenz = ist_wert - soll_wert
        differenz_prozent = (differenz / soll_wert) * 100 if soll_wert > 0 else 0
        
        status = "✓ Erreicht" if differenz <= 0 else "✗ Nicht erreicht"
        
        vergleiche.append({
            "klimaziel": ziel,
            "beschreibung": daten["beschreibung"],
            "soll_kg_co2_m2": soll_wert,
            "ist_kg_co2_m2": ist_wert,
            "differenz_kg_co2_m2": differenz,
            "differenz_prozent": differenz_prozent,
            "status": status,
        })
    
    return pd.DataFrame(vergleiche)


def erstelle_benchmark_report(
    gebaeude: pd.Series,
    emissionen_kg: float
) -> str:
    """
    Erstellt vollständigen Benchmark-Report.
    
    Args:
        gebaeude: Gebäudedaten
        emissionen_kg: Jährliche Emissionen
        
    Returns:
        Formatierter Report-Text
    """
    report = "="*60 + "\n"
    report += "BENCHMARK-ANALYSE\n"
    report += "="*60 + "\n\n"
    
    # Kennwerte
    kennwerte = berechne_kennwerte_pro_m2(gebaeude, emissionen_kg)
    
    if kennwerte["heizenergie_kwh_m2"] is None:
        report += "⚠ Keine Flächenangabe - Benchmark-Vergleich nicht möglich\n"
        return report
    
    report += f"GEBÄUDE: {gebaeude.get('gebaeude_id', 'N/A')}\n"
    if "baujahr" in gebaeude:
        report += f"Baujahr: {gebaeude['baujahr']}\n"
    if "flaeche_m2" in gebaeude:
        report += f"Fläche: {gebaeude['flaeche_m2']:,.0f} m²\n"
    report += f"Heizung: {gebaeude.get('heizung_typ', 'N/A')}\n\n"
    
    report += "KENNWERTE:\n"
    report += f"  Heizenergie: {kennwerte['heizenergie_kwh_m2']:.1f} kWh/m²/Jahr\n"
    report += f"  Strom: {kennwerte['strom_kwh_m2']:.1f} kWh/m²/Jahr\n"
    report += f"  CO₂: {kennwerte['co2_kg_m2']:.1f} kg CO₂/m²/Jahr\n\n"
    
    # Effizienzklasse
    klasse = bestimme_energieeffizienz_klasse(kennwerte["heizenergie_kwh_m2"])
    report += f"ENERGIEEFFIZIENZKLASSE: {klasse}\n"
    report += "(A = sehr effizient, G = sehr ineffizient)\n\n"
    
    # Standards-Vergleich
    report += "VERGLEICH MIT STANDARDS:\n"
    report += "-"*60 + "\n"
    
    standards_df = vergleiche_mit_standards(gebaeude, emissionen_kg)
    for idx, row in standards_df.iterrows():
        report += f"\n{row['standard']}: {row['beschreibung']}\n"
        report += f"  Soll: {row['soll_kwh_m2']:.0f} kWh/m²  |  Ist: {row['ist_kwh_m2']:.1f} kWh/m²\n"
        report += f"  Differenz: {row['differenz_kwh_m2']:.1f} kWh/m² ({row['differenz_prozent']:.0f}%)\n"
        report += f"  {row['status']}\n"
    
    # Klimaziele
    report += "\n" + "="*60 + "\n"
    report += "VERGLEICH MIT KLIMAZIELEN:\n"
    report += "-"*60 + "\n"
    
    ziele_df = vergleiche_mit_klimazielen(gebaeude, emissionen_kg)
    for idx, row in ziele_df.iterrows():
        report += f"\n{row['beschreibung']}:\n"
        report += f"  Ziel: {row['soll_kg_co2_m2']:.1f} kg CO₂/m²  |  Ist: {row['ist_kg_co2_m2']:.1f} kg CO₂/m²\n"
        report += f"  Differenz: {row['differenz_kg_co2_m2']:.1f} kg CO₂/m² ({row['differenz_prozent']:.0f}%)\n"
        report += f"  {row['status']}\n"
    
    report += "\n" + "="*60 + "\n"
    
    return report


def berechne_sanierungspotential(
    gebaeude: pd.Series,
    emissionen_kg_aktuell: float,
    ziel_standard: str = "Minergie"
) -> Dict:
    """
    Berechnet Sanierungspotential bis Ziel-Standard.
    
    Args:
        gebaeude: Gebäudedaten
        emissionen_kg_aktuell: Aktuelle Emissionen
        ziel_standard: Zielstandard (z.B. "Minergie", "Neubau_SIA_2024")
        
    Returns:
        Dictionary mit Potential-Analyse
    """
    kennwerte = berechne_kennwerte_pro_m2(gebaeude, emissionen_kg_aktuell)
    
    if kennwerte["heizenergie_kwh_m2"] is None:
        return {}
    
    ist_kwh_m2 = kennwerte["heizenergie_kwh_m2"]
    
    if ziel_standard not in BENCHMARKS_HEIZENERGIE:
        ziel_standard = "Minergie"
    
    ziel_kwh_m2 = BENCHMARKS_HEIZENERGIE[ziel_standard]["heizwaermebedarf_kwh_m2"]
    
    if ist_kwh_m2 <= ziel_kwh_m2:
        return {
            "status": "Ziel bereits erreicht",
            "einsparungspotential_kwh_m2": 0,
            "einsparungspotential_prozent": 0,
        }
    
    einsparung_kwh_m2 = ist_kwh_m2 - ziel_kwh_m2
    einsparung_prozent = (einsparung_kwh_m2 / ist_kwh_m2) * 100
    
    # Hochrechnung auf Gebäude
    flaeche = gebaeude.get("flaeche_m2", 0)
    einsparung_gesamt_kwh = einsparung_kwh_m2 * flaeche
    
    # CO₂-Potential (vereinfacht)
    from emissionen import KBOB_FAKTOREN
    faktor = KBOB_FAKTOREN.get(gebaeude.get("heizung_typ", "Gas"), 0.2)
    co2_einsparung_kg = einsparung_gesamt_kwh * faktor
    
    return {
        "ziel_standard": ziel_standard,
        "ist_kwh_m2": ist_kwh_m2,
        "ziel_kwh_m2": ziel_kwh_m2,
        "einsparungspotential_kwh_m2": einsparung_kwh_m2,
        "einsparungspotential_prozent": einsparung_prozent,
        "einsparungspotential_gesamt_kwh": einsparung_gesamt_kwh,
        "co2_einsparungspotential_kg": co2_einsparung_kg,
        "co2_einsparungspotential_t": co2_einsparung_kg / 1000,
    }
