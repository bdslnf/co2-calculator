"""
CO2 Portfolio Calculator - Streamlit Web App
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
    page_title="CO2 Portfolio Calculator",
    page_icon="☘︎",
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
    else:
        st.error(f"Datei nicht gefunden: {data_path}")
        return None


def zeige_portfolio_uebersicht(df):
    """Zeigt Portfolio-Uebersicht."""
    st.header("▦ Portfolio-Übersicht")
    
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
    """Zeigt Details fuer ein Gebaeude."""
    gebaeude = df_aktuell[df_aktuell["gebaeude_id"] == gebaeude_id].iloc[0]
    
    st.header(f"⌂ {gebaeude_id}")
    
    # Basis-Infos
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.write("**Heizung:**", gebaeude["heizung_typ"])
        if "baujahr" in gebaeude:
            st.write("**Baujahr:**", int(gebaeude["baujahr"]))
    
    with col2:
        verbrauch_formatted = format_number_swiss(gebaeude['jahresverbrauch_kwh'])
        st.write("**Verbrauch:**", f"{verbrauch_formatted} kWh/Jahr")
        if "flaeche_m2" in gebaeude:
            flaeche_formatted = format_number_swiss(gebaeude['flaeche_m2'])
            st.write("**Fläche:**", f"{flaeche_formatted} m²")
    
    with col3:
        st.write("**Emissionen:**", f"{gebaeude['emissionen_gesamt_t']:.1f} t CO₂e/Jahr")
    
    # Benchmarks
    if "flaeche_m2" in gebaeude and gebaeude["flaeche_m2"] > 0:
        st.subheader("∣—∣ Benchmark-Vergleich")
        
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
    """Zeigt Sanierungsszenarien fuer ein Gebaeude."""
    st.header("✦ Sanierungsszenarien")
    
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
    st.sidebar.subheader("Filter")
    
    kategorie_filter = st.sidebar.multiselect(
        "Kategorie",
        options=szenarien_df["kategorie"].unique(),
        default=szenarien_df["kategorie"].unique(),
        key="kategorie_filter_unique"
    )
    
    # Max. Investition mit formatiertem Text Input + Slider
    st.sidebar.markdown("### ¤ Max. Investition")
    
    # Session State initialisieren
    if 'max_investition_wert' not in st.session_state:
        st.session_state.max_investition_wert = 100000
    
    # Text Input mit automatischer Formatierung
    current_formatted = format_number_swiss(st.session_state.max_investition_wert)
    
    text_input = st.sidebar.text_input(
        "Betrag eingeben [CHF]:",
        value=current_formatted,
        key="max_inv_text_input",
        help="Eingabe mit oder ohne Apostrophe: 100000 oder 100'000"
    )
    
    # Parse die Eingabe
    parsed_value = parse_swiss_number(text_input)
    if parsed_value != st.session_state.max_investition_wert:
        st.session_state.max_investition_wert = min(max(0, parsed_value), 2000000)
        st.rerun()
    
    # Slider (synchronisiert)
    slider_value = st.sidebar.slider(
        "Oder per Slider:",
        min_value=0,
        max_value=2000000,
        value=st.session_state.max_investition_wert,
        step=10000,
        key="max_inv_slider",
        format="%d"
    )
    
    # Update bei Slider-Aenderung
    if slider_value != st.session_state.max_investition_wert:
        st.session_state.max_investition_wert = slider_value
        st.rerun()
    
    # Finale Variable
    max_investition = st.session_state.max_investition_wert
    
    # Grosse formatierte Anzeige
    formatted_display = format_number_swiss(max_investition)
    st.sidebar.success(f"**Gewählt: CHF {formatted_display}**")
    
    # Slider-Wert mit Apostrophen anzeigen
    slider_min_formatted = format_number_swiss(0)
    slider_max_formatted = format_number_swiss(2000000)
    slider_current_formatted = format_number_swiss(max_investition)
    st.sidebar.caption(f"▦ Bereich: {slider_min_formatted} - {slider_max_formatted} CHF")
    
    # Filtern
    szenarien_gefiltert = szenarien_df[
        (szenarien_df["kategorie"].isin(kategorie_filter)) &
        (szenarien_df["investition_netto_chf"] <= max_investition)
    ]
    
    # Top-Empfehlungen
    st.subheader("★ Top-3 Empfehlungen")
    
    for idx, row in szenarien_gefiltert.head(3).iterrows():
        with st.expander(f"#{row['rang']}: {row['name']}", expanded=(idx == 0)):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                inv_formatted = format_number_swiss(row['investition_netto_chf'])
                foerd_formatted = format_number_swiss(row['foerderung_chf'])
                st.metric("Investition (netto)", f"CHF {inv_formatted}")
                st.metric("Förderung", f"CHF {foerd_formatted}")
            
            with col2:
                st.metric("CO₂-Reduktion", f"{row['co2_einsparung_kg_jahr']/1000:.1f} t/Jahr")
                st.metric("Amortisation", f"{row['amortisation_jahre']:.1f} Jahre")
            
            with col3:
                npv_formatted = format_number_swiss(row['npv_chf'])
                st.metric("ROI", f"{row['roi_prozent']:.1f}%")
                st.metric("NPV", f"CHF {npv_formatted}")
            
            st.write("**Beschreibung:**", row["beschreibung"])
    
    # Vergleichstabelle
    st.subheader("≡ Alle Szenarien im Vergleich")
    
    vergleich_df = szenarien_gefiltert[[
        "rang", "name", "kategorie", "investition_netto_chf",
        "co2_einsparung_kg_jahr", "amortisation_jahre", "roi_prozent", "prioritaets_score"
    ]].copy()
    
    vergleich_df["co2_einsparung_t_jahr"] = vergleich_df["co2_einsparung_kg_jahr"] / 1000
    vergleich_df = vergleich_df.drop("co2_einsparung_kg_jahr", axis=1)
    
    # Formatierung fuer Tabelle
    vergleich_df_display = vergleich_df.copy()
    vergleich_df_display["investition_netto_chf"] = vergleich_df_display["investition_netto_chf"].apply(
        lambda x: f"CHF {format_number_swiss(x)}"
    )
    
    st.dataframe(
        vergleich_df_display.style.format({
            "co2_einsparung_t_jahr": "{:.2f}",
            "amortisation_jahre": "{:.1f}",
            "roi_prozent": "{:.1f}%",
            "prioritaets_score": "{:.0f}"
        }),
        use_container_width=True
    )
    
    # Visualisierung: Kosten vs. CO2
    st.subheader("▦ Kosten-Nutzen-Analyse")
    
    fig = px.scatter(
        szenarien_gefiltert,
        x="investition_netto_chf",
        y="co2_einsparung_kg_jahr",
        size="prioritaets_score",
        color="kategorie",
        hover_data=["name", "amortisation_jahre", "roi_prozent"],
        labels={
            "investition_netto_chf": "Investition [CHF]",
            "co2_einsparung_kg_jahr": "CO₂-Reduktion [kg/Jahr]",
            "kategorie": "Kategorie"
        },
        title="Investition vs. CO₂-Reduktion (Größe = Priorität)"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    return szenarien_gefiltert


def zeige_sensitivitaet(gebaeude, sanierung):
    """Zeigt Sensitivitaetsanalyse."""
    st.header("⌕ Sensitivitätsanalyse")
    
    st.write(f"**Massnahme:** {sanierung['name']}")
    
    # Parameter auswaehlen
    parameter = st.selectbox(
        "Szenario",
        ["energiepreis", "co2_abgabe", "foerderung"],
        format_func=lambda x: {
            "energiepreis": "Energiepreis-Entwicklung",
            "co2_abgabe": "CO₂-Abgabe",
            "foerderung": "Fördergelder"
        }[x]
    )
    
    # Sensitivitaet berechnen
    sens_df = sensitivitaetsanalyse(sanierung, gebaeude, parameter)
    
    # Visualisierung
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=sens_df["faktor"],
        y=sens_df["amortisation_jahre"],
        mode="lines+markers",
        name="Amortisation",
        yaxis="y"
    ))
    
    fig.add_trace(go.Scatter(
        x=sens_df["faktor"],
        y=sens_df["npv_chf"],
        mode="lines+markers",
        name="NPV",
        yaxis="y2"
    ))
    
    fig.update_layout(
        title=f"Sensitivität: {parameter}",
        xaxis_title="Multiplikator (1.0 = Basis)",
        yaxis_title="Amortisation [Jahre]",
        yaxis2=dict(
            title="NPV [CHF]",
            overlaying="y",
            side="right"
        ),
        hovermode="x unified"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Tabelle
    st.dataframe(sens_df, use_container_width=True)


def main():
    """Hauptfunktion der Streamlit App."""
    
    # Header
    st.markdown('<div class="main-header">☘︎ CO₂ Portfolio Calculator</div>', 
                unsafe_allow_html=True)
    st.markdown("**HSLU Digital Twin Programmieren** | Nicola Beeli & Mattia Rohrer")
    
    # Sidebar
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Seite auswählen",
        ["Portfolio-Übersicht", "Gebäude-Analyse", "Vergleich"]
    )
    
    # Daten laden
    df = lade_daten()
    
    if df is None:
        st.stop()
    
    # Seiten
    if page == "Portfolio-Übersicht":
        df_aktuell, stats = zeige_portfolio_uebersicht(df)
        
        # Top-Emittenten
        st.subheader("🔴 Top-5 Emittenten")
        top_df = df_aktuell.nlargest(5, "emissionen_gesamt_t")[
            ["gebaeude_id", "heizung_typ", "emissionen_gesamt_t"]
        ]
        st.dataframe(top_df, use_container_width=True)
        
    elif page == "Gebäude-Analyse":
        # Gebaeude auswaehlen
        df_aktuell = berechne_emissionen(df[df["jahr"] == df["jahr"].max()])
        
        gebaeude_id = st.sidebar.selectbox(
            "Gebäude auswählen",
            df_aktuell["gebaeude_id"].unique()
        )
        
        # Details anzeigen
        gebaeude = zeige_gebaeude_detail(df_aktuell, gebaeude_id)
        
        # Sanierungsszenarien
        szenarien_df = zeige_sanierungsszenarien(gebaeude)
        
        # Sensitivitaet (optional)
        if len(szenarien_df) > 0:
            with st.expander("⌕ Sensitivitätsanalyse (Top-Empfehlung)"):
                top_sanierung = szenarien_df.iloc[0].to_dict()
                zeige_sensitivitaet(gebaeude, top_sanierung)
    
    elif page == "Vergleich":
        st.header("≡ Gebäude-Vergleich")
        
        df_aktuell = berechne_emissionen(df[df["jahr"] == df["jahr"].max()])
        
        # Multi-Select
        ausgewaehlte = st.multiselect(
            "Gebäude auswählen (max. 5)",
            df_aktuell["gebaeude_id"].unique(),
            default=df_aktuell["gebaeude_id"].unique()[:3]
        )
        
        if ausgewaehlte:
            vergleich_df = df_aktuell[df_aktuell["gebaeude_id"].isin(ausgewaehlte)]
            
            # Vergleichstabelle
            st.dataframe(
                vergleich_df[["gebaeude_id", "heizung_typ", "jahresverbrauch_kwh", 
                             "emissionen_gesamt_t"]],
                use_container_width=True
            )
            
            # Chart
            fig = px.bar(
                vergleich_df,
                x="gebaeude_id",
                y="emissionen_gesamt_t",
                color="heizung_typ",
                title="CO₂-Emissionen im Vergleich"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.info("""
    **HSLU Digital Twin Programmieren**  
    Nicola Beeli & Mattia Rohrer
    """)


if __name__ == "__main__":
    main()
