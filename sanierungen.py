"""
Sanierungsszenarien und Massnahmen für CO₂-Reduktion
Berechnet Kosten, Einsparungen und technische Parameter
"""

from typing import Dict, List
import pandas as pd


# Sanierungskatalog mit realistischen Schweizer Kosten
SANIERUNGSKATALOG = {
    "heizung_gas_zu_wp": {
        "name": "Heizungsersatz Gas → Wärmepumpe",
        "kategorie": "Heizung",
        "investition_chf": 50000,  # Inkl. Erschließung, Pufferspeicher
        "lebensdauer_jahre": 25,
        "neue_heizung": "Wärmepumpe",
        "energieeinsparung_prozent": 0,  # Gleiche kWh, aber besserer Faktor
        "beschreibung": "Ersatz fossile Heizung durch Luft/Wasser-Wärmepumpe",
    },
    "heizung_oel_zu_wp": {
        "name": "Heizungsersatz Öl → Wärmepumpe",
        "kategorie": "Heizung",
        "investition_chf": 50000,  # Inkl. Tankentsorgung
        "lebensdauer_jahre": 25,
        "neue_heizung": "Wärmepumpe",
        "energieeinsparung_prozent": 0,
        "beschreibung": "Ersatz Ölheizung durch Wärmepumpe, inkl. Tankrückbau",
    },
    "daemmung_fassade": {
        "name": "Fassadendämmung",
        "kategorie": "Gebäudehülle",
        "investition_chf_pro_m2": 280,  # Minergie-Qualität
        "lebensdauer_jahre": 50,
        "energieeinsparung_prozent": 25,  # Reduktion Heizenergie
        "beschreibung": "Vollständige Fassadendämmung 20cm, U-Wert < 0.20",
    },
    "daemmung_dach": {
        "name": "Dachdämmung",
        "kategorie": "Gebäudehülle",
        "investition_chf_pro_m2": 220,
        "lebensdauer_jahre": 50,
        "energieeinsparung_prozent": 15,
        "beschreibung": "Aufdachdämmung 20cm, U-Wert < 0.15",
    },
    "fenster": {
        "name": "Fensterersatz",
        "kategorie": "Gebäudehülle",
        "investition_chf_pro_m2": 850,  # 3-fach-Verglasung
        "lebensdauer_jahre": 50,
        "energieeinsparung_prozent": 12,
        "beschreibung": "3-fach-Verglasung, U-Wert < 0.8",
    },
    "solar_pv": {
        "name": "Photovoltaikanlage",
        "kategorie": "Stromerzeugung",
        "investition_chf_pro_kwp": 1800,  # 2025 Marktpreis
        "lebensdauer_jahre": 25,
        "eigenverbrauch_prozent": 30,  # Typisch ohne Batterie
        "beschreibung": "PV-Anlage auf Dach, inkl. Wechselrichter",
    },
    "solar_thermie": {
        "name": "Solarthermie Warmwasser",
        "kategorie": "Warmwasser",
        "investition_chf": 10000,  # 6m² Kollektoren
        "lebensdauer_jahre": 25,
        "warmwasser_deckung_prozent": 60,
        "beschreibung": "Solarkollektoren für Warmwasser",
    },
}

# Schweizer Förderprogramme (vereinfacht)
FOERDERGELDER = {
    "heizung_gas_zu_wp": {
        "gebaeudeprogramm_chf": 1000,  # Pauschal
        "kanton_zusatz_prozent": 20,  # Zusätzlich 20% der Investition
        "max_foerderung_chf": 25000,
    },
    "heizung_oel_zu_wp": {
        "gebaeudeprogramm_chf": 1000,  # Pauschal
        "kanton_zusatz_prozent": 20,
        "max_foerderung_chf": 30000,
    },
    "daemmung_fassade": {
        "gebaeudeprogramm_chf_pro_m2": 40,
        "max_foerderung_chf": 50000,
    },
    "daemmung_dach": {
        "gebaeudeprogramm_chf_pro_m2": 35,
        "max_foerderung_chf": 40000,
    },
    "fenster": {
        "gebaeudeprogramm_chf_pro_m2": 70,
        "max_foerderung_chf": 30000,
    },
    "solar_pv": {
        "einmalverguetung_chf_pro_kwp": 380,  # EVG 2025
        "max_foerderung_chf": 15000,
    },
}


