"""
CO2 Portfolio Calculator - Streamlit Web App
Interactive Dashboard fuer Gebaeude-Analyse und Sanierungsplanung
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
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


# =========================
# Design System (Gruen)
# =========================
GREEN_DARK = "#1B5E20"
GREEN_MAIN = "#2E7D32"
GREEN_MED = "#66BB6A"
GREEN_LIGHT = "#A5D6A7"
GRAY_DARK = "#263238"
GRAY_MID = "#607D8B"
GRAY_LIGHT = "#ECEFF1"
WHITE = "#FFFFFF"

# Einfache, konsistente Farb-Maps
COLOR_MAP_HEIZUNG = {
    "Gas": GREEN_DARK,
    "Fernwärme": GREEN_MAIN,
    "Wärmepumpe": GREEN_MED,
    "Öl": GREEN_LIGHT,
    "Pellets": GREEN_MED,
    "Solar": GREEN_LIGHT,
}

# Kategorien kommen aus sanierungen.py; wir mappen robust auf 3-4 Gruentoene
# (falls neue Kategorien auftauchen: Fallback = GREEN_MAIN)
CATEGORY_COLORS_FALLBACK = [GREEN_DARK, GREEN_MAIN, GREEN_MED, GREEN_LIGHT]


def get_category_color_map(categories):
    cats = list(pd.Series(categories).dropna().unique())
    mapping = {}
    for i, c in enumerate(cats):
        mapping[c] = CATEGORY_COLORS_FALLBACK[i % len(CATEGORY_COLORS_FALLBACK)]
    return mapping


# Plotly Template: ruhiger Look
PLOTLY_TEMPLATE = "simple_white"


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
:root{
  --green-dark:  #1B5E20;
  --green-main:  #2E7D32;
  --green-med:   #66BB6A;
  --green-light: #A5D6A7;

  --gray-900: #263238;
  --gray-600: #607D8B;
  --gray-100: #ECEFF1;
  --white:    #FFFFFF;
}

html, body, [data-testid="stAppViewContainer"]{
  background: var(--white) !important;
  color: var(--gray-900) !important;
}

section[data-testid="stSidebar"]{
  background: var(--gray-100) !important;
}


div[data-baseweb="tag"],
div[data-baseweb="tag"] > span{
  background-color: var(--green-med) !important;
  color: var(--white) !important;
  border-radius: 10px !important;
  font-weight: 700 !important;
}

div[data-baseweb="tag"] svg{
  fill: var(--white) !important;
}

div[data-testid="stMultiSelect"] span[role="button"],
div[data-testid="stMultiSelect"] div[role="button"]{
  background-color: var(--green-med) !important;
  color: var(--white) !important;
  border: 0 !important;
  border-radius: 10px !important;
  font-weight: 700 !important;
}

div[data-baseweb="select"] > div{
  border-color: rgba(46,125,50,0.55) !important;
}

div[data-baseweb="select"] > div:focus-within{
  box-shadow: 0 0 0 2px rgba(46,125,50,0.25) !important;
  border-color: var(--green-main) !important;
}


div[data-testid="stSlider"] [data-baseweb="slider"] div[role="slider"]{
  background: var(--green-main) !important;
}

div[data-testid="stSlider"] [data-baseweb="slider"] div[aria-valuemin] ~ div{
  background: var(--green-main) !important;
}

div[data-testid="stSlider"] *{
  color: var(--gray-900) !important;
}
div[data-testid="stSlider"] p,
div[data-testid="stSlider"] span{
  color: var(--gray-900) !important;
}


div[data-testid="stRadio"] label{
  color: var(--gray-900) !important;
}
div[data-testid="stRadio"] input[type="radio"]{
  accent-color: var(--green-main) !important;
}


a, a:visited{
  color: var(--green-main) !important;
}
a:hover{
  color: var(--green-dark) !important;
}

/* Icons in Sidebar (Fragezeichen etc.) */
svg, svg *{
  stroke: currentColor !important;
}

button[kind="primary"]{
  background: var(--green-main) !important;
  border-color: var(--green-main) !important;
}
button[kind="secondary"]{
  color: var(--green-main) !important;
  border-color: var(--green-main) !important;
}

*:focus{
  outline: none !important;
  box-shadow: none !important;
}
</style>
""", unsafe_allow_html=True)


def format_number_swiss(value):
    """Formatiert Zahlen im Schweizer Format mit Apostrophen."""
    try:
        value = float(value)
    except Exception:
        return "0"
    if value == 0:
        return "0"
    return f"{int(round(value)): ,}".replace(",", "").replace(" ", "'")


def parse_swiss_number(text):
    """Konvertiert Schweizer Format (mit Apostrophen) zurueck zu Zahl."""
    if not text:
        return 0
    cleaned = text.replace("'", "").replace(" ", "").replace(",", "")
    try:
        return int(cleaned)
    except Exception:
        return 0


