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

# Pfad zu src hinzufügen
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

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
        default=szenarien_df["kategorie"].unique()
    )
    
    max_investition = st.sidebar.slider(
        "Max. Investition [CHF]",
        0,
        int(szenarien_df["investition_netto_chf"].max()),
        int(szenarien_df["investition_netto_chf"].max())
    )
    
    # Filtern
    szenarien_gefiltert = szenarien_df[
        (szenarien_df["kategorie"].isin(kategorie_filter)) &
        (szenarien_df["investition_netto_chf"] <= max_investition)
    ]
    
    # Top-Empfehlungen
    st.subheader("🏆 Top-3 Empfehlungen")
    
    for idx, row in szenarien_gefiltert.head(3).iterrows():
        with st.expander(f"#{row['rang']}: {row['name']}", expanded=(idx == 0)):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Investition (netto)", f"CHF {row['investition_netto_chf']:,.0f}")
                st.metric("Förderung", f"CHF {row['foerderung_chf']:,.0f}")
            
            with col2:
                st.metric("CO₂-Reduktion", f"{row['co2_einsparung_kg_jahr']/1000:.1f} t/Jahr")
                st.metric("Amortisation", f"{row['amortisation_jahre']:.1f} Jahre")
            
            with col3:
                st.metric("ROI", f"{row['roi_prozent']:.1f}%")
                st.metric("NPV", f"CHF {row['npv_chf']:,.0f}")
            
            st.write("**Beschreibung:**", row["beschreibung"])
    
    # Vergleichstabelle
    st.subheader("📋 Alle Szenarien im Vergleich")
    
    vergleich_df = szenarien_gefiltert[[
        "rang", "name", "kategorie", "investition_netto_chf",
        "co2_einsparung_kg_jahr", "amortisation_jahre", "roi_prozent", "prioritaets_score"
    ]].copy()
    
    vergleich_df["co2_einsparung_t_jahr"] = vergleich_df["co2_einsparung_kg_jahr"] / 1000
    vergleich_df = vergleich_df.drop("co2_einsparung_kg_jahr", axis=1)
    
    st.dataframe(
        vergleich_df.style.format({
            "investition_netto_chf": "CHF {:,.0f}",
            "co2_einsparung_t_jahr": "{:.2f}",
            "amortisation_jahre": "{:.1f}",
            "roi_prozent": "{:.1f}%",
            "prioritaets_score": "{:.0f}"
        }),
        use_container_width=True
    )
    
    # Visualisierung: Kosten vs. CO₂
    st.subheader("📈 Kosten-Nutzen-Analyse")
    
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
    """Zeigt Sensitivitätsanalyse."""
    st.header("🔍 Sensitivitätsanalyse")
    
    st.write(f"**Massnahme:** {sanierung['name']}")
    
    # Parameter auswählen
    parameter = st.selectbox(
        "Szenario",
        ["energiepreis", "co2_abgabe", "foerderung"],
        format_func=lambda x: {
            "energiepreis": "Energiepreis-Entwicklung",
            "co2_abgabe": "CO₂-Abgabe",
            "foerderung": "Fördergelder"
        }[x]
    )
    
    # Sensitivität berechnen
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
    st.markdown('<div class="main-header">🌱 CO₂ Neutrality Path Calculator</div>', 
                unsafe_allow_html=True)
    st.markdown("**HSLU Digital Twin Programming** | Interaktive Analyse & Sanierungsplanung")
    
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
        # Gebäude auswählen
        df_aktuell = berechne_emissionen(df[df["jahr"] == df["jahr"].max()])
        
        gebaeude_id = st.sidebar.selectbox(
            "Gebäude auswählen",
            df_aktuell["gebaeude_id"].unique()
        )
        
        # Details anzeigen
        gebaeude = zeige_gebaeude_detail(df_aktuell, gebaeude_id)
        
        # Sanierungsszenarien
        szenarien_df = zeige_sanierungsszenarien(gebaeude)
        
        # Sensitivität (optional)
        if len(szenarien_df) > 0:
            with st.expander("🔬 Sensitivitätsanalyse (Top-Empfehlung)"):
                top_sanierung = szenarien_df.iloc[0].to_dict()
                zeige_sensitivitaet(gebaeude, top_sanierung)
    
    elif page == "Vergleich":
        st.header("⚖️ Gebäude-Vergleich")
        
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
    **HSLU Digital Twin Programming**  
    Nicola Beeli, Manuel Flühler, Domenic Zogg, Fabrice Bachofner Sarn
    """)


if __name__ == "__main__":
    main()