def berechne_heizungsersatz(
    gebaeude: pd.Series,
    sanierung_id: str,
    emissionsfaktoren: Dict[str, float]
) -> Dict:
    """
    Berechnet Kosten und Einsparungen für Heizungsersatz.
    
    Args:
        gebaeude: Series mit Gebäudedaten
        sanierung_id: ID der Sanierung (z.B. "heizung_gas_zu_wp")
        emissionsfaktoren: Dict mit CO₂-Faktoren
        
    Returns:
        Dictionary mit Ergebnissen
    """
    sanierung = SANIERUNGSKATALOG[sanierung_id]
    
    # Alte Emissionen
    alter_faktor = emissionsfaktoren.get(gebaeude["heizung_typ"], 0.2)
    alte_emissionen = gebaeude["jahresverbrauch_kwh"] * alter_faktor
    
    # Neue Emissionen (Wärmepumpe nutzt Strom)
    # Annahme: COP 3.5 → 1 kWh Strom = 3.5 kWh Wärme
    cop = 3.5
    neuer_stromverbrauch = gebaeude["jahresverbrauch_kwh"] / cop
    neuer_faktor = emissionsfaktoren.get("Wärmepumpe", 0.05)
    neue_emissionen = neuer_stromverbrauch * neuer_faktor
    
    einsparung_kg = alte_emissionen - neue_emissionen
    einsparung_prozent = (einsparung_kg / alte_emissionen * 100) if alte_emissionen > 0 else 0
    
    # Kosten
    investition = sanierung["investition_chf"]
    foerderung = berechne_foerderung(sanierung_id, investition, gebaeude)
    netto_investition = investition - foerderung
    
    return {
        "sanierung_id": sanierung_id,
        "name": sanierung["name"],
        "kategorie": sanierung["kategorie"],
        "investition_brutto_chf": investition,
        "foerderung_chf": foerderung,
        "investition_netto_chf": netto_investition,
        "co2_einsparung_kg_jahr": einsparung_kg,
        "co2_einsparung_prozent": einsparung_prozent,
        "lebensdauer_jahre": sanierung["lebensdauer_jahre"],
        "neuer_verbrauch_kwh": neuer_stromverbrauch,
        "neue_heizung": sanierung["neue_heizung"],
        "beschreibung": sanierung["beschreibung"],
    }


def berechne_daemmung(
    gebaeude: pd.Series,
    sanierung_id: str,
    emissionsfaktoren: Dict[str, float]
) -> Dict:
    """
    Berechnet Kosten und Einsparungen für Dämmungsmassnahmen.
    
    Args:
        gebaeude: Series mit Gebäudedaten (muss flaeche_m2 enthalten)
        sanierung_id: ID der Sanierung
        emissionsfaktoren: Dict mit CO₂-Faktoren
        
    Returns:
        Dictionary mit Ergebnissen
    """
    sanierung = SANIERUNGSKATALOG[sanierung_id]
    
    # Flächenberechnung (vereinfacht)
    if "flaeche_m2" not in gebaeude:
        raise ValueError("Für Dämmung wird 'flaeche_m2' benötigt")
    
    if sanierung_id == "daemmung_fassade":
        # Annahme: Fassadenfläche ≈ 2.5 × Grundfläche (bei 3-4 Geschossen)
        flaeche = gebaeude["flaeche_m2"] * 2.5
    elif sanierung_id == "daemmung_dach":
        # Dachfläche ≈ Grundfläche × 1.2 (Dachneigung)
        flaeche = gebaeude["flaeche_m2"] * 1.2
    else:
        flaeche = gebaeude["flaeche_m2"]
    
    # Kosten
    investition = sanierung["investition_chf_pro_m2"] * flaeche
    foerderung = berechne_foerderung(sanierung_id, investition, gebaeude, flaeche)
    netto_investition = investition - foerderung
    
    # Energieeinsparung
    energieeinsparung_kwh = gebaeude["jahresverbrauch_kwh"] * (sanierung["energieeinsparung_prozent"] / 100)
    
    # CO₂-Einsparung
    faktor = emissionsfaktoren.get(gebaeude["heizung_typ"], 0.2)
    co2_einsparung = energieeinsparung_kwh * faktor
    
    return {
        "sanierung_id": sanierung_id,
        "name": sanierung["name"],
        "kategorie": sanierung["kategorie"],
        "flaeche_m2": flaeche,
        "investition_brutto_chf": investition,
        "foerderung_chf": foerderung,
        "investition_netto_chf": netto_investition,
        "energieeinsparung_kwh_jahr": energieeinsparung_kwh,
        "co2_einsparung_kg_jahr": co2_einsparung,
        "co2_einsparung_prozent": sanierung["energieeinsparung_prozent"],
        "lebensdauer_jahre": sanierung["lebensdauer_jahre"],
        "beschreibung": sanierung["beschreibung"],
    }


