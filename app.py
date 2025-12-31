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


# -----------------------------
# Pfade
# -----------------------------
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
CSV_INPUT = DATA_DIR / "beispiel_emissionen_mit_jahr.csv"
IMAGES_DIR = DATA_DIR / "images"

# -----------------------------
# Farben (nur Gruentoene)
# -----------------------------
GREEN_MAIN = "#2E7D32"
GREEN_MED = "#66BB6A"
GREEN_DARK = "#1B5E20"
GREEN_LIGHT = "#A5D6A7"

WHITE = "#FFFFFF"
GRAY_900 = "#263238"
GRAY_600 = "#607D8B"
GRAY_100 = "#ECEFF1"

PLOTLY_TEMPLATE = "simple_white"

# Plotly Defaults: keine bunten Farben mehr
px.defaults.template = PLOTLY_TEMPLATE
px.defaults.color_discrete_sequence = [GREEN_MAIN, GREEN_DARK, GREEN_MED, GREEN_LIGHT]

st.set_page_config(page_title="CO₂ Portfolio Calculator", page_icon="☘︎", layout="wide")

# -----------------------------
# CSS (Sidebar: Radio, Chips, Slider, Alerts)
# -----------------------------
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

/* Radio (Seitenwahl) */
input[type="radio"] {{
  accent-color: {GREEN_MAIN} !important;
}}

/* Multiselect Chips (global, nicht nur Sidebar) */
[data-baseweb="tag"] {{
  background-color: {GREEN_MED} !important;
  color: white !important;
  border: 0 !important;
  border-radius: 10px !important;
  font-weight: 800 !important;
}}
[data-baseweb="tag"] * {{ color: white !important; }}
[data-baseweb="tag"] svg {{ fill: white !important; }}

/* Slider Thumb */
[data-baseweb="slider"] div[role="slider"] {{
  background: {GREEN_MAIN} !important;
  border-color: {GREEN_MAIN} !important;
}}

/* Slider Track (rot/blau) -> gruen (sehr breit gefasst) */
[data-baseweb="slider"] div[style*="255, 75, 75"],
[data-baseweb="slider"] div[style*="rgb(255, 75, 75)"],
[data-baseweb="slider"] div[style*="#ff4b4b"],
[data-baseweb="slider"] div[style*="0, 104, 201"],
[data-baseweb="slider"] div[style*="rgb(0, 104, 201)"],
[data-baseweb="slider"] div[style*="#0068c9"] {{
  background-color: {GREEN_MAIN} !important;
  border-color: {GREEN_MAIN} !important;
}}

/* Alert Box (Info/Warning/Error) -> gruen (global + sidebar) */
[data-testid="stAlert"] {{
  background: #E8F5E9 !important;
  border: 1px solid {GREEN_LIGHT} !important;
  color: {GREEN_DARK} !important;
}}
[data-testid="stAlert"] * {{
  color: {GREEN_DARK} !important;
}}
[data-testid="stAlert"] svg {{
  fill: {GREEN_DARK} !important;
}}