def lade_daten():
    """Laedt Daten aus CSV oder nutzt Demo-Daten."""
    data_path = ROOT / "data" / "beispiel_emissionen_mit_jahr.csv"
    if data_path.exists():
        return pd.read_csv(data_path)
    st.error(f"Datei nicht gefunden: {data_path}")
    return None


def zeige_portfolio_uebersicht(df):
    """Zeigt Portfolio-Uebersicht."""
    st.header("▦ Portfolio-Uebersicht")

    aktuelles_jahr = df["jahr"].max()
    df_aktuell = df[df["jahr"] == aktuelles_jahr].copy()

    # Emissionen berechnen
    df_aktuell = berechne_emissionen(df_aktuell)

    # Portfolio-Statistiken
    stats = analysiere_portfolio(df_aktuell, KBOB_FAKTOREN)

    # Metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Gebaeude", f"{stats['anzahl_gebaeude']}")

    with col2:
        st.metric("Gesamt-Emissionen", f"{stats['gesamt_emissionen_t_jahr']:.1f} t CO₂e/Jahr")

    with col3:
        st.metric("Ø pro Gebaeude", f"{stats['durchschnitt_emissionen_t_jahr']:.1f} t/Jahr")

    with col4:
        if stats.get("durchschnitt_emissionen_kg_m2"):
            st.metric("Ø pro m²", f"{stats['durchschnitt_emissionen_kg_m2']:.1f} kg/m²")

    # Heizungstypen
    st.subheader("Heizungstypen-Verteilung")

    heiz_df = pd.DataFrame([
        {"Typ": k, "Anzahl": v}
        for k, v in stats.get("heizungstypen_verteilung", {}).items()
    ])

    # Falls Typen nicht in Map: Fallback auf GREEN_MAIN
    heiz_color_map = {t: COLOR_MAP_HEIZUNG.get(t, GREEN_MAIN) for t in heiz_df["Typ"].unique()}

    fig = px.pie(
        heiz_df,
        values="Anzahl",
        names="Typ",
        color="Typ",
        color_discrete_map=heiz_color_map,
        title="Verteilung nach Heizungstyp",
        template=PLOTLY_TEMPLATE
    )

    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        marker=dict(line=dict(color=WHITE, width=2))
    )

    fig.update_layout(
        legend_title_text="Heizung",
        margin=dict(t=60, b=20, l=20, r=20)
    )

    st.plotly_chart(fig, use_container_width=True)

    return df_aktuell, stats


