"""
MAIN (Entry-Point) – CO2 Portfolio Calculator - Streamlit Web App
HSLU Digital Twin Programmieren | Nicola Beeli & Mattia Rohrer

WICHTIGE AENDERUNGEN (wie gewuenscht):
- Gebaeude-Analyse: Ausgangsdaten LINKS als Textzeilen (inkl. Emissionen), Bild RECHTS klein (fixe Breite).
- KEIN grosses Bild oben (keine volle Breite).
- Sidebar: Tags (Multiselect), Radio, Slider, Links -> Gruen (robuste CSS Overrides).
- Bilder liegen unter: data/images/<gebaeude_id>.(jpg|jpeg|png|webp)
- Keine Standort-Karte.

Hinweis:
Wenn bei dir vorher "keine Aenderung" kam, lag es sehr wahrscheinlich daran, dass Streamlit eine andere Datei gestartet hat.
Mit diesem File startest du sicher richtig via: streamlit run main.py
"""

from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from emissionen import (
    validiere_eingabedaten,
    berechne_emissionen,
    KBOB_FAKTOREN,
)
from sanierungen import erstelle_alle_szenarien, erstelle_kombinationsszenarien
from wirtschaftlichkeit import wirtschaftlichkeitsanalyse, sensitivitaetsanalyse
from empfehlungen import priorisiere_sanierungen
from benchmarks import vergleiche_mit_standards
from portfolio import analysiere_portfolio


# ------------------------------------------------------------
# Pfade
# ------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
CSV_INPUT = DATA_DIR / "beispiel_emissionen_mit_jahr.csv"
IMAGES_DIR = DATA_DIR / "images"


# ------------------------------------------------------------
# Design System (Gruen)
# ------------------------------------------------------------
GREEN_DARK = "#1B5E20"
GREEN_MAIN = "#2E7D32"
GREEN_MED = "#66BB6A"
GREEN_LIGHT = "#A5D6A7"

GRAY_900 = "#263238"
GRAY_700 = "#455A64"
GRAY_600 = "#607D8B"
GRAY_200 = "#E5E7EB"
GRAY_100 = "#ECEFF1"
WHITE = "#FFFFFF"

PLOTLY_TEMPLATE = "simple_white"

COLOR_MAP_HEIZUNG = {
    "Gas": GREEN_DARK,
    "Fernwärme": GREEN_MAIN,
    "Wärmepumpe": GREEN_MED,
    "Öl": GREEN_LIGHT,
    "Pellets": GREEN_MED,
    "Solar": GREEN_LIGHT,
}


def get_category_color_map(categories):
    fallback = [GREEN_DARK, GREEN_MAIN, GREEN_MED, GREEN_LIGHT]
    cats = list(pd.Series(categories).dropna().unique())
    return {c: fallback[i % len(fallback)] for i, c in enumerate(cats)}


