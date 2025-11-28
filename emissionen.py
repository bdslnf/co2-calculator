"""
Emissionsberechnungen für Gebäude nach KBOB-Methodik
HSLU Digital Twin Programming - CO₂ Neutrality Path Calculator
"""

from typing import Dict
import pandas as pd


# KBOB 2022/1:2022 Emissionsfaktoren (kg CO₂e/kWh) inkl. Vorkette
KBOB_FAKTOREN = {
    "Gas": 0.228,           # Erdgas
    "Öl": 0.302,            # Heizöl EL
    "Fernwärme": 0.095,     # Mix CH (variiert stark je nach Quelle)
    "Wärmepumpe": 0.050,    # Abhängig vom Strommix
    "Pellets": 0.026,       # Holzpellets
    "Solar": 0.000,         # Solarthermie
    "Default": 0.050,       # Fallback: CH-Strommix
}

# Stromfaktor CH-Verbrauchermix (KBOB)
STROM_FAKTOR_CH = 0.122  # kg CO₂e/kWh


def validiere_eingabedaten(df: pd.DataFrame) -> list:
    """
    Validiert Eingabedaten auf Plausibilität und Vollständigkeit.
    
    Args:
        df: DataFrame mit Gebäudedaten
        
    Returns:
        Liste mit Fehlermeldungen (leer wenn alles OK)
    """
    fehler = []
    
    # Erforderliche Spalten
    required_cols = ["gebaeude_id", "jahr", "heizung_typ", 
                     "jahresverbrauch_kwh", "strom_kwh_jahr"]
    
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        fehler.append(f"Fehlende Spalten: {', '.join(missing)}")
        return fehler  # Stoppe weitere Validierung
    
    # Negative Werte
    if (df["jahresverbrauch_kwh"] < 0).any():
        fehler.append("Negative Werte in 'jahresverbrauch_kwh' gefunden")
    
    if (df["strom_kwh_jahr"] < 0).any():
        fehler.append("Negative Werte in 'strom_kwh_jahr' gefunden")
    
    # Unrealistisch hohe Werte (>500'000 kWh/Jahr für Heizung)
    if (df["jahresverbrauch_kwh"] > 500000).any():
        anzahl = (df["jahresverbrauch_kwh"] > 500000).sum()
        fehler.append(f"Warnung: {anzahl} Gebäude mit sehr hohem Heizenergieverbrauch (>500 MWh/a)")
    
    # Unbekannte Heizungstypen
    unbekannte = set(df["heizung_typ"].unique()) - set(KBOB_FAKTOREN.keys())
    if unbekannte:
        fehler.append(f"Unbekannte Heizungstypen: {', '.join(unbekannte)} "
                     f"→ Verwende Fallback-Faktor {KBOB_FAKTOREN['Default']}")
    
    return fehler


def berechne_emissionen(
    df: pd.DataFrame,
    faktor_strom: float = STROM_FAKTOR_CH,
    custom_heiz_faktoren: Dict[str, float] = None
) -> pd.DataFrame:
    """
    Berechnet CO₂-Emissionen für alle Gebäude und Jahre.
    
    Args:
        df: DataFrame mit Spalten gebaeude_id, jahr, heizung_typ, 
            jahresverbrauch_kwh, strom_kwh_jahr
        faktor_strom: Emissionsfaktor für Strom (Standard: CH-Mix)
        custom_heiz_faktoren: Optional eigene Heizungs-Emissionsfaktoren
        
    Returns:
        DataFrame mit zusätzlichen Spalten:
        - emissionen_heizen_kg: CO₂ aus Heizenergie
        - emissionen_strom_kg: CO₂ aus Stromverbrauch
        - emissionen_gesamt_kg: Gesamt-CO₂
        - emissionen_gesamt_t: Gesamt-CO₂ in Tonnen
    """
    df = df.copy()
    
    # Heizungsfaktoren bestimmen
    heiz_faktoren = custom_heiz_faktoren or KBOB_FAKTOREN
    
    # Faktor für jede Zeile mappen (mit Fallback für unbekannte Typen)
    df["faktor_heizen"] = df["heizung_typ"].map(heiz_faktoren).fillna(heiz_faktoren["Default"])
    
    # Emissionen berechnen
    df["emissionen_heizen_kg"] = df["jahresverbrauch_kwh"] * df["faktor_heizen"]
    df["emissionen_strom_kg"] = df["strom_kwh_jahr"] * faktor_strom
    df["emissionen_gesamt_kg"] = df["emissionen_heizen_kg"] + df["emissionen_strom_kg"]
    
    # In Tonnen umrechnen (üblicher für Gebäude)
    df["emissionen_gesamt_t"] = df["emissionen_gesamt_kg"] / 1000
    
    return df


def aggregiere_jaehrlich(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregiert Emissionen pro Gebäude und Jahr.
    
    Args:
        df: DataFrame mit berechneten Emissionen
        
    Returns:
        DataFrame mit Spalten: gebaeude_id, jahr, emissionen_gesamt_kg, emissionen_gesamt_t
    """
    yearly = df.groupby(["gebaeude_id", "jahr"], as_index=False).agg({
        "emissionen_gesamt_kg": "sum",
        "emissionen_gesamt_t": "sum"
    })
    
    return yearly.sort_values(["gebaeude_id", "jahr"])


def berechne_kumulierte_emissionen(df: pd.DataFrame) -> pd.DataFrame:
    """
    Berechnet kumulierte Emissionen über Zeit für jedes Gebäude.
    
    Args:
        df: DataFrame mit aggregierten Jahreswerten
        
    Returns:
        DataFrame mit zusätzlichen Spalten:
        - emissionen_kumuliert_kg
        - emissionen_kumuliert_t
    """
    df = df.copy()
    
    df["emissionen_kumuliert_kg"] = (
        df.groupby("gebaeude_id")["emissionen_gesamt_kg"].cumsum()
    )
    
    df["emissionen_kumuliert_t"] = df["emissionen_kumuliert_kg"] / 1000
    
    return df
