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


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
CSV_INPUT = DATA_DIR / "beispiel_emissionen_mit_jahr.csv"
IMAGES_DIR = DATA_DIR / "images"

GREEN_MAIN = "#2E7D32"
GREEN_MED = "#66BB6A"
GREEN_DARK = "#1B5E20"
WHITE = "#FFFFFF"
GRAY_900 = "#263238"
GRAY_600 = "#607D8B"
GRAY_100 = "#ECEFF1"

PLOTLY_TEMPLATE = "simple_white"


st.set_page_config(page_title="CO2 Portfolio Calculator", page_icon="☘︎", layout="wide")


st.markdown(
    f"""
<style>
html, body, [data-testid="stAppViewContainer"] {{
  background: {WHITE} !important;
  color: {GRAY_900} !important;
}}
section[data-testid="stSidebar"] {{
  background: {GRAY_100} !important;
}}

.main-header {{
  font-size: 2.6rem;
  font-weight: 900;
  color: {GREEN_MAIN};
  text-align: center;
  padding: 0.75rem 0 0.25rem 0;
}}
.sub-header {{
  text-align: center;
  color: {GRAY_600};
  margin-top: -0.25rem;
  margin-bottom: 1rem;
  font-weight: 700;
}}

a, a:visited {{ color: {GREEN_MAIN} !important; }}
a:hover {{ color: {GREEN_DARK} !important; }}

/* Radio */
section[data-testid="stSidebar"] input[type="radio"] {{
  accent-color: {GREEN_MAIN} !important;
}}

/* Multiselect Chips */
section[data-testid="stSidebar"] [data-baseweb="tag"] {{
  background-color: {GREEN_MED} !important;
  color: white !important;
  border: 0 !important;
  border-radius: 10px !important;
  font-weight: 800 !important;
}}
section[data-testid="stSidebar"] [data-baseweb="tag"] * {{
  color: white !important;
}}
section[data-testid="stSidebar"] [data-baseweb="tag"] svg {{
  fill: white !important;
}}

/* Slider */
section[data-testid="stSidebar"] [data-baseweb="slider"] div[role="slider"] {{
  background: {GREEN_MAIN} !important;
  border-color: {GREEN_MAIN} !important;
}}
section[data-testid="stSidebar"] [data-baseweb="slider"] div[style*="rgb(255, 75, 75)"] {{
  background-color: {GREEN_MAIN} !important;
}}
section[data-testid="stSidebar"] [data-baseweb="slider"] div[style*="rgb(0, 104, 201)"] {{
  background-color: {GREEN_MAIN} !important;
}}

.img-right img {{
  border-radius: 14px;
  object-fit: cover !important;
}}
</style>
""",
    unsafe_allow_html=True,
)


def format_number_ch(x) -> str:
    try:
        x = float(x)
    except Exception:
        return "0"
    return f"{int(round(x)):,}".replace(",", "'")


def format_chf(x) -> str:
    return f"{format_number_ch(x)}.-"


def parse_chf(s: str) -> int:
    if not s:
        return 0
    s = str(s).replace("CHF", "").replace(".-", "").replace("’", "'")
    s = s.replace(" ", "").replace(",", "").replace("'", "")
    try:
        return int(float(s))
    except Exception:
        return 0


def load_data() -> pd.DataFrame:
    df = pd.read_csv(CSV_INPUT, encoding="utf-8")
    msgs = validiere_eingabedaten(df)
    for m in msgs:
        if "Warnung" in m:
            st.sidebar.warning(m)
        else:
            st.sidebar.error(m)
    return df


def find_image_path(gebaeude_id: str) -> Path | None:
    gid = str(gebaeude_id).strip()
    for base in (gid, gid.replace(" ", "_")):
        for ext in ("jpg", "jpeg", "png", "webp"):
            p = IMAGES_DIR / f"{base}.{ext}"
            if p.exists():
                return p
    return None