def berechne_solar_pv(
    gebaeude: pd.Series,
    kwp: float = None,
    emissionsfaktoren: Dict[str, float] = None
) -> Dict:
    """
    Berechnet Kosten und Einsparungen für PV-Anlage.
    
    Args:
        gebaeude: Series mit Gebäudedaten
        kwp: Installierte Leistung in kWp (wenn None: auto aus Fläche)
        emissionsfaktoren: Dict mit CO₂-Faktoren
        
    Returns:
        Dictionary mit Ergebnissen
    """
    sanierung = SANIERUNGSKATALOG["solar_pv"]
    
    # Leistung bestimmen
    if kwp is None:
        # Annahme: 6 kWp pro 100m² Dachfläche
        if "flaeche_m2" not in gebaeude:
            kwp = 10  # Default
        else:
            kwp = (gebaeude["flaeche_m2"] * 1.2) / 100 * 6
    
    # Jahresertrag (Schweiz: ~1000 kWh/kWp)
    jahresertrag_kwh = kwp * 1000
    
    # Eigenverbrauch
    eigenverbrauch_kwh = jahresertrag_kwh * (sanierung["eigenverbrauch_prozent"] / 100)
    
    # CO₂-Einsparung (nur Eigenverbrauch relevant)
    strom_faktor = emissionsfaktoren.get("Strom", 0.122) if emissionsfaktoren else 0.122
    co2_einsparung = eigenverbrauch_kwh * strom_faktor
    
    # Kosten
    investition = sanierung["investition_chf_pro_kwp"] * kwp
    foerderung = berechne_foerderung("solar_pv", investition, gebaeude, kwp=kwp)
    netto_investition = investition - foerderung
    
    return {
        "sanierung_id": "solar_pv",
        "name": sanierung["name"],
        "kategorie": sanierung["kategorie"],
        "leistung_kwp": kwp,
        "jahresertrag_kwh": jahresertrag_kwh,
        "eigenverbrauch_kwh": eigenverbrauch_kwh,
        "investition_brutto_chf": investition,
        "foerderung_chf": foerderung,
        "investition_netto_chf": netto_investition,
        "co2_einsparung_kg_jahr": co2_einsparung,
        "lebensdauer_jahre": sanierung["lebensdauer_jahre"],
        "beschreibung": sanierung["beschreibung"],
    }


def berechne_foerderung(
    sanierung_id: str,
    investition: float,
    gebaeude: pd.Series,
    flaeche: float = None,
    kwp: float = None
) -> float:
    """
    Berechnet verfügbare Fördergelder für Sanierung.
    
    Args:
        sanierung_id: ID der Sanierung
        investition: Brutto-Investition
        gebaeude: Gebäudedaten
        flaeche: Fläche (für Dämmung)
        kwp: Leistung (für Solar)
        
    Returns:
        Fördersumme in CHF
    """
    if sanierung_id not in FOERDERGELDER:
        return 0
    
    foerderung_config = FOERDERGELDER[sanierung_id]
    foerderung = 0
    
    # Gebäudeprogramm Pauschal
    if "gebaeudeprogramm_chf" in foerderung_config:
        foerderung += foerderung_config["gebaeudeprogramm_chf"]
    
    # Gebäudeprogramm pro m²
    if "gebaeudeprogramm_chf_pro_m2" in foerderung_config and flaeche:
        foerderung += foerderung_config["gebaeudeprogramm_chf_pro_m2"] * flaeche
    
    # Einmalvergütung PV
    if "einmalverguetung_chf_pro_kwp" in foerderung_config and kwp:
        foerderung += foerderung_config["einmalverguetung_chf_pro_kwp"] * kwp
    
    # Kantonaler Zusatz (prozentual)
    if "kanton_zusatz_prozent" in foerderung_config:
        kanton_zusatz = investition * (foerderung_config["kanton_zusatz_prozent"] / 100)
        foerderung += kanton_zusatz
    
    # Maximale Förderung begrenzen
    max_foerderung = foerderung_config.get("max_foerderung_chf", float('inf'))
    foerderung = min(foerderung, max_foerderung)
    
    # Nicht mehr als Investition
    foerderung = min(foerderung, investition)
    
    return foerderung