/* Bild rechts */
.img-right img {{
  border-radius: 14px;
  object-fit: cover !important;
}}
</style>
""",
    unsafe_allow_html=True,
)

# -----------------------------
# Format Helfer (Schweiz)
# -----------------------------
def format_number_ch(x) -> str:
    if pd.isna(x):
        return "0"
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


def fmt_float(x, d=2) -> str:
    if pd.isna(x):
        return "-"
    try:
        return f"{float(x):.{d}f}"
    except Exception:
        return "-"


# -----------------------------
# Daten
# -----------------------------
def load_data() -> pd.DataFrame:
    df = pd.read_csv(CSV_INPUT, encoding="utf-8")
    msgs = validiere_eingabedaten(df)
    for m in msgs:
        if "Warnung" in m:
            st.sidebar.warning(m)
        else:
            st.sidebar.error(m)
    return df


# -----------------------------
# Bild Matching (Bahnhofstr <-> Bahnhofstrasse etc.)
# -----------------------------
def _canon_street(s: str) -> str:
    s = str(s).lower().strip()
    # Normalisierung fuer Strasse-Abkuerzungen
    s = s.replace("straße", "strasse")
    s = s.replace("str.", "str")
    s = s.replace("strasse", "str")
    # alles ausser alnum entfernen
    s = "".join(ch for ch in s if ch.isalnum())
    return s


def find_image_path(gebaeude_id: str) -> Path | None:
    if not IMAGES_DIR.exists():
        return None

    gid_key = _canon_street(gebaeude_id)

    files = [p for p in IMAGES_DIR.glob("*.*") if p.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]]
    if not files:
        return None

    # 1) exakter match auf canonical key
    for p in files:
        if _canon_street(p.stem) == gid_key:
            return p

    # 2) token match: gleicher Zahlenblock + hoher String-Overlap
    #    (z.B. MFH Bahnhofstrasse 5 <-> MFH_Bahnhofstr_5)
    def digits(x: str) -> str:
        return "".join(ch for ch in x if ch.isdigit())

    gid_digits = digits(gid_key)

    best = None
    best_score = -1
    for p in files:
        stem_key = _canon_street(p.stem)

        # gleiche Hausnummer ist wichtig
        if gid_digits and digits(stem_key) and gid_digits != digits(stem_key):
            continue

        # overlap score (sehr simpel, aber robust genug)
        common = set(gid_key) & set(stem_key)
        score = len(common) + (5 if gid_digits and gid_digits == digits(stem_key) else 0)

        if score > best_score:
            best_score = score
            best = p

    return best


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
                border:1px dashed {GREEN_LIGHT};border-radius:14px;
                background:#F5F7F6;display:flex;
                align-items:center;justify-content:center;
                color:{GRAY_600};font-weight:800;">
                Kein Bild
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


# -----------------------------
# Seiten: Portfolio
# -----------------------------
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

    st.subheader("Heizungstypen-Verteilung")
    heiz_df = pd.DataFrame(
        [{"Typ": k, "Anzahl": v} for k, v in stats.get("heizungstypen_verteilung", {}).items()]
    )
    if not heiz_df.empty:
        # bewusst monochrom (Gruen)
        fig = px.pie(
            heiz_df,
            values="Anzahl",
            names="Typ",
            template=PLOTLY_TEMPLATE,
        )
        fig.update_traces(marker=dict(colors=[GREEN_MAIN, GREEN_DARK, GREEN_MED, GREEN_LIGHT]))
        fig.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Gebäude (Bilder)")
    cards_df = df_now.sort_values("emissionen_gesamt_t", ascending=False).reset_index(drop=True)

    cols_per_row = 3
    total = len(cards_df)
    rows = (total + cols_per_row - 1) // cols_per_row
    idx = 0

    for _ in range(rows):
        cols = st.columns(cols_per_row)
        for col in cols:
            if idx >= total:
                break
            r = cards_df.iloc[idx]
            gid = r["gebaeude_id"]
            with col:
                with st.container(border=True):
                    p = find_image_path(gid)
                    if p:
                        st.image(str(p), use_container_width=True)
                    else:
                        st.markdown(
                            f"""
                            <div style="
                                height:170px;border:1px dashed {GREEN_LIGHT};
                                border-radius:14px;background:#F5F7F6;
                                display:flex;align-items:center;justify-content:center;
                                color:{GRAY_600};font-weight:800;">
                                Kein Bild
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    st.markdown(f"### {gid}")
                    st.write(f"**Heizung:** {r.get('heizung_typ', '-')}")
                    st.write(f"**Emissionen:** {float(r.get('emissionen_gesamt_t', 0)):.1f} t CO₂e/Jahr")
            idx += 1