def small_image_right(gebaeude_id: str, width: int = 340, height: int = 220):
    p = find_image_path(gebaeude_id)
    st.markdown('<div class="img-right">', unsafe_allow_html=True)
    if p:
        st.image(str(p), width=width)
    else:
        st.markdown(
            f"""
            <div style="
                width:{width}px;height:{height}px;
                border:1px dashed #A5D6A7;border-radius:14px;
                background:#F5F7F6;display:flex;
                align-items:center;justify-content:center;
                color:{GRAY_600};font-weight:800;">
                Kein Bild
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


def page_portfolio(df: pd.DataFrame):
    st.header("▦ Portfolio-Übersicht")

    jahr = int(df["jahr"].max())
    df_now = berechne_emissionen(df[df["jahr"] == jahr].copy())
    stats = analysiere_portfolio(df_now, KBOB_FAKTOREN)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Gebäude", f"{stats['anzahl_gebaeude']}")
    c2.metric("Gesamt-Emissionen", f"{stats['gesamt_emissionen_t_jahr']:.1f} t CO₂e/Jahr")
    c3.metric("Ø pro Gebäude", f"{stats['durchschnitt_emissionen_t_jahr']:.1f} t/Jahr")
    if stats.get("durchschnitt_emissionen_kg_m2") is not None:
        c4.metric("Ø pro m²", f"{stats['durchschnitt_emissionen_kg_m2']:.1f} kg/m²")
    else:
        c4.empty()

    st.subheader("Heizungstypen-Verteilung")
    heiz_df = pd.DataFrame(
        [{"Typ": k, "Anzahl": v} for k, v in stats.get("heizungstypen_verteilung", {}).items()]
    )
    fig = px.pie(
        heiz_df,
        values="Anzahl",
        names="Typ",
        template=PLOTLY_TEMPLATE,
        title="Verteilung nach Heizungstyp",
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    st.plotly_chart(fig, use_container_width=True)


def page_gebaeude(df: pd.DataFrame):
    df_now = berechne_emissionen(df[df["jahr"] == df["jahr"].max()].copy())

    gebaeude_id = st.sidebar.selectbox("Gebäude auswählen", list(df_now["gebaeude_id"].unique()))
    g = df_now[df_now["gebaeude_id"] == gebaeude_id].iloc[0]

    st.header(f"⌂ {gebaeude_id}")

    left, right = st.columns([4, 2], vertical_alignment="top")

    with left:
        st.write(f"**Heizung:** {g.get('heizung_typ', '-')}")
        if "baujahr" in g:
            try:
                st.write(f"**Baujahr:** {int(g['baujahr'])}")
            except Exception:
                pass
        st.write(f"**Verbrauch:** {format_number_ch(g.get('jahresverbrauch_kwh', 0))} kWh/Jahr")
        if "flaeche_m2" in g and pd.notna(g["flaeche_m2"]):
            st.write(f"**Fläche:** {format_number_ch(g.get('flaeche_m2', 0))} m²")
        st.write(f"**Emissionen:** {g.get('emissionen_gesamt_t', 0):.1f} t CO₂e/Jahr")

    with right:
        small_image_right(gebaeude_id, width=340, height=220)

    st.markdown("---")

    if "flaeche_m2" in g and pd.notna(g["flaeche_m2"]) and g["flaeche_m2"] > 0:
        st.subheader("|—| Benchmark-Vergleich")
        bdf = vergleiche_mit_standards(g, g.get("emissionen_gesamt_kg", 0))
        if isinstance(bdf, pd.DataFrame) and not bdf.empty:
            st.dataframe(bdf, use_container_width=True)

    st.header("✦ Sanierungsszenarien")

    szen = erstelle_alle_szenarien(g, KBOB_FAKTOREN) + erstelle_kombinationsszenarien(g, KBOB_FAKTOREN)
    szen = [wirtschaftlichkeitsanalyse(s, g) for s in szen]
    szen_df = priorisiere_sanierungen(szen, kriterium="score")

    st.sidebar.subheader("Filter")
    kategorie_filter = (
        st.sidebar.multiselect("Kategorie", list(szen_df["kategorie"].unique()), list(szen_df["kategorie"].unique()))
        if "kategorie" in szen_df.columns
        else []
    )

    if "max_inv" not in st.session_state:
        st.session_state.max_inv = 100_000

    st.sidebar.markdown("### Max. Investition")

    # Text -> Slider
    txt = st.sidebar.text_input("Betrag eingeben [CHF]:", value=format_chf(st.session_state.max_inv))
    val = parse_chf(txt)
    val = max(0, min(2_000_000, val))
    st.session_state.max_inv = val

    # Slider -> Text (bei Änderung)
    slider = st.sidebar.slider("Oder per Slider:", 0, 2_000_000, st.session_state.max_inv, 10_000)
    if slider != st.session_state.max_inv:
        st.session_state.max_inv = slider
        st.rerun()

    max_inv = st.session_state.max_inv
    st.sidebar.success(f"**Gewählt: CHF {format_chf(max_inv)}**")

    f = szen_df.copy()
    if kategorie_filter and "kategorie" in f.columns:
        f = f[f["kategorie"].isin(kategorie_filter)]
    if "investition_netto_chf" in f.columns:
        f = f[f["investition_netto_chf"] <= max_inv]

    st.subheader("Top-3 Empfehlungen")
    for i, row in f.head(3).iterrows():
        title = f"#{int(row.get('rang', i + 1))}: {row.get('name', 'Massnahme')}"
        with st.expander(title, expanded=(i == 0)):
            c1, c2, c3 = st.columns(3)
            c1.write(f"**Investition (netto):** CHF {format_chf(row.get('investition_netto_chf', 0))}")
            c1.write(f"**Förderung:** CHF {format_chf(row.get('foerderung_chf', 0))}")
            c2.write(f"**CO₂-Reduktion:** {row.get('co2_einsparung_kg_jahr', 0) / 1000:.1f} t/Jahr")
            c2.write(f"**Amortisation:** {row.get('amortisation_jahre', 0):.1f} Jahre")
            c3.write(f"**ROI:** {row.get('roi_prozent', 0):.1f}%")
            c3.write(f"**NPV:** CHF {format_chf(row.get('npv_chf', 0))}")

    st.subheader("Alle Szenarien")
    show_cols = [c for c in ["rang", "name", "kategorie", "investition_netto_chf", "amortisation_jahre", "roi_prozent", "npv_chf"] if c in f.columns]
    st.dataframe(f[show_cols], use_container_width=True)

    if len(f) > 0:
        with st.expander("Sensitivitätsanalyse (Top-Empfehlung)"):
            top = f.iloc[0].to_dict()
            parameter = st.selectbox(
                "Szenario",
                ["energiepreis", "co2_abgabe", "foerderung"],
                format_func=lambda x: {"energiepreis": "Energiepreis", "co2_abgabe": "CO₂-Abgabe", "foerderung": "Förderung"}[x],
            )
            sens_df = sensitivitaetsanalyse(top, g, parameter)

            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=sens_df["faktor"], y=sens_df["amortisation_jahre"], mode="lines+markers", name="Amortisation"))
            st.plotly_chart(fig2, use_container_width=True)
            st.dataframe(sens_df, use_container_width=True)


def page_vergleich(df: pd.DataFrame):
    st.header("≡ Gebäude-Vergleich")
    df_now = berechne_emissionen(df[df["jahr"] == df["jahr"].max()].copy())

    selected = st.multiselect(
        "Gebäude auswählen (max. 5)",
        list(df_now["gebaeude_id"].unique()),
        default=list(df_now["gebaeude_id"].unique())[:3],
    )
    if not selected:
        st.info("Bitte mindestens ein Gebäude auswählen.")
        return

    vdf = df_now[df_now["gebaeude_id"].isin(selected)].copy()
    cols = [c for c in ["gebaeude_id", "heizung_typ", "jahresverbrauch_kwh", "emissionen_gesamt_t"] if c in vdf.columns]
    st.dataframe(vdf[cols], use_container_width=True)

    fig = px.bar(vdf, x="gebaeude_id", y="emissionen_gesamt_t", color="heizung_typ", template=PLOTLY_TEMPLATE, title="CO₂-Emissionen pro Gebäude")
    st.plotly_chart(fig, use_container_width=True)


def main():
    st.markdown('<div class="main-header">☘︎ CO₂ Portfolio Calculator</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">HSLU Digital Twin Programmieren | Nicola Beeli & Mattia Rohrer</div>', unsafe_allow_html=True)

    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Seite auswählen", ["Portfolio-Übersicht", "Gebäude-Analyse", "Vergleich"])

    df = load_data()

    if page == "Portfolio-Übersicht":
        page_portfolio(df)
    elif page == "Gebäude-Analyse":
        page_gebaeude(df)
    else:
        page_vergleich(df)

    st.sidebar.markdown("---")
    st.sidebar.info("**HSLU Digital Twin Programmieren**  \nNicola Beeli & Mattia Rohrer")


if __name__ == "__main__":
    main()
