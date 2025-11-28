"""
Tests für Emissionsberechnungen
"""

import pytest
import pandas as pd
import sys
from pathlib import Path

# Pfad zu src hinzufügen
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from emissionen import (
    berechne_emissionen,
    validiere_eingabedaten,
    KBOB_FAKTOREN
)


def test_validierung_erfolg():
    """Test: Korrekte Daten sollten validieren."""
    df = pd.DataFrame({
        "gebaeude_id": ["A"],
        "jahr": [2024],
        "heizung_typ": ["Gas"],
        "jahresverbrauch_kwh": [10000],
        "strom_kwh_jahr": [5000]
    })
    
    fehler = validiere_eingabedaten(df)
    assert len(fehler) == 0


def test_validierung_fehlende_spalten():
    """Test: Fehlende Spalten sollten erkannt werden."""
    df = pd.DataFrame({
        "gebaeude_id": ["A"],
        "jahr": [2024]
    })
    
    fehler = validiere_eingabedaten(df)
    assert len(fehler) > 0
    assert any("Fehlende Spalten" in f for f in fehler)


def test_validierung_negative_werte():
    """Test: Negative Werte sollten erkannt werden."""
    df = pd.DataFrame({
        "gebaeude_id": ["A"],
        "jahr": [2024],
        "heizung_typ": ["Gas"],
        "jahresverbrauch_kwh": [-10000],  # Negativ!
        "strom_kwh_jahr": [5000]
    })
    
    fehler = validiere_eingabedaten(df)
    assert any("Negative" in f for f in fehler)


def test_emissionsberechnung_gas():
    """Test: Emissionen für Gas korrekt berechnen."""
    df = pd.DataFrame({
        "gebaeude_id": ["A"],
        "jahr": [2024],
        "heizung_typ": ["Gas"],
        "jahresverbrauch_kwh": [10000],
        "strom_kwh_jahr": [5000]
    })
    
    result = berechne_emissionen(df)
    
    # Erwartete Emissionen (Gas)
    faktor_gas = KBOB_FAKTOREN["Gas"]
    expected_heizen = 10000 * faktor_gas
    
    # Stromfaktor (Default)
    faktor_strom = 0.122
    expected_strom = 5000 * faktor_strom
    
    expected_gesamt = expected_heizen + expected_strom
    
    assert abs(result.iloc[0]["emissionen_heizen_kg"] - expected_heizen) < 0.1
    assert abs(result.iloc[0]["emissionen_strom_kg"] - expected_strom) < 0.1
    assert abs(result.iloc[0]["emissionen_gesamt_kg"] - expected_gesamt) < 0.1


def test_emissionsberechnung_mehrere_gebaeude():
    """Test: Mehrere Gebäude korrekt verarbeiten."""
    df = pd.DataFrame({
        "gebaeude_id": ["A", "B"],
        "jahr": [2024, 2024],
        "heizung_typ": ["Gas", "Öl"],
        "jahresverbrauch_kwh": [10000, 15000],
        "strom_kwh_jahr": [5000, 6000]
    })
    
    result = berechne_emissionen(df)
    
    assert len(result) == 2
    assert "emissionen_gesamt_kg" in result.columns
    assert all(result["emissionen_gesamt_kg"] > 0)


def test_unbekannter_heizungstyp():
    """Test: Unbekannter Heizungstyp sollte Fallback-Faktor nutzen."""
    df = pd.DataFrame({
        "gebaeude_id": ["A"],
        "jahr": [2024],
        "heizung_typ": ["Unbekannt"],
        "jahresverbrauch_kwh": [10000],
        "strom_kwh_jahr": [5000]
    })
    
    result = berechne_emissionen(df)
    
    # Sollte Default-Faktor verwenden
    expected = 10000 * KBOB_FAKTOREN["Default"]
    assert abs(result.iloc[0]["emissionen_heizen_kg"] - expected) < 0.1


def test_emissionen_in_tonnen():
    """Test: Umrechnung in Tonnen korrekt."""
    df = pd.DataFrame({
        "gebaeude_id": ["A"],
        "jahr": [2024],
        "heizung_typ": ["Gas"],
        "jahresverbrauch_kwh": [10000],
        "strom_kwh_jahr": [5000]
    })
    
    result = berechne_emissionen(df)
    
    kg = result.iloc[0]["emissionen_gesamt_kg"]
    t = result.iloc[0]["emissionen_gesamt_t"]
    
    assert abs(kg / 1000 - t) < 0.001


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