def erstelle_alle_szenarien(
    gebaeude: pd.Series,
    emissionsfaktoren: Dict[str, float]
) -> List[Dict]:
    """
    Erstellt alle möglichen Sanierungsszenarien für ein Gebäude.
    
    Args:
        gebaeude: Series mit Gebäudedaten
        emissionsfaktoren: Dict mit CO₂-Faktoren
        
    Returns:
        Liste mit allen Szenarien
    """
    szenarien = []
    
    # Heizungsersatz (wenn fossil)
    if gebaeude["heizung_typ"] == "Gas":
        szenarien.append(berechne_heizungsersatz(gebaeude, "heizung_gas_zu_wp", emissionsfaktoren))
    elif gebaeude["heizung_typ"] == "Öl":
        szenarien.append(berechne_heizungsersatz(gebaeude, "heizung_oel_zu_wp", emissionsfaktoren))
    
    # Dämmungen (wenn Fläche vorhanden)
    if "flaeche_m2" in gebaeude and gebaeude["flaeche_m2"] > 0:
        szenarien.append(berechne_daemmung(gebaeude, "daemmung_fassade", emissionsfaktoren))
        szenarien.append(berechne_daemmung(gebaeude, "daemmung_dach", emissionsfaktoren))
        szenarien.append(berechne_daemmung(gebaeude, "fenster", emissionsfaktoren))
    
    # Solar PV
    szenarien.append(berechne_solar_pv(gebaeude, emissionsfaktoren=emissionsfaktoren))
    
    return szenarien


def erstelle_kombinationsszenarien(
    gebaeude: pd.Series,
    emissionsfaktoren: Dict[str, float]
) -> List[Dict]:
    """
    Erstellt sinnvolle Kombinationen von Sanierungsmassnahmen.
    
    Args:
        gebaeude: Series mit Gebäudedaten
        emissionsfaktoren: Dict mit CO₂-Faktoren
        
    Returns:
        Liste mit Kombinations-Szenarien
    """
    kombinationen = []
    
    # Kombination 1: Heizung + Solar
    if gebaeude["heizung_typ"] in ["Gas", "Öl"]:
        kombi_name = "Kombi: Wärmepumpe + PV"
        heizung_id = "heizung_gas_zu_wp" if gebaeude["heizung_typ"] == "Gas" else "heizung_oel_zu_wp"
        
        heizung = berechne_heizungsersatz(gebaeude, heizung_id, emissionsfaktoren)
        solar = berechne_solar_pv(gebaeude, emissionsfaktoren=emissionsfaktoren)
        
        kombinationen.append({
            "sanierung_id": "kombi_heizung_solar",
            "name": kombi_name,
            "kategorie": "Kombination",
            "investition_brutto_chf": heizung["investition_brutto_chf"] + solar["investition_brutto_chf"],
            "foerderung_chf": heizung["foerderung_chf"] + solar["foerderung_chf"],
            "investition_netto_chf": heizung["investition_netto_chf"] + solar["investition_netto_chf"],
            "co2_einsparung_kg_jahr": heizung["co2_einsparung_kg_jahr"] + solar["co2_einsparung_kg_jahr"],
            "lebensdauer_jahre": 20,  # Durchschnitt
            "beschreibung": f"{heizung['name']} + {solar['name']}",
            "massnahmen": [heizung, solar],
        })
    
    # Kombination 2: Vollsanierung (wenn Fläche vorhanden)
    if "flaeche_m2" in gebaeude and gebaeude["flaeche_m2"] > 0:
        if gebaeude["heizung_typ"] in ["Gas", "Öl"]:
            heizung_id = "heizung_gas_zu_wp" if gebaeude["heizung_typ"] == "Gas" else "heizung_oel_zu_wp"
            heizung = berechne_heizungsersatz(gebaeude, heizung_id, emissionsfaktoren)
            fassade = berechne_daemmung(gebaeude, "daemmung_fassade", emissionsfaktoren)
            dach = berechne_daemmung(gebaeude, "daemmung_dach", emissionsfaktoren)
            solar = berechne_solar_pv(gebaeude, emissionsfaktoren=emissionsfaktoren)
            
            kombinationen.append({
                "sanierung_id": "kombi_vollsanierung",
                "name": "Kombi: Vollsanierung Minergie",
                "kategorie": "Kombination",
                "investition_brutto_chf": sum([m["investition_brutto_chf"] for m in [heizung, fassade, dach, solar]]),
                "foerderung_chf": sum([m["foerderung_chf"] for m in [heizung, fassade, dach, solar]]),
                "investition_netto_chf": sum([m["investition_netto_chf"] for m in [heizung, fassade, dach, solar]]),
                "co2_einsparung_kg_jahr": sum([m["co2_einsparung_kg_jahr"] for m in [heizung, fassade, dach, solar]]),
                "lebensdauer_jahre": 30,
                "beschreibung": "Komplette energetische Sanierung: Wärmepumpe + Dämmung + PV",
                "massnahmen": [heizung, fassade, dach, solar],
            })
    
    return kombinationen
