from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from emissionen import validiere_eingabedaten, berechne_emissionen, KBOB_FAKTOREN
from sanierungen import erstelle_alle_szenarien, erstelle_kombinationsszenarien
from wirtschaftlichkeit import wirtschaftlichkeitsanalyse, sensitivitaetsanalyse
from empfehlungen import priorisiere_sanierungen
from benchmarks import vergleiche_mit_standards
from portfolio import analysiere_portfolio


# =========================================================
# Grundkonfiguration
# =========================================================
st.set_page_config(
    page_title="CO₂ Portfolio Calculator",
    page_icon="☘︎",
    layout="wide",
)

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
CSV_INPUT = DATA_DIR / "beispiel_emissionen_mit_jahr.csv"
IMAGES_DIR = DATA_DIR / "images"

# =========================================================
# Farben (Light Mode Basis)
# =========================================================
GREEN_MAIN = "#2E7D32"
GREEN_MED = "#66BB6A"
GREEN_LIGHT = "#A5D6A7"
GREEN_DARK = "#1B5E20"

GRAY_900 = "#263238"
GRAY_600 = "#607D8B"
GRAY_100 = "#ECEFF1"
WHITE = "#FFFFFF"

# Plotly: keine Default-Farben
px.defaults.template = "simple_white"
px.defaults.color_discrete_sequence = [GREEN_MAIN, GREEN_DARK, GREEN_MED, GREEN_LIGHT]


# =========================================================
# CSS – Light + Dark Mode (entscheidend)
# =========================================================
st.markdown(
    f"""
<style>

/* =======================
   LIGHT MODE (Default)
   ======================= */
html, body, [data-testid="stAppViewContainer"] {{
  background: {WHITE};
  color: {GRAY_900};
}}

section[data-testid="stSidebar"] {{
  background: {GRAY_100};
}}

.main-header {{
  font-size: 2.4rem;
  font-weight: 900;
  color: {GREEN_MAIN};
  text-align: center;
  margin-bottom: 0.2rem;
}}

.sub-header {{
  text-align: center;
  color: {GRAY_600};
  margin-bottom: 1rem;
}}

a {{ color: {GREEN_MAIN}; }}

input[type="radio"],
input[type="checkbox"] {{
  accent-color: {GREEN_MAIN};
}}

[data-baseweb="tag"] {{
  background: {GREEN_MED};
  color: white;
  font-weight: 700;
}}

[data-baseweb="slider"] div[role="slider"] {{
  background: {GREEN_MAIN};
  border-color: {GREEN_MAIN};
}}

[data-testid="stAlert"] {{
  background: #E8F5E9;
  border: 1px solid {GREEN_LIGHT};
  color: {GREEN_DARK};
}}

/* =======================
   DARK MODE
   ======================= */
@media (prefers-color-scheme: dark) {{

  html, body, [data-testid="stAppViewContainer"] {{
    background: #0E1117 !important;
    color: #E6E6E6 !important;
  }}

  section[data-testid="stSidebar"] {{
    background: #111827 !important;
  }}

  h1, h2, h3, h4, h5, h6, p, span, div {{
    color: #E6E6E6 !important;
  }}

  a {{
    color: #7CFF9B !important;
  }}

  /* Gruen mit mehr Kontrast */
  input[type="radio"],
  input[type="checkbox"] {{
    accent-color: #2ECC71 !important;
  }}

  [data-baseweb="tag"] {{
    background: #2ECC71 !important;
    color: #0B1F14 !important;
  }}

  [data-baseweb="slider"] div[role="slider"] {{
    background: #2ECC71 !important;
    border-color: #2ECC71 !important;
  }}

  [data-testid="stAlert"] {{
    background: #0F2F1E !important;
    border: 1px solid #58D68D !important;
    color: #A9F5C6 !important;
  }}

  [data-testid="stDataFrame"] {{
    background: #0E1117 !important;
    color: #E6E6E6 !important;
  }}
}}
</style>
""",
    unsafe_allow_html=True,
)


# =========================================================
# Hilfsfunktionen
# =========================================================
def format_chf(x):
    if pd.isna(x):
        return "-"
    return f"{int(round(float(x))):,}".replace(",", "'") + ".-"


def load_data():
    df = pd.read_csv(CSV_INPUT)
    for msg in validiere_eingabedaten(df):
        if "Warnung" in msg:
            st.sidebar.warning(msg)
        else:
            st.sidebar.error(msg)
    return df


# =========================================================
# Seiten
# =========================================================
def page_portfolio(df):
    st.header("Portfolio-Übersicht")

    df_now = berechne_emissionen(df[df["jahr"] == df["jahr"].max()].copy())
    stats = analysiere_portfolio(df_now, KBOB_FAKTOREN)

    c1, c2, c3 = st.columns(3)
    c1.metric("Gebäude", stats["anzahl_gebaeude"])
    c2.metric("Gesamt-Emissionen", f"{stats['gesamt_emissionen_t_jahr']:.1f} t CO₂e/Jahr")
    c3.metric("Ø pro Gebäude", f"{stats['durchschnitt_emissionen_t_jahr']:.1f} t/Jahr")


def page_gebaeude(df):
    df_now = berechne_emissionen(df[df["jahr"] == df["jahr"].max()].copy())
    gid = st.sidebar.selectbox("Gebäude auswählen", df_now["gebaeude_id"].unique())
    g = df_now[df_now["gebaeude_id"] == gid].iloc[0]

    st.header(gid)
    st.write(f"**Heizung:** {g['heizung_typ']}")
    st.write(f"**Emissionen:** {g['emissionen_gesamt_t']:.1f} t CO₂e/Jahr")

    fig = px.bar(
        x=["Emissionen"],
        y=[g["emissionen_gesamt_t"]],
    )
    fig.update_traces(marker_color=GREEN_MAIN)
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E6E6E6"),
    )
    st.plotly_chart(fig, use_container_width=True)


def page_vergleich(df):
    st.header("Vergleich")

    df_now = berechne_emissionen(df[df["jahr"] == df["jahr"].max()].copy())
    sel = st.multiselect(
        "Gebäude auswählen",
        df_now["gebaeude_id"].unique(),
        default=df_now["gebaeude_id"].unique()[:3],
    )

    vdf = df_now[df_now["gebaeude_id"].isin(sel)]

    fig = px.bar(
        vdf,
        x="gebaeude_id",
        y="emissionen_gesamt_t",
    )
    fig.update_traces(marker_color=GREEN_MAIN)
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E6E6E6"),
    )
    st.plotly_chart(fig, use_container_width=True)


# =========================================================
# Main
# =========================================================
def main():
    st.markdown('<div class="main-header">☘︎ CO₂ Portfolio Calculator</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">HSLU Digital Twin Programmieren</div>', unsafe_allow_html=True)

    page = st.sidebar.radio("Navigation", ["Portfolio", "Gebäude", "Vergleich"])
    df = load_data()

    if page == "Portfolio":
        page_portfolio(df)
    elif page == "Gebäude":
        page_gebaeude(df)
    else:
        page_vergleich(df)

    st.sidebar.info("Nicola Beeli · Mattia Rohrer")


if __name__ == "__main__":
    main()
