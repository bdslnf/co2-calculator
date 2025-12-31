"""
CO2 Portfolio Calculator – Streamlit Web App
HSLU Digital Twin Programmieren | Nicola Beeli & Mattia Rohrer

Fixes (gemäss Screenshot):
- Schweizer Schreibweise: ä ö ü (kein ae/oe/ue) und kein ß.
- CHF-Format: 1'000.- (Apostroph + .-) und saubere Synchronisation Textfeld <-> Slider.
- Sidebar-Farben: Rot/Blau konsequent auf Grün (Slider-Track, Radio, Chips/Tags, Links) via robuste CSS-Overrides.
- Gebäude-Analyse: Daten links als Textzeilen inkl. Emissionen, Bild klein rechts (fixe Breite), kein Full-Width-Bild oben.
- Bilder: data/images/<gebaeude_id>.(jpg|jpeg|png|webp)
- Keine Standort-Karte.

Start:
    streamlit run main.py
"""

from __future__ import annotations

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
# Design System (Grün)
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
# CSS: Sidebar Rot/Blau -> Grün (robust)
#   - Slider Track ist oft hardcodiert (rgb(255, 75, 75) = Streamlit-Rot)
#   - Wir überschreiben gezielt inline-Farben per style-contains Selektoren
# ------------------------------------------------------------
st.markdown(
    f"""
<style>
/* Base */
html, body, [data-testid="stAppViewContainer"] {{
  background: {WHITE} !important;
  color: {GRAY_900} !important;
}}
section[data-testid="stSidebar"] {{
  background: {GRAY_100} !important;
}}

/* Header */
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

/* Links */
a, a:visited {{ color: {GREEN_MAIN} !important; }}
a:hover {{ color: {GREEN_DARK} !important; }}

/* RADIO: Rot -> Grün (BaseWeb) */
section[data-testid="stSidebar"] [data-baseweb="radio"] input {{
  accent-color: {GREEN_MAIN} !important;
}}
/* Manche Versionen: SVG Kreis */
section[data-testid="stSidebar"] [data-baseweb="radio"] svg {{
  color: {GREEN_MAIN} !important;
  fill: {GREEN_MAIN} !important;
}}

/* MULTISELECT CHIPS: Rot -> Grün */
section[data-testid="stSidebar"] [data-baseweb="tag"] {{
  background-color: {GREEN_MED} !important;
  color: {WHITE} !important;
  border: 0 !important;
  border-radius: 10px !important;
  font-weight: 800 !important;
}}
section[data-testid="stSidebar"] [data-baseweb="tag"] * {{
  color: {WHITE} !important;
}}
section[data-testid="stSidebar"] [data-baseweb="tag"] svg {{
  fill: {WHITE} !important;
}}

/* SELECT: Fokus */
section[data-testid="stSidebar"] div[data-baseweb="select"] > div {{
  border-color: rgba(46,125,50,0.55) !important;
}}
section[data-testid="stSidebar"] div[data-baseweb="select"] > div:focus-within {{
  border-color: {GREEN_MAIN} !important;
  box-shadow: 0 0 0 2px rgba(46,125,50,0.25) !important;
}}

/* SLIDER: Thumb */
section[data-testid="stSidebar"] [data-baseweb="slider"] div[role="slider"] {{
  background: {GREEN_MAIN} !important;
  border-color: {GREEN_MAIN} !important;
}}

/* SLIDER: Track (überschreibt Streamlit-Rot rgb(255, 75, 75) und Blau) */
section[data-testid="stSidebar"] [data-baseweb="slider"] div[style*="rgb(255, 75, 75)"] {{
  background-color: {GREEN_MAIN} !important;
}}
section[data-testid="stSidebar"] [data-baseweb="slider"] div[style*="rgb(0, 104, 201)"] {{
  background-color: {GREEN_MAIN} !important;
}}
/* Generischer: falls inline background gesetzt ist */
section[data-testid="stSidebar"] [data-baseweb="slider"] div[style*="background"] {{
  /* NICHT alles grün faerben, nur wenn es wirklich ein Track ist */
}}
/* Slider Labels nicht rot */
section[data-testid="stSidebar"] div[data-testid="stSlider"] * {{
  color: {GRAY_900} !important;
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
# Formatierung (CH)
# ------------------------------------------------------------
def format_number_ch(value) -> str:
    """1000 -> 1'000"""
    try:
        x = float(value)
    except Exception:
        return "0"
    return f"{int(round(x)):,}".replace(",", "'")


def format_chf(value) -> str:
    """1000 -> 1'000.-"""
    return f"{format_number_ch(value)}.-"


def parse_chf_input(text: str) -> int:
    """
    Akzeptiert:
    1000
    1'000
    1'000.-
    CHF 1'000.-
    '2000000 (falls User vorn ein Apostroph tippt)
    """
    if not text:
        return 0
    s = str(text).strip()
    s = s.replace("CHF", "").replace("chf", "")
    s = s.replace(".-", "")
    s = s.replace("’", "'")
    s = s.replace(" ", "").replace(",", "")
    # Apostrophe (auch ein führendes) entfernen
    s = s.replace("'", "")
    try:
        return int(float(s))
    except Exception:
        return 0


# ------------------------------------------------------------
# Daten
# ------------------------------------------------------------
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


# ------------------------------------------------------------
# Bilder
# ------------------------------------------------------------
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


def zeige_bild_klein_rechts(gebaeude_id: str, width: int = 320, height: int = 220):
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
# Sidebar: Max. Investition – saubere Synchronisation
# ------------------------------------------------------------
MAX_INV_MIN = 0
MAX_INV_MAX = 2_000_000
MAX_INV_STEP = 10_000


def _ensure_state():
    if "max_inv" not in st.session_state:
        st.session_state.max_inv = 100_000
    if "max_inv_text" not in st.session_state:
        st.session_state.max_inv_text = format_chf(st.session_state.max_inv)
    if "max_inv_slider" not in st.session_state:
        st.session_state.max_inv_slider = int(st.session_state.max_inv)


def on_change_max_inv_text():
    v = parse_chf_input(st.session_state.max_inv_text)
    v = max(MAX_INV_MIN, min(MAX_INV_MAX, v))
    st.session_state.max_inv = v
    st.session_state.max_inv_slider = v
    # Re-formatieren, damit nie "'2000000" stehen bleibt
    st.session_state.max_inv_text = format_chf(v)


def on_change_max_inv_slider():
    v = int(st.session_state.max_inv_slider)
    v = max(MAX_INV_MIN, min(MAX_INV_MAX, v))
    st.session_state.max_inv = v
    st.session_state.max_inv_text = format_chf(v)


# ------------------------------------------------------------
# Pages
# ------------------------------------------------------------
def page_portfolio_uebersicht(df: pd.DataFrame):
    st.header("▦ Portfolio-Übersicht")

    aktuelles_jahr = int(df["jahr"].max())
    df_aktuell = berechne_emissionen(df[df["jahr"] == aktuelles_jahr].copy())
    stats = analysiere_portfolio(df_aktuell, KBOB_FAKTOREN)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Gebäude", f"{stats['anzahl_gebaeude']}")
    with c2:
        st.metric("Gesamt-Emissionen", f"{stats['gesamt_emissionen_t_jahr']:.1f} t CO₂e/Jahr")
    with c3:
        st.metric("Ø pro Gebäude", f"{stats['durchschnitt_emissionen_t_jahr']:.1f} t/Jahr")
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

    st.subheader("Gebäude (Bilder)")
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

    gebaeude_id = st.sidebar.selectbox("Gebäude auswählen", list(df_aktuell["gebaeude_id"].unique()))
    gebaeude = df_aktuell[df_aktuell["gebaeude_id"] == gebaeude_id].iloc[0]

    st.header(f"⌂ {gebaeude_id}")

    # Daten links, Bild klein rechts (wie im Screenshot gewünscht)
    col_data, col_img = st.columns([4, 2], vertical_alignment="top")

    with col_data:
        st.write(f"**Heizung:** {gebaeude.get('heizung_typ', '-')}")
        if "baujahr" in gebaeude:
            try:
                st.write(f"**Baujahr:** {int(gebaeude['baujahr'])}")
            except Exception:
                pass

        st.write(f"**Verbrauch:** {format_number_ch(gebaeude.get('jahresverbrauch_kwh', 0))} kWh/Jahr")

        if "flaeche_m2" in gebaeude and pd.notna(gebaeude["flaeche_m2"]):
            st.write(f"**Fläche:** {format_number_ch(gebaeude.get('flaeche_m2', 0))} m²")

        st.write(f"**Emissionen:** {gebaeude.get('emissionen_gesamt_t', 0):.1f} t CO₂e/Jahr")

    with col_img:
        zeige_bild_klein_rechts(gebaeude_id, width=340, height=220)

    st.markdown("---")

    # Benchmark
    if "flaeche_m2" in gebaeude and pd.notna(gebaeude["flaeche_m2"]) and gebaeude["flaeche_m2"] > 0:
        st.subheader("|—| Benchmark-Vergleich")
        standards_df = vergleiche_mit_standards(gebaeude, gebaeude.get("emissionen_gesamt_kg", 0))
        if isinstance(standards_df, pd.DataFrame) and not standards_df.empty:
            st.dataframe(standards_df, use_container_width=True)

    # Sanierungsszenarien
    st.header("✦ Sanierungsszenarien")

    szenarien = erstelle_alle_szenarien(gebaeude, KBOB_FAKTOREN)
    kombis = erstelle_kombinationsszenarien(gebaeude, KBOB_FAKTOREN)
    alle = szenarien + kombis

    szen_wirtschaft = [wirtschaftlichkeitsanalyse(san, gebaeude) for san in alle]
    szen_df = priorisiere_sanierungen(szen_wirtschaft, kriterium="score")

    # Filter
    st.sidebar.subheader("Filter")
    if "kategorie" in szen_df.columns:
        kategorie_filter = st.sidebar.multiselect(
            "Kategorie",
            options=list(szen_df["kategorie"].unique()),
            default=list(szen_df["kategorie"].unique()),
        )
    else:
        kategorie_filter = []

    # Max. Investition (Text <-> Slider synchron)
    st.sidebar.markdown("### Max. Investition")
    _ensure_state()

    st.sidebar.text_input(
        "Betrag eingeben [CHF]:",
        key="max_inv_text",
        on_change=on_change_max_inv_text,
        help="Beispiele: 1000, 1'000, 1'000.-, CHF 1'000.-",
    )

    st.sidebar.slider(
        "Oder per Slider:",
        min_value=MAX_INV_MIN,
        max_value=MAX_INV_MAX,
        value=int(st.session_state.max_inv_slider),
        step=MAX_INV_STEP,
        key="max_inv_slider",
        on_change=on_change_max_inv_slider,
    )

    max_inv = int(st.session_state.max_inv)
    st.sidebar.success(f"**Gewählt: CHF {format_chf(max_inv)}**")
    st.sidebar.caption(f"Bereich: 0 - {format_chf(MAX_INV_MAX)}")

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
                st.write(f"**Investition (netto):** CHF {format_chf(row.get('investition_netto_chf', 0))}")
                st.write(f"**Förderung:** CHF {format_chf(row.get('foerderung_chf', 0))}")
            with cc2:
                st.write(f"**CO₂-Reduktion:** {row.get('co2_einsparung_kg_jahr', 0) / 1000:.1f} t/Jahr")
                st.write(f"**Amortisation:** {row.get('amortisation_jahre', 0):.1f} Jahre")
            with cc3:
                st.write(f"**ROI:** {row.get('roi_prozent', 0):.1f}%")
                st.write(f"**NPV:** CHF {format_chf(row.get('npv_chf', 0))}")

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

    # Kosten-Nutzen
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
            title="Investition vs. CO₂-Reduktion (Grösse = Priorität)",
        )
        fig.update_traces(marker=dict(opacity=0.85))
        st.plotly_chart(fig, use_container_width=True)

    # Sensitivität
    if len(szen_f) > 0:
        with st.expander("Sensitivitätsanalyse (Top-Empfehlung)"):
            top = szen_f.iloc[0].to_dict()

            parameter = st.selectbox(
                "Szenario",
                ["energiepreis", "co2_abgabe", "foerderung"],
                format_func=lambda x: {
                    "energiepreis": "Energiepreis-Entwicklung",
                    "co2_abgabe": "CO₂-Abgabe",
                    "foerderung": "Fördergelder",
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
                title=f"Sensitivität: {parameter}",
                xaxis_title="Multiplikator (1.0 = Basis)",
                yaxis_title="Amortisation [Jahre]",
                yaxis2=dict(title="NPV [CHF]", overlaying="y", side="right"),
                hovermode="x unified",
                template=PLOTLY_TEMPLATE,
            )
            st.plotly_chart(fig2, use_container_width=True)
            st.dataframe(sens_df, use_container_width=True)


def page_vergleich(df: pd.DataFrame):
    st.header("≡ Gebäude-Vergleich")
    df_aktuell = berechne_emissionen(df[df["jahr"] == df["jahr"].max()].copy())

    ausgewaehlt = st.multiselect(
        "Gebäude auswählen (max. 5)",
        list(df_aktuell["gebaeude_id"].unique()),
        default=list(df_aktuell["gebaeude_id"].unique())[:3],
    )
    if not ausgewaehlt:
        st.info("Bitte mindestens ein Gebäude auswählen.")
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
        title="CO₂-Emissionen pro Gebäude",
    )
    fig.update_layout(legend_title_text="Heizung")
    st.plotly_chart(fig, use_container_width=True)


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
def main():
    st.markdown('<div class="main-header">☘︎ CO₂ Portfolio Calculator</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">HSLU Digital Twin Programmieren | Nicola Beeli & Mattia Rohrer</div>',
        unsafe_allow_html=True,
    )

    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Seite auswählen", ["Portfolio-Übersicht", "Gebäude-Analyse", "Vergleich"])

    df = lade_daten()

    if page == "Portfolio-Übersicht":
        page_portfolio_uebersicht(df)
    elif page == "Gebäude-Analyse":
        page_gebaeude_analyse(df)
    else:
        page_vergleich(df)

    st.sidebar.markdown("---")
    st.sidebar.info("**HSLU Digital Twin Programmieren**  \nNicola Beeli & Mattia Rohrer")


if __name__ == "__main__":
    main()