def zeige_gebaeude_detail(df_aktuell, gebaeude_id):
    """Zeigt Details fuer ein Gebaeude."""
    gebaeude = df_aktuell[df_aktuell["gebaeude_id"] == gebaeude_id].iloc[0]

    st.header(f"⌂ {gebaeude_id}")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.write("**Heizung:**", gebaeude["heizung_typ"])
        if "baujahr" in gebaeude:
            try:
                st.write("**Baujahr:**", int(gebaeude["baujahr"]))
            except Exception:
                pass

    with col2:
        verbrauch_formatted = format_number_swiss(gebaeude.get("jahresverbrauch_kwh", 0))
        st.write("**Verbrauch:**", f"{verbrauch_formatted} kWh/Jahr")
        if "flaeche_m2" in gebaeude:
            flaeche_formatted = format_number_swiss(gebaeude.get("flaeche_m2", 0))
            st.write("**Flaeche:**", f"{flaeche_formatted} m²")

    with col3:
        st.write("**Emissionen:**", f"{gebaeude.get('emissionen_gesamt_t', 0):.1f} t CO₂e/Jahr")

    # Benchmarks
    if "flaeche_m2" in gebaeude and pd.notna(gebaeude["flaeche_m2"]) and gebaeude["flaeche_m2"] > 0:
        st.subheader("∣—∣ Benchmark-Vergleich")

        emissionen_kg = gebaeude.get("emissionen_gesamt_kg", 0)
        standards_df = vergleiche_mit_standards(gebaeude, emissionen_kg)

        if isinstance(standards_df, pd.DataFrame) and not standards_df.empty:
            st.dataframe(
                standards_df[["standard", "beschreibung", "soll_kwh_m2", "ist_kwh_m2", "status"]],
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
        options=list(szenarien_df["kategorie"].unique()),
        default=list(szenarien_df["kategorie"].unique()),
        key="kategorie_filter_unique"
    )

    # Max. Investition
    st.sidebar.markdown("### ¤ Max. Investition")

    if "max_investition_wert" not in st.session_state:
        st.session_state.max_investition_wert = 100000

    current_formatted = format_number_swiss(st.session_state.max_investition_wert)

    text_input = st.sidebar.text_input(
        "Betrag eingeben [CHF]:",
        value=current_formatted,
        key="max_inv_text_input",
        help="Eingabe mit oder ohne Apostrophe: 100000 oder 100'000"
    )

    parsed_value = parse_swiss_number(text_input)
    if parsed_value != st.session_state.max_investition_wert:
        st.session_state.max_investition_wert = min(max(0, parsed_value), 2000000)
        st.rerun()

    slider_value = st.sidebar.slider(
        "Oder per Slider:",
        min_value=0,
        max_value=2000000,
        value=st.session_state.max_investition_wert,
        step=10000,
        key="max_inv_slider",
        format="%d"
    )

    if slider_value != st.session_state.max_investition_wert:
        st.session_state.max_investition_wert = slider_value
        st.rerun()

    max_investition = st.session_state.max_investition_wert
    formatted_display = format_number_swiss(max_investition)
    st.sidebar.success(f"**Gewaehlt: CHF {formatted_display}**")
    st.sidebar.caption(f"▦ Bereich: {format_number_swiss(0)} - {format_number_swiss(2000000)} CHF")

    # Filtern
    szenarien_gefiltert = szenarien_df[
        (szenarien_df["kategorie"].isin(kategorie_filter)) &
        (szenarien_df["investition_netto_chf"] <= max_investition)
    ].copy()

    # Top-Empfehlungen
    st.subheader("★ Top-3 Empfehlungen")

    for idx, row in szenarien_gefiltert.head(3).iterrows():
        with st.expander(f"#{row['rang']}: {row['name']}", expanded=(idx == 0)):
            c1, c2, c3 = st.columns(3)

            with c1:
                inv_formatted = format_number_swiss(row.get("investition_netto_chf", 0))
                foerd_formatted = format_number_swiss(row.get("foerderung_chf", 0))
                st.metric("Investition (netto)", f"CHF {inv_formatted}")
                st.metric("Foerderung", f"CHF {foerd_formatted}")

            with c2:
                st.metric("CO₂-Reduktion", f"{row.get('co2_einsparung_kg_jahr', 0)/1000:.1f} t/Jahr")
                st.metric("Amortisation", f"{row.get('amortisation_jahre', 0):.1f} Jahre")

            with c3:
                npv_formatted = format_number_swiss(row.get("npv_chf", 0))
                st.metric("ROI", f"{row.get('roi_prozent', 0):.1f}%")
                st.metric("NPV", f"CHF {npv_formatted}")

            st.write("**Beschreibung:**", row.get("beschreibung", ""))

    # Vergleichstabelle
    st.subheader("≡ Alle Szenarien im Vergleich")

    vergleich_cols = [
        "rang", "name", "kategorie", "investition_netto_chf",
        "co2_einsparung_kg_jahr", "amortisation_jahre", "roi_prozent", "prioritaets_score"
    ]
    vergleich_df = szenarien_gefiltert[vergleich_cols].copy()

    vergleich_df["co2_einsparung_t_jahr"] = vergleich_df["co2_einsparung_kg_jahr"] / 1000
    vergleich_df = vergleich_df.drop("co2_einsparung_kg_jahr", axis=1)

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

    # Visualisierung: Kosten vs CO2 (weniger Farben: Kategorien in Gruentoenen)
    st.subheader("▦ Kosten-Nutzen-Analyse")

    cat_color_map = get_category_color_map(szenarien_gefiltert["kategorie"]) if len(szenarien_gefiltert) else {}

    fig = px.scatter(
        szenarien_gefiltert,
        x="investition_netto_chf",
        y="co2_einsparung_kg_jahr",
        size="prioritaets_score",
        color="kategorie",
        color_discrete_map=cat_color_map,
        hover_data=["name", "amortisation_jahre", "roi_prozent"],
        labels={
            "investition_netto_chf": "Investition [CHF]",
            "co2_einsparung_kg_jahr": "CO₂-Reduktion [kg/Jahr]",
            "kategorie": "Kategorie"
        },
        title="Investition vs. CO₂-Reduktion (Groesse = Prioritaet)",
        template=PLOTLY_TEMPLATE
    )

    fig.update_traces(marker=dict(opacity=0.85, line=dict(width=0)))
    fig.update_layout(
        legend_title_text="Kategorie",
        margin=dict(t=60, b=20, l=20, r=20)
    )

    st.plotly_chart(fig, use_container_width=True)

    return szenarien_gefiltert


