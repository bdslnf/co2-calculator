"""
CO2 Neutrality Path Calculator - Streamlit Web App
Interactive Dashboard fuer Gebaeude-Analyse und Sanierungsplanung
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys
import re

# Pfad fuer Datenzugriff
ROOT = Path(__file__).resolve().parent

from emissionen import (
    validiere_eingabedaten,
    berechne_emissionen,
    aggregiere_jaehrlich,
    KBOB_FAKTOREN
)
from sanierungen import erstelle_alle_szenarien, erstelle_kombinationsszenarien
from wirtschaftlichkeit import wirtschaftlichkeitsanalyse, sensitivitaetsanalyse
from empfehlungen import priorisiere_sanierungen, generiere_empfehlung
from benchmarks import vergleiche_mit_standards, vergleiche_mit_klimazielen
from portfolio import analysiere_portfolio, priorisiere_gebaeude_fuer_sanierung


# Page Config
st.set_page_config(
    page_title="CO2 Calculator",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #2E7D32;
        text-align: center;
        padding: 1rem 0;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #2E7D32;
    }
</style>
""", unsafe_allow_html=True)


def format_number_swiss(value):
    """Formatiert Zahlen im Schweizer Format mit Apostrophen."""
    if value == 0:
        return "0"
    return f"{int(value):,}".replace(",", "'")


def parse_swiss_number(text):
    """Konvertiert Schweizer Format (mit Apostrophen) zurueck zu Zahl."""
    if not text:
        return 0
    # Entferne alle Apostrophe und Leerzeichen
    cleaned = text.replace("'", "").replace(" ", "").replace(",", "")
    try:
        return int(cleaned)
    except:
        return 0


def lade_daten():
    """Laedt Daten aus CSV oder nutzt Demo-Daten."""
    data_path = ROOT / "data" / "beispiel_emissionen_mit_jahr.csv"
    
    if data_path.exists():
        df = pd.read_csv(data_path)
        return df