# ------------------------------------------------------------
# Streamlit Config
# ------------------------------------------------------------
st.set_page_config(
    page_title="CO2 Portfolio Calculator",
    page_icon="☘︎",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------
# CSS: Rot/Blau -> Gruen (robust)
# ------------------------------------------------------------
st.markdown(
    f"""
<style>
/* ----- Force Streamlit theme vars (hilft gegen Blau/Rot Defaults) ----- */
:root {{
  --primary-color: {GREEN_MAIN};
  --secondary-background-color: {GRAY_100};
  --text-color: {GRAY_900};
}}

/* ----- Base Layout ----- */
html, body, [data-testid="stAppViewContainer"] {{
  background: {WHITE} !important;
  color: {GRAY_900} !important;
}}
section[data-testid="stSidebar"] {{
  background: {GRAY_100} !important;
}}

/* ----- Headings ----- */
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

/* ----- Links (Blau -> Gruen) ----- */
a, a:visited {{
  color: {GREEN_MAIN} !important;
}}
a:hover {{
  color: {GREEN_DARK} !important;
}}

/* ==========================================================
   SIDEBAR CONTROLS (Multiselect Tags / Radio / Slider)
   ========================================================== */

/* Radio circle (rot -> gruen) */
section[data-testid="stSidebar"] input[type="radio"] {{
  accent-color: {GREEN_MAIN} !important;
}}

/* Slider thumb/track (rot -> gruen) */
section[data-testid="stSidebar"] div[data-testid="stSlider"] [data-baseweb="slider"] div[role="slider"] {{
  background: {GREEN_MAIN} !important;
}}
/* Slider value text (nicht rot) */
section[data-testid="stSidebar"] div[data-testid="stSlider"] * {{
  color: {GRAY_900} !important;
}}

/* Select focus border */
section[data-testid="stSidebar"] div[data-baseweb="select"] > div {{
  border-color: rgba(46,125,50,0.55) !important;
}}
section[data-testid="stSidebar"] div[data-baseweb="select"] > div:focus-within {{
  border-color: {GREEN_MAIN} !important;
  box-shadow: 0 0 0 2px rgba(46,125,50,0.25) !important;
}}

/* Multiselect tags (rot -> gruen) - BaseWeb Tag */
section[data-testid="stSidebar"] div[data-baseweb="tag"] {{
  background-color: {GREEN_MED} !important;
  color: {WHITE} !important;
  border: 0 !important;
  border-radius: 10px !important;
  font-weight: 800 !important;
}}
section[data-testid="stSidebar"] div[data-baseweb="tag"] * {{
  color: {WHITE} !important;
}}
section[data-testid="stSidebar"] div[data-baseweb="tag"] svg {{
  fill: {WHITE} !important;
}}

/* Alternative tag rendering in some versions */
section[data-testid="stSidebar"] div[data-testid="stMultiSelect"] span[role="button"],
section[data-testid="stSidebar"] div[data-testid="stMultiSelect"] div[role="button"] {{
  background-color: {GREEN_MED} !important;
  color: {WHITE} !important;
  border: 0 !important;
  border-radius: 10px !important;
  font-weight: 800 !important;
}}
section[data-testid="stSidebar"] div[data-testid="stMultiSelect"] span[role="button"] *,
section[data-testid="stSidebar"] div[data-testid="stMultiSelect"] div[role="button"] * {{
  color: {WHITE} !important;
}}

/* Fokus ruhig */
*:focus {{
  outline: none !important;
  box-shadow: none !important;
}}

/* Bild rechts: runde Ecken */
.img-right img {{
  border-radius: 14px;
  object-fit: cover !important;
}}
</style>
""",
    unsafe_allow_html=True,
)


# ------------------------------------------------------------
# Utilities
# ------------------------------------------------------------
def format_number_swiss(value) -> str:
    try:
        value = float(value)
    except Exception:
        return "0"
    return f"{int(round(value)): ,}".replace(",", "").replace(" ", "'")


def parse_swiss_number(text: str) -> int:
    if not text:
        return 0
    cleaned = str(text).replace("'", "").replace(" ", "").replace(",", "")
    try:
        return int(cleaned)
    except Exception:
        return 0


def lade_daten() -> pd.DataFrame:
    if not CSV_INPUT.exists():
        st.error(f"CSV-Datei nicht gefunden: {CSV_INPUT}")
        st.stop()

    df = pd.read_csv(CSV_INPUT, encoding="utf-8")

    fehler = validiere_eingabedaten(df)
    if fehler:
        for f in fehler:
            if "Warnung" in f:
                st.warning(f)
            else:
                st.error(f)
        kritische = [f for f in fehler if "Fehlende" in f or "Negative" in f]
        if kritische:
            st.stop()

    return df


def finde_gebaeude_bildpfad(gebaeude_id: str) -> Path | None:
    if not IMAGES_DIR.exists():
        return None
    gid = str(gebaeude_id).strip()
    kandidaten = [gid, gid.replace(" ", "_")]
    for base in kandidaten:
        for ext in ["jpg", "jpeg", "png", "webp"]:
            p = IMAGES_DIR / f"{base}.{ext}"
            if p.exists():
                return p
    return None


def zeige_bild_klein_rechts(gebaeude_id: str, width: int = 300, height: int = 200):
    """
    Zeigt Bild klein rechts (fixe Breite), nicht als volle Spaltenbreite.
    """
    p = finde_gebaeude_bildpfad(gebaeude_id)
    st.markdown('<div class="img-right">', unsafe_allow_html=True)
    if p:
        st.image(str(p), width=width)
    else:
        st.markdown(
            f"""
            <div style="
                width:{width}px;
                height:{height}px;
                border:1px dashed {GREEN_LIGHT};
                border-radius:14px;
                background:#F5F7F6;
                display:flex;
                align-items:center;
                justify-content:center;
                color:{GRAY_600};
                font-weight:800;">
                Kein Bild: {gebaeude_id}
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


# ------------------------------------------------------------
# Pages
# ------------------------------------------------------------
def page_portfolio_uebersicht(df: pd.DataFrame):
    st.header("▦ Portfolio-Uebersicht")

    aktuelles_jahr = int(df["jahr"].max())
    df_aktuell = berechne_emissionen(df[df["jahr"] == aktuelles_jahr].copy())

    stats = analysiere_portfolio(df_aktuell, KBOB_FAKTOREN)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Gebaeude", f"{stats['anzahl_gebaeude']}")
    with c2:
        st.metric("Gesamt-Emissionen", f"{stats['gesamt_emissionen_t_jahr']:.1f} t CO₂e/Jahr")
    with c3:
        st.metric("Ø pro Gebaeude", f"{stats['durchschnitt_emissionen_t_jahr']:.1f} t/Jahr")
    with c4:
        if stats.get("durchschnitt_emissionen_kg_m2") is not None:
            st.metric("Ø pro m²", f"{stats['durchschnitt_emissionen_kg_m2']:.1f} kg/m²")

    st.subheader("Heizungstypen-Verteilung")
    heiz_df = pd.DataFrame([{"Typ": k, "Anzahl": v} for k, v in stats.get("heizungstypen_verteilung", {}).items()])
    heiz_color_map = {t: COLOR_MAP_HEIZUNG.get(t, GREEN_MAIN) for t in heiz_df["Typ"].unique()}

    fig = px.pie(
        heiz_df,
        values="Anzahl",
        names="Typ",
        color="Typ",
        color_discrete_map=heiz_color_map,
        template=PLOTLY_TEMPLATE,
        title="Verteilung nach Heizungstyp",
    )
    fig.update_traces(textposition="inside", textinfo="percent+label", marker=dict(line=dict(color=WHITE, width=2)))
    fig.update_layout(margin=dict(t=60, b=20, l=20, r=20), legend_title_text="Heizung")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Gebaeude (Bilder)")
    cards_df = df_aktuell.sort_values("emissionen_gesamt_t", ascending=False).reset_index(drop=True)

    cols_per_row = 3
    total = len(cards_df)
    rows = (total + cols_per_row - 1) // cols_per_row
    idx = 0

    for _ in range(rows):
        cols = st.columns(cols_per_row)
        for col in cols:
            if idx >= total:
                break
            row = cards_df.iloc[idx]
            gid = row["gebaeude_id"]
            with col:
                with st.container(border=True):
                    p = finde_gebaeude_bildpfad(gid)
                    if p:
                        st.image(str(p), use_container_width=True)
                    else:
                        st.markdown(
                            f"""
                            <div style="
                                height:170px;
                                border:1px dashed {GREEN_LIGHT};
                                border-radius:14px;
                                background:#F5F7F6;
                                display:flex;
                                align-items:center;
                                justify-content:center;
                                color:{GRAY_600};
                                font-weight:800;">
                                Kein Bild: {gid}
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                    st.markdown(f"### {gid}")
                    st.write(f"**Heizung:** {row.get('heizung_typ', '-')}")
                    st.write(f"**Emissionen:** {row.get('emissionen_gesamt_t', 0):.1f} t CO₂e/Jahr")
            idx += 1


def page_gebaeude_analyse(df: pd.DataFrame):
    df_aktuell = berechne_emissionen(df[df["jahr"] == df["jahr"].max()].copy())

    gebaeude_id = st.sidebar.selectbox("Gebaeude auswaehlen", list(df_aktuell["gebaeude_id"].unique()))
    gebaeude = df_aktuell[df_aktuell["gebaeude_id"] == gebaeude_id].iloc[0]

    st.header(f"⌂ {gebaeude_id}")

    # ---- GENAU WIE GEWUENSCHT: Daten links, Bild klein rechts ----
    col_data, col_img = st.columns([4, 2], vertical_alignment="top")

    with col_data:
        st.write(f"**Heizung:** {gebaeude.get('heizung_typ', '-')}")
        if "baujahr" in gebaeude:
            try:
                st.write(f"**Baujahr:** {int(gebaeude['baujahr'])}")
            except Exception:
                pass

        st.write(f"**Verbrauch:** {format_number_swiss(gebaeude.get('jahresverbrauch_kwh', 0))} kWh/Jahr")

        if "flaeche_m2" in gebaeude and pd.notna(gebaeude["flaeche_m2"]):
            st.write(f"**Flaeche:** {format_number_swiss(gebaeude.get('flaeche_m2', 0))} m²")

        # Emissionen gleich wie der Rest (KEIN st.metric!)
        st.write(f"**Emissionen:** {gebaeude.get('emissionen_gesamt_t', 0):.1f} t CO₂e/Jahr")

    with col_img:
        zeige_bild_klein_rechts(gebaeude_id, width=320, height=220)

    st.markdown("---")

    # Benchmark
    if "flaeche_m2" in gebaeude and pd.notna(gebaeude["flaeche_m2"]) and gebaeude["flaeche_m2"] > 0:
        st.subheader("|—| Benchmark-Vergleich")
        standards_df = vergleiche_mit_standards(gebaeude, gebaeude.get("emissionen_gesamt_kg", 0))
        if isinstance(standards_df, pd.DataFrame) and not standards_df.empty:
            st.dataframe(standards_df, use_container_width=True)

    # Sanierungen
    st.header("✦ Sanierungsszenarien")

    szenarien = erstelle_alle_szenarien(gebaeude, KBOB_FAKTOREN)
    kombis = erstelle_kombinationsszenarien(gebaeude, KBOB_FAKTOREN)
    alle = szenarien + kombis

    szen_wirtschaft = [wirtschaftlichkeitsanalyse(san, gebaeude) for san in alle]
    szen_df = priorisiere_sanierungen(szen_wirtschaft, kriterium="score")

    # Sidebar Filter
    st.sidebar.subheader("Filter")
    if "kategorie" in szen_df.columns:
        kategorie_filter = st.sidebar.multiselect(
            "Kategorie",
            options=list(szen_df["kategorie"].unique()),
            default=list(szen_df["kategorie"].unique()),
        )
    else:
        kategorie_filter = []

    st.sidebar.markdown("### Max. Investition")
    if "max_investition_wert" not in st.session_state:
        st.session_state.max_investition_wert = 100000

    txt = st.sidebar.text_input("Betrag eingeben [CHF]:", value=format_number_swiss(st.session_state.max_investition_wert))
    parsed = parse_swiss_number(txt)
    if parsed != st.session_state.max_investition_wert:
        st.session_state.max_investition_wert = min(max(0, parsed), 2000000)
        st.rerun()

    slider = st.sidebar.slider(
        "Oder per Slider:",
        min_value=0,
        max_value=2000000,
        value=st.session_state.max_investition_wert,
        step=10000,
    )
    if slider != st.session_state.max_investition_wert:
        st.session_state.max_investition_wert = slider
        st.rerun()

    max_inv = st.session_state.max_investition_wert
    st.sidebar.success(f"**Gewaehlt: CHF {format_number_swiss(max_inv)}**")

    # Filter anwenden
    szen_f = szen_df.copy()
    if kategorie_filter and "kategorie" in szen_f.columns:
        szen_f = szen_f[szen_f["kategorie"].isin(kategorie_filter)]
    if "investition_netto_chf" in szen_f.columns:
        szen_f = szen_f[szen_f["investition_netto_chf"] <= max_inv]

    st.subheader("Top-3 Empfehlungen")
    for i, row in szen_f.head(3).iterrows():
        title = f"#{int(row.get('rang', i + 1))}: {row.get('name', 'Massnahme')}"
        with st.expander(title, expanded=(i == 0)):
            cc1, cc2, cc3 = st.columns(3)
            with cc1:
                st.write(f"**Investition (netto):** CHF {format_number_swiss(row.get('investition_netto_chf', 0))}")
                st.write(f"**Foerderung:** CHF {format_number_swiss(row.get('foerderung_chf', 0))}")
            with cc2:
                st.write(f"**CO₂-Reduktion:** {row.get('co2_einsparung_kg_jahr', 0) / 1000:.1f} t/Jahr")
                st.write(f"**Amortisation:** {row.get('amortisation_jahre', 0):.1f} Jahre")
            with cc3:
                st.write(f"**ROI:** {row.get('roi_prozent', 0):.1f}%")
                st.write(f"**NPV:** CHF {format_number_swiss(row.get('npv_chf', 0))}")

    st.subheader("Alle Szenarien im Vergleich")
    show_cols = [
        "rang",
        "name",
        "kategorie",
        "investition_netto_chf",
        "co2_einsparung_kg_jahr",
        "amortisation_jahre",
        "roi_prozent",
        "npv_chf",
        "prioritaets_score",
    ]
    show_cols = [c for c in show_cols if c in szen_f.columns]
    st.dataframe(szen_f[show_cols], use_container_width=True)

    if (
        "investition_netto_chf" in szen_f.columns
        and "co2_einsparung_kg_jahr" in szen_f.columns
        and len(szen_f) > 0
    ):
        st.subheader("Kosten-Nutzen-Analyse")
        cat_map = get_category_color_map(szen_f["kategorie"]) if "kategorie" in szen_f.columns else None

        fig = px.scatter(
            szen_f,
            x="investition_netto_chf",
            y="co2_einsparung_kg_jahr",
            size="prioritaets_score" if "prioritaets_score" in szen_f.columns else None,
            color="kategorie" if "kategorie" in szen_f.columns else None,
            color_discrete_map=cat_map,
            hover_data=["name", "amortisation_jahre", "roi_prozent"] if "name" in szen_f.columns else None,
            template=PLOTLY_TEMPLATE,
            title="Investition vs. CO₂-Reduktion (Groesse = Prioritaet)",
        )
        fig.update_traces(marker=dict(opacity=0.85))
        st.plotly_chart(fig, use_container_width=True)

    if len(szen_f) > 0:
        with st.expander("Sensitivitaetsanalyse (Top-Empfehlung)"):
            top = szen_f.iloc[0].to_dict()
            parameter = st.selectbox(
                "Szenario",
                ["energiepreis", "co2_abgabe", "foerderung"],
                format_func=lambda x: {
                    "energiepreis": "Energiepreis-Entwicklung",
                    "co2_abgabe": "CO₂-Abgabe",
                    "foerderung": "Foerdergelder",
                }[x],
            )
            sens_df = sensitivitaetsanalyse(top, gebaeude, parameter)

            fig2 = go.Figure()
            fig2.add_trace(
                go.Scatter(
                    x=sens_df["faktor"],
                    y=sens_df["amortisation_jahre"],
                    mode="lines+markers",
                    name="Amortisation",
                    line=dict(color=GREEN_MAIN, width=3),
                    marker=dict(size=7),
                )
            )
            if "npv_chf" in sens_df.columns:
                fig2.add_trace(
                    go.Scatter(
                        x=sens_df["faktor"],
                        y=sens_df["npv_chf"],
                        mode="lines+markers",
                        name="NPV",
                        line=dict(color=GREEN_DARK, width=3),
                        marker=dict(size=7),
                        yaxis="y2",
                    )
                )

            fig2.update_layout(
                title=f"Sensitivitaet: {parameter}",
                xaxis_title="Multiplikator (1.0 = Basis)",
                yaxis_title="Amortisation [Jahre]",
                yaxis2=dict(title="NPV [CHF]", overlaying="y", side="right"),
                hovermode="x unified",
                template=PLOTLY_TEMPLATE,
            )
            st.plotly_chart(fig2, use_container_width=True)
            st.dataframe(sens_df, use_container_width=True)


def page_vergleich(df: pd.DataFrame):
    st.header("≡ Gebaeude-Vergleich")
    df_aktuell = berechne_emissionen(df[df["jahr"] == df["jahr"].max()].copy())

    ausgewaehlt = st.multiselect(
        "Gebaeude auswaehlen (max. 5)",
        list(df_aktuell["gebaeude_id"].unique()),
        default=list(df_aktuell["gebaeude_id"].unique())[:3],
    )
    if not ausgewaehlt:
        st.info("Bitte mindestens ein Gebaeude auswaehlen.")
        return

    vdf = df_aktuell[df_aktuell["gebaeude_id"].isin(ausgewaehlt)].copy()

    st.subheader("Kennzahlen")
    cols = ["gebaeude_id", "heizung_typ", "jahresverbrauch_kwh", "strom_kwh_jahr", "emissionen_gesamt_t"]
    cols = [c for c in cols if c in vdf.columns]
    st.dataframe(vdf[cols], use_container_width=True)

    st.subheader("CO₂-Emissionen im Vergleich")
    heiz_map = {t: COLOR_MAP_HEIZUNG.get(t, GREEN_MAIN) for t in vdf["heizung_typ"].unique()}
    fig = px.bar(
        vdf,
        x="gebaeude_id",
        y="emissionen_gesamt_t",
        color="heizung_typ",
        color_discrete_map=heiz_map,
        template=PLOTLY_TEMPLATE,
        title="CO₂-Emissionen pro Gebaeude",
    )
    fig.update_layout(legend_title_text="Heizung")
    st.plotly_chart(fig, use_container_width=True)


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
def main():
    # Debug label, damit du sofort siehst, dass diese Datei laeuft
    st.sidebar.caption("APP VERSION: MAIN-REPLACE-OK")

    st.markdown('<div class="main-header">☘︎ CO₂ Portfolio Calculator</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">HSLU Digital Twin Programmieren | Nicola Beeli & Mattia Rohrer</div>',
        unsafe_allow_html=True,
    )

    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Seite auswaehlen", ["Portfolio-Uebersicht", "Gebaeude-Analyse", "Vergleich"])

    df = lade_daten()

    if page == "Portfolio-Uebersicht":
        page_portfolio_uebersicht(df)
    elif page == "Gebaeude-Analyse":
        page_gebaeude_analyse(df)
    else:
        page_vergleich(df)

    st.sidebar.markdown("---")
    st.sidebar.info("**HSLU Digital Twin Programmieren**  \nNicola Beeli & Mattia Rohrer")


if __name__ == "__main__":
    main()
