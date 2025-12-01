"""
CO₂ Neutrality Path Calculator - Streamlit Web App
Interactive Dashboard für Gebäude-Analyse und Sanierungsplanung
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys

# Pfad für Datenzugriff
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
    page_title="CO₂ Calculator",
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


def lade_daten():
    """Lädt Daten aus CSV oder nutzt Demo-Daten."""
    data_path = ROOT / "data" / "beispiel_emissionen_mit_jahr.csv"
    
    if data_path.exists():
        df = pd.read_csv(data_path)
        return df
    else:
        st.error(f"Datei nicht gefunden: {data_path}")
        return None


def zeige_portfolio_uebersicht(df):
    """Zeigt Portfolio-Übersicht."""
    st.header("📊 Portfolio-Übersicht")
    
    # Aktuelles Jahr
    aktuelles_jahr = df["jahr"].max()
    df_aktuell = df[df["jahr"] == aktuelles_jahr]
    
    # Emissionen berechnen
    df_aktuell = berechne_emissionen(df_aktuell)
    
    # Portfolio-Statistiken
    stats = analysiere_portfolio(df_aktuell, KBOB_FAKTOREN)
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Gebäude",
            f"{stats['anzahl_gebaeude']}"
        )
    
    with col2:
        st.metric(
            "Gesamt-Emissionen",
            f"{stats['gesamt_emissionen_t_jahr']:.1f} t CO₂e/Jahr"
        )
    
    with col3:
        st.metric(
            "Ø pro Gebäude",
            f"{stats['durchschnitt_emissionen_t_jahr']:.1f} t/Jahr"
        )
    
    with col4:
        if stats['durchschnitt_emissionen_kg_m2']:
            st.metric(
                "Ø pro m²",
                f"{stats['durchschnitt_emissionen_kg_m2']:.1f} kg/m²"
            )
    
    # Heizungstypen
    st.subheader("Heizungstypen-Verteilung")
    heiz_df = pd.DataFrame([
        {"Typ": k, "Anzahl": v} 
        for k, v in stats['heizungstypen_verteilung'].items()
    ])
    
    fig = px.pie(heiz_df, values="Anzahl", names="Typ", 
                 title="Verteilung nach Heizungstyp")
    st.plotly_chart(fig, use_container_width=True)
    
    return df_aktuell, stats


def zeige_gebaeude_detail(df_aktuell, gebaeude_id):
    """Zeigt Details für ein Gebäude."""
    gebaeude = df_aktuell[df_aktuell["gebaeude_id"] == gebaeude_id].iloc[0]
    
    st.header(f"🏢 {gebaeude_id}")
    
    # Basis-Infos
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.write("**Heizung:**", gebaeude["heizung_typ"])
        if "baujahr" in gebaeude:
            st.write("**Baujahr:**", int(gebaeude["baujahr"]))
    
    with col2:
        st.write("**Verbrauch:**", f"{gebaeude['jahresverbrauch_kwh']:,.0f} kWh/Jahr")
        if "flaeche_m2" in gebaeude:
            st.write("**Fläche:**", f"{gebaeude['flaeche_m2']:,.0f} m²")
    
    with col3:
        st.write("**Emissionen:**", f"{gebaeude['emissionen_gesamt_t']:.1f} t CO₂e/Jahr")
    
    # Benchmarks
    if "flaeche_m2" in gebaeude and gebaeude["flaeche_m2"] > 0:
        st.subheader("📏 Benchmark-Vergleich")
        
        emissionen_kg = gebaeude["emissionen_gesamt_kg"]
        standards_df = vergleiche_mit_standards(gebaeude, emissionen_kg)
        
        if not standards_df.empty:
            st.dataframe(
                standards_df[["standard", "beschreibung", "soll_kwh_m2", 
                             "ist_kwh_m2", "status"]],
                use_container_width=True
            )
    
    return gebaeude


def zeige_sanierungsszenarien(gebaeude):
    """Zeigt Sanierungsszenarien für ein Gebäude."""
    st.header("💡 Sanierungsszenarien")
    
    # Szenarien erstellen
    szenarien = erstelle_alle_szenarien(gebaeude, KBOB_FAKTOREN)
    kombinationen = erstelle_kombinationsszenarien(gebaeude, KBOB_FAKTOREN)
    
    alle_szenarien = szenarien + kombinationen
    
    # Wirtschaftlichkeit berechnen
    szenarien_wirtschaft = []
    for san in alle_szenarien:
        san_wirt = wirtschaftlichkeitsanalyse(san, gebaeude)
        szenarien_wirtschaft.append(san_wirt)
    
    # Priorisieren
    szenarien_df = priorisiere_sanierungen(szenarien_wirtschaft)
    
    # Filter-Optionen
    st.sidebar.subheader("🔧 Filter")
    
    kategorie_filter = st.sidebar.multiselect(
        "Kategorie",
        options=szenarien_df["kategorie"].unique(),
        default=szenarien_df["kategorie"].unique(),
        key="kategorie_filter_unique"
    )
    
    # Max. Investition mit Input + Slider
    st.sidebar.markdown("### 💰 Max. Investition")
    
    # Number Input für direkte Eingabe
    max_inv_input = st.sidebar.number_input(
        "Betrag eingeben [CHF]:",
        min_value=0,
        max_value=2000000,
        value=100000,
        step=10000,
        format="%d",
        key="max_inv_number_input",
        help="Direkt Betrag eingeben oder Slider nutzen"
    )
    
    # Slider für visuelle Anpas