def zeige_sensitivitaet(gebaeude, sanierung):
    """Zeigt Sensitivitaetsanalyse."""
    st.header("⌕ Sensitivitaetsanalyse")
    st.write(f"**Massnahme:** {sanierung.get('name', '')}")

    parameter = st.selectbox(
        "Szenario",
        ["energiepreis", "co2_abgabe", "foerderung"],
        format_func=lambda x: {
            "energiepreis": "Energiepreis-Entwicklung",
            "co2_abgabe": "CO₂-Abgabe",
            "foerderung": "Foerdergelder"
        }[x]
    )

    sens_df = sensitivitaetsanalyse(sanierung, gebaeude, parameter)

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=sens_df["faktor"],
        y=sens_df["amortisation_jahre"],
        mode="lines+markers",
        name="Amortisation",
        line=dict(color=GREEN_MAIN, width=3),
        marker=dict(size=7, color=GREEN_MAIN),
        yaxis="y"
    ))

    fig.add_trace(go.Scatter(
        x=sens_df["faktor"],
        y=sens_df["npv_chf"],
        mode="lines+markers",
        name="NPV",
        line=dict(color=GREEN_DARK, width=3),
        marker=dict(size=7, color=GREEN_DARK),
        yaxis="y2"
    ))

    fig.update_layout(
        title=f"Sensitivitaet: {parameter}",
        xaxis_title="Multiplikator (1.0 = Basis)",
        yaxis_title="Amortisation [Jahre]",
        yaxis2=dict(
            title="NPV [CHF]",
            overlaying="y",
            side="right"
        ),
        hovermode="x unified",
        template=PLOTLY_TEMPLATE,
        margin=dict(t=60, b=20, l=20, r=20)
    )

    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(sens_df, use_container_width=True)


def main():
    """Hauptfunktion der Streamlit App."""

    st.markdown('<div class="main-header">☘︎ CO₂ Portfolio Calculator</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">HSLU Digital Twin Programmieren | Nicola Beeli & Mattia Rohrer</div>',
                unsafe_allow_html=True)

    # Sidebar
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Seite auswaehlen",
        ["Portfolio-Uebersicht", "Gebaeude-Analyse", "Vergleich"]
    )

    # Daten laden
    df = lade_daten()
    if df is None:
        st.stop()

    # Seiten
    if page == "Portfolio-Uebersicht":
        df_aktuell, stats = zeige_portfolio_uebersicht(df)

        st.subheader("Top-5 Emittenten")
        top_df = df_aktuell.nlargest(5, "emissionen_gesamt_t")[
            ["gebaeude_id", "heizung_typ", "emissionen_gesamt_t"]
        ].copy()
        st.dataframe(top_df, use_container_width=True)

    elif page == "Gebaeude-Analyse":
        df_aktuell = berechne_emissionen(df[df["jahr"] == df["jahr"].max()].copy())

        gebaeude_id = st.sidebar.selectbox(
            "Gebaeude auswaehlen",
            list(df_aktuell["gebaeude_id"].unique())
        )

        gebaeude = zeige_gebaeude_detail(df_aktuell, gebaeude_id)

        szenarien_df = zeige_sanierungsszenarien(gebaeude)

        if isinstance(szenarien_df, pd.DataFrame) and len(szenarien_df) > 0:
            with st.expander("⌕ Sensitivitaetsanalyse (Top-Empfehlung)"):
                top_sanierung = szenarien_df.iloc[0].to_dict()
                zeige_sensitivitaet(gebaeude, top_sanierung)

    elif page == "Vergleich":
        st.header("≡ Gebaeude-Vergleich")

        df_aktuell = berechne_emissionen(df[df["jahr"] == df["jahr"].max()].copy())

        ausgewaehlte = st.multiselect(
            "Gebaeude auswaehlen (max. 5)",
            list(df_aktuell["gebaeude_id"].unique()),
            default=list(df_aktuell["gebaeude_id"].unique())[:3]
        )

        if ausgewaehlte:
            vergleich_df = df_aktuell[df_aktuell["gebaeude_id"].isin(ausgewaehlte)].copy()

            st.dataframe(
                vergleich_df[["gebaeude_id", "heizung_typ", "jahresverbrauch_kwh", "emissionen_gesamt_t"]],
                use_container_width=True
            )

            # Einheitliche Gruenfarben nach Heizungstyp
            heiz_color_map = {t: COLOR_MAP_HEIZUNG.get(t, GREEN_MAIN) for t in vergleich_df["heizung_typ"].unique()}

            fig = px.bar(
                vergleich_df,
                x="gebaeude_id",
                y="emissionen_gesamt_t",
                color="heizung_typ",
                color_discrete_map=heiz_color_map,
                title="CO₂-Emissionen im Vergleich",
                template=PLOTLY_TEMPLATE
            )
            fig.update_layout(
                legend_title_text="Heizung",
                margin=dict(t=60, b=20, l=20, r=20)
            )
            st.plotly_chart(fig, use_container_width=True)

    # Footer
    st.sidebar.markdown("---")
    st.sidebar.info(
        "**HSLU Digital Twin Programmieren**  \n"
        "Nicola Beeli & Mattia Rohrer"
    )


if __name__ == "__main__":
    main()