# -----------------------------
# Seiten: Gebäude-Analyse
# -----------------------------
def page_gebaeude(df: pd.DataFrame):
    df_now = berechne_emissionen(df[df["jahr"] == df["jahr"].max()].copy())

    gebaeude_id = st.sidebar.selectbox("Gebäude auswählen", list(df_now["gebaeude_id"].unique()))
    g = df_now[df_now["gebaeude_id"] == gebaeude_id].iloc[0]

    st.header(f"⌂ {gebaeude_id}")

    left, right = st.columns([4, 2], vertical_alignment="top")

    with left:
        st.write(f"**Heizung:** {g.get('heizung_typ', '-')}")
        if "baujahr" in g and pd.notna(g["baujahr"]):
            st.write(f"**Baujahr:** {int(g['baujahr'])}")
        st.write(f"**Verbrauch:** {format_number_ch(g.get('jahresverbrauch_kwh', 0))} kWh/Jahr")
        if "flaeche_m2" in g and pd.notna(g["flaeche_m2"]):
            st.write(f"**Fläche:** {format_number_ch(g.get('flaeche_m2', 0))} m²")
        st.write(f"**Emissionen:** {float(g.get('emissionen_gesamt_t', 0)):.1f} t CO₂e/Jahr")

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
    if "kategorie" in szen_df.columns:
        kategorie_filter = st.sidebar.multiselect(
            "Kategorie",
            list(szen_df["kategorie"].unique()),
            list(szen_df["kategorie"].unique()),
        )
    else:
        kategorie_filter = []

    # Max. Investition (Text + Slider synchron)
    if "max_inv" not in st.session_state:
        st.session_state.max_inv = 100_000

    st.sidebar.markdown("### Max. Investition")
    txt = st.sidebar.text_input("Betrag eingeben [CHF]:", value=format_chf(st.session_state.max_inv))
    st.session_state.max_inv = max(0, min(2_000_000, parse_chf(txt)))

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
            c2.write(f"**CO₂-Reduktion:** {float(row.get('co2_einsparung_kg_jahr', 0)) / 1000:.1f} t/Jahr")
            c2.write(f"**Amortisation:** {fmt_float(row.get('amortisation_jahre', 0), 2)} Jahre")
            c3.write(f"**ROI:** {fmt_float(row.get('roi_prozent', 0), 1)}%")
            c3.write(f"**NPV:** CHF {format_chf(row.get('npv_chf', 0))}")

    st.subheader("Alle Szenarien")
    show_cols = [c for c in ["rang", "name", "kategorie", "investition_netto_chf", "amortisation_jahre", "roi_prozent", "npv_chf"] if c in f.columns]
    show_df = f[show_cols].copy()

    if "investition_netto_chf" in show_df.columns:
        show_df["investition_netto_chf"] = show_df["investition_netto_chf"].apply(lambda v: f"CHF {format_chf(v)}")
    if "npv_chf" in show_df.columns:
        show_df["npv_chf"] = show_df["npv_chf"].apply(lambda v: f"CHF {format_chf(v)}")
    if "amortisation_jahre" in show_df.columns:
        show_df["amortisation_jahre"] = show_df["amortisation_jahre"].apply(lambda v: fmt_float(v, 2))
    if "roi_prozent" in show_df.columns:
        show_df["roi_prozent"] = show_df["roi_prozent"].apply(lambda v: fmt_float(v, 1))

    st.dataframe(show_df, use_container_width=True)

    # Sensitivitaet (Plot + Tabelle: gruen + sauber formatiert)
    if len(f) > 0:
        with st.expander("Sensitivitätsanalyse (Top-Empfehlung)"):
            top = f.iloc[0].to_dict()
            parameter = st.selectbox(
                "Szenario",
                ["energiepreis", "co2_abgabe", "foerderung"],
                format_func=lambda x: {"energiepreis": "Energiepreis", "co2_abgabe": "CO₂-Abgabe", "foerderung": "Förderung"}[x],
            )

            sens_df = sensitivitaetsanalyse(top, g, parameter)

            # Plot: nachtraeglich ALLE Traces gruen zwingen (auch wenn Funktion intern andere Farben setzt)
            fig2 = px.line(sens_df, x="faktor", y="amortisation_jahre", markers=True)
            fig2.update_traces(line=dict(color=GREEN_MAIN, width=3), marker=dict(color=GREEN_MAIN, size=8))
            fig2.update_layout(template=PLOTLY_TEMPLATE, xaxis_title="Faktor", yaxis_title="Amortisation (Jahre)")
            st.plotly_chart(fig2, use_container_width=True)

            # Tabelle: einheitliche Stellen
            sens_show = sens_df.copy()
            if "faktor" in sens_show.columns:
                sens_show["faktor"] = sens_show["faktor"].apply(lambda v: fmt_float(v, 1))
            if "amortisation_jahre" in sens_show.columns:
                sens_show["amortisation_jahre"] = sens_show["amortisation_jahre"].apply(lambda v: fmt_float(v, 2))
            if "roi_prozent" in sens_show.columns:
                sens_show["roi_prozent"] = sens_show["roi_prozent"].apply(lambda v: fmt_float(v, 1))
            if "npv_chf" in sens_show.columns:
                sens_show["npv_chf"] = sens_show["npv_chf"].apply(lambda v: f"CHF {format_chf(v)}" if pd.notna(v) else "-")
            if "jaehrliche_einsparung_chf" in sens_show.columns:
                sens_show["jaehrliche_einsparung_chf"] = sens_show["jaehrliche_einsparung_chf"].apply(lambda v: f"CHF {format_chf(v)}" if pd.notna(v) else "-")
            st.dataframe(sens_show, use_container_width=True)


# -----------------------------
# Seiten: Vergleich
# -----------------------------
def page_vergleich(df: pd.DataFrame):
    st.header("≡ Gebäude-Vergleich")

    df_now = berechne_emissionen(df[df["jahr"] == df["jahr"].max()].copy())

    all_ids = list(df_now["gebaeude_id"].unique())
    selected = st.multiselect("Gebäude auswählen (max. 5)", all_ids, default=all_ids[:3])
    if len(selected) > 5:
        st.warning("Bitte maximal 5 Gebäude auswählen.")
        selected = selected[:5]
    if not selected:
        st.info("Bitte mindestens ein Gebäude auswählen.")
        return

    vdf = df_now[df_now["gebaeude_id"].isin(selected)].copy()

    # pro m² Kennzahlen
    if "flaeche_m2" in vdf.columns:
        vdf["emissionen_pro_m2"] = vdf.apply(
            lambda r: (r.get("emissionen_gesamt_t", 0) / r["flaeche_m2"]) if pd.notna(r.get("flaeche_m2")) and r["flaeche_m2"] else None,
            axis=1,
        )
        vdf["verbrauch_pro_m2"] = vdf.apply(
            lambda r: (r.get("jahresverbrauch_kwh", 0) / r["flaeche_m2"]) if pd.notna(r.get("flaeche_m2")) and r["flaeche_m2"] else None,
            axis=1,
        )
    else:
        vdf["emissionen_pro_m2"] = None
        vdf["verbrauch_pro_m2"] = None

    c1, c2, c3 = st.columns([2, 2, 2])
    with c1:
        metric = st.selectbox(
            "Kennzahl",
            [
                "Emissionen (t CO₂e/Jahr)",
                "Verbrauch (kWh/Jahr)",
                "Emissionen pro m² (t CO₂e/m²)",
                "Verbrauch pro m² (kWh/m²)",
            ],
        )
    with c2:
        sort_on = st.selectbox("Sortieren", ["keine", "aufsteigend", "absteigend"])
    with c3:
        normalize = st.checkbox("Normalisieren (0–1)", value=False)

    if metric == "Emissionen (t CO₂e/Jahr)":
        y_col, y_title = "emissionen_gesamt_t", "t CO₂e/Jahr"
        y_fmt = lambda x: fmt_float(x, 2)
    elif metric == "Verbrauch (kWh/Jahr)":
        y_col, y_title = "jahresverbrauch_kwh", "kWh/Jahr"
        y_fmt = lambda x: format_number_ch(x) if pd.notna(x) else "-"
    elif metric == "Emissionen pro m² (t CO₂e/m²)":
        y_col, y_title = "emissionen_pro_m2", "t CO₂e/m²"
        y_fmt = lambda x: fmt_float(x, 4)
    else:
        y_col, y_title = "verbrauch_pro_m2", "kWh/m²"
        y_fmt = lambda x: fmt_float(x, 1)

    plot_df = vdf[["gebaeude_id", y_col]].copy()
    if sort_on != "keine":
        plot_df = plot_df.sort_values(y_col, ascending=(sort_on == "aufsteigend"))

    if normalize:
        vals = plot_df[y_col].astype(float)
        vmin, vmax = vals.min(), vals.max()
        plot_df["y_plot"] = (vals - vmin) / (vmax - vmin) if pd.notna(vmin) and pd.notna(vmax) and vmax != vmin else 0.0
        y_plot_col = "y_plot"
        y_axis_title = "normalisiert (0–1)"
    else:
        y_plot_col = y_col
        y_axis_title = y_title

    # Tabelle (einheitlich formatiert)
    tdf = vdf[["gebaeude_id", "heizung_typ", "jahresverbrauch_kwh", "emissionen_gesamt_t", "flaeche_m2", "verbrauch_pro_m2", "emissionen_pro_m2"]].copy()
    tdf["jahresverbrauch_kwh"] = tdf["jahresverbrauch_kwh"].apply(lambda x: format_number_ch(x) if pd.notna(x) else "-")
    tdf["emissionen_gesamt_t"] = tdf["emissionen_gesamt_t"].apply(lambda x: fmt_float(x, 2))
    if "flaeche_m2" in tdf.columns:
        tdf["flaeche_m2"] = tdf["flaeche_m2"].apply(lambda x: format_number_ch(x) if pd.notna(x) else "-")
    tdf["verbrauch_pro_m2"] = tdf["verbrauch_pro_m2"].apply(lambda x: fmt_float(x, 1))
    tdf["emissionen_pro_m2"] = tdf["emissionen_pro_m2"].apply(lambda x: fmt_float(x, 4))
    st.dataframe(tdf, use_container_width=True)

    # Balkenplot: bewusst EIN gruen (keine Legende, keine Heizung-Farben)
    st.subheader("Vergleich")
    fig = px.bar(
        plot_df,
        x="gebaeude_id",
        y=y_plot_col,
        template=PLOTLY_TEMPLATE,
        title=metric,
    )
    fig.update_traces(marker_color=GREEN_MAIN)
    fig.update_layout(xaxis_title="", yaxis_title=y_axis_title, showlegend=False, bargap=0.25)
    st.plotly_chart(fig, use_container_width=True)

    # Delta zum besten Gebäude (min = besser)
    st.subheader("Delta zum besten Gebäude")
    base = vdf[["gebaeude_id", y_col]].dropna().copy()
    if base.empty:
        st.info("Für diese Kennzahl fehlen Werte.")
    else:
        best_val = base[y_col].min()
        best_id = base.loc[base[y_col].idxmin(), "gebaeude_id"]

        delta_df = base.copy()
        delta_df["wert"] = delta_df[y_col].apply(y_fmt)
        delta_df["delta_prozent"] = ((delta_df[y_col] - best_val) / best_val * 100) if best_val != 0 else 0.0
        delta_df["delta_prozent"] = delta_df["delta_prozent"].apply(lambda x: f"{x:+.1f}%")
        delta_df = delta_df.sort_values(y_col, ascending=True)

        st.caption(f"Bestes Gebäude: **{best_id}** ({y_fmt(best_val)} {y_title})")
        st.dataframe(delta_df[["gebaeude_id", "wert", "delta_prozent"]], use_container_width=True)

    # Spider / Radar (3–4 Kennzahlen)
    st.subheader("Spider/Radar (normalisiert)")

    radar_metrics = [
        ("Emissionen", "emissionen_gesamt_t"),
        ("Verbrauch", "jahresverbrauch_kwh"),
        ("Emissionen pro m²", "emissionen_pro_m2"),
        ("Verbrauch pro m²", "verbrauch_pro_m2"),
    ]

    # Investition nur wenn vorhanden
    invest_cols = [c for c in ["investition_netto_chf", "investition_chf", "investition"] if c in vdf.columns]
    if invest_cols:
        radar_metrics.append(("Investition", invest_cols[0]))

    options = [n for n, _ in radar_metrics]
    chosen = st.multiselect("Radar-Kennzahlen (3–4)", options, default=options[:4])
    if len(chosen) < 3:
        st.info("Bitte mindestens 3 Kennzahlen auswählen.")
        return
    chosen = chosen[:4]

    chosen_cols = [c for n, c in radar_metrics if n in chosen]
    chosen_names = [n for n, c in radar_metrics if n in chosen]

    radar_df = vdf[["gebaeude_id"] + chosen_cols].copy()

    # kleiner = besser -> invertieren, damit höher = besser
    invert_cols = set(["emissionen_gesamt_t", "jahresverbrauch_kwh", "emissionen_pro_m2", "verbrauch_pro_m2"] + invest_cols)

    for col in chosen_cols:
        vals = radar_df[col].astype(float)
        vmin, vmax = vals.min(), vals.max()
        if pd.isna(vmin) or pd.isna(vmax) or vmax == vmin:
            radar_df[col] = 0.0
        else:
            norm = (vals - vmin) / (vmax - vmin)
            radar_df[col] = (1 - norm) if col in invert_cols else norm

    fig_r = go.Figure()
    for gid in radar_df["gebaeude_id"].tolist():
        r_vals = radar_df.loc[radar_df["gebaeude_id"] == gid, chosen_cols].iloc[0].tolist()
        r_vals = r_vals + [r_vals[0]]
        theta = chosen_names + [chosen_names[0]]

        fig_r.add_trace(
            go.Scatterpolar(
                r=r_vals,
                theta=theta,
                fill="toself",
                name=gid,
            )
        )

    fig_r.update_layout(
        template=PLOTLY_TEMPLATE,
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        title="Radar: 1.0 = besser (normalisiert)",
    )
    st.plotly_chart(fig_r, use_container_width=True)


# -----------------------------
# Main
# -----------------------------
def main():
    st.markdown('<div class="main-header">☘︎ CO₂ Portfolio Calculator</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">HSLU Digital Twin Programmieren | Nicola Beeli & Mattia Rohrer</div>',
        unsafe_allow_html=True,
    )

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
