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
GREEN_LIGHT = "#A5D6A7"

WHITE = "#FFFFFF"
GRAY_900 = "#263238"
GRAY_700 = "#455A64"
GRAY_600 = "#607D8B"
GRAY_100 = "#ECEFF1"

PLOTLY_TEMPLATE = "simple_white"

COLOR_MAP_HEIZUNG = {
    "Gas": GREEN_DARK,
    "Fernwärme": GREEN_MAIN,
    "Wärmepumpe": GREEN_MED,
    "Öl": GREEN_LIGHT,
    "Pellets": GREEN_MED,
    "Solar": GREEN_LIGHT,
}

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

/* Radio (Seitenwahl) */
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

/* Slider Thumb */
section[data-testid="stSidebar"] [data-baseweb="slider"] div[role="slider"] {{
  background: {GREEN_MAIN} !important;
  border-color: {GREEN_MAIN} !important;
}}

/* Slider Track (Streamlit rot/blau) -> gruen (sehr breit) */
section[data-testid="stSidebar"] [data-baseweb="slider"] div[style*="255, 75, 75"],
section[data-testid="stSidebar"] [data-baseweb="slider"] div[style*="rgb(255, 75, 75)"],
section[data-testid="stSidebar"] [data-baseweb="slider"] div[style*="#ff4b4b"],
section[data-testid="stSidebar"] [data-baseweb="slider"] div[style*="0, 104, 201"],
section[data-testid="stSidebar"] [data-baseweb="slider"] div[style*="rgb(0, 104, 201)"],
section[data-testid="stSidebar"] [data-baseweb="slider"] div[style*="#0068c9"] {{
  background-color: {GREEN_MAIN} !important;
  border-color: {GREEN_MAIN} !important;
}}

/* Slider Value (rot) -> neutral */
section[data-testid="stSidebar"] div[data-testid="stSlider"] * {{
  color: {GRAY_900} !important;
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
    if not heiz_df.empty:
        fig = px.pie(
            heiz_df,
            values="Anzahl",
            names="Typ",
            color="Typ",
            color_discrete_map={t: COLOR_MAP_HEIZUNG.get(t, GREEN_MAIN) for t in heiz_df["Typ"].unique()},
            template=PLOTLY_TEMPLATE,
        )
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
                    st.write(f"**Emissionen:** {r.get('emissionen_gesamt_t', 0):.1f} t CO₂e/Jahr")
            idx += 1


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

    txt = st.sidebar.text_input("Betrag eingeben [CHF]:", value=format_chf(st.session_state.max_inv))
    val = parse_chf(txt)
    val = max(0, min(2_000_000, val))
    st.session_state.max_inv = val

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
    show_cols = [
        c
        for c in [
            "rang",
            "name",
            "kategorie",
            "investition_netto_chf",
            "amortisation_jahre",
            "roi_prozent",
            "npv_chf",
        ]
        if c in f.columns
    ]
    st.dataframe(f[show_cols], use_container_width=True)

    if len(f) > 0:
        with st.expander("Sensitivitätsanalyse (Top-Empfehlung)"):
            top = f.iloc[0].to_dict()
            parameter = st.selectbox(
                "Szenario",
                ["energiepreis", "co2_abgabe", "foerderung"],
                format_func=lambda x: {"energiepreis": "Energiepreis", "co2_abgabe": "CO₂-Abgabe", "foerderung": "Förderung"}[
                    x
                ],
            )
            sens_df = sensitivitaetsanalyse(top, g, parameter)
            fig2 = go.Figure()
            fig2.add_trace(
                go.Scatter(x=sens_df["faktor"], y=sens_df["amortisation_jahre"], mode="lines+markers", name="Amortisation")
            )
            st.plotly_chart(fig2, use_container_width=True)
            st.dataframe(sens_df, use_container_width=True)


def page_vergleich(df: pd.DataFrame):
    st.header("≡ Gebäude-Vergleich")

    df_now = berechne_emissionen(df[df["jahr"] == df["jahr"].max()].copy())

    # Auswahl (max. 5)
    all_ids = list(df_now["gebaeude_id"].unique())
    selected = st.multiselect(
        "Gebäude auswählen (max. 5)",
        all_ids,
        default=all_ids[:3],
    )
    if len(selected) > 5:
        st.warning("Bitte maximal 5 Gebäude auswählen.")
        selected = selected[:5]
    if not selected:
        st.info("Bitte mindestens ein Gebäude auswählen.")
        return

    vdf = df_now[df_now["gebaeude_id"].isin(selected)].copy()

    # Ableitungen
    if "flaeche_m2" in vdf.columns:
        vdf["emissionen_pro_m2"] = vdf.apply(
            lambda r: (r.get("emissionen_gesamt_t", 0) / r["flaeche_m2"])
            if pd.notna(r.get("flaeche_m2")) and r["flaeche_m2"]
            else None,
            axis=1,
        )
        vdf["verbrauch_pro_m2"] = vdf.apply(
            lambda r: (r.get("jahresverbrauch_kwh", 0) / r["flaeche_m2"])
            if pd.notna(r.get("flaeche_m2")) and r["flaeche_m2"]
            else None,
            axis=1,
        )
    else:
        vdf["emissionen_pro_m2"] = None
        vdf["verbrauch_pro_m2"] = None

    # Kennzahlenwahl (Balken)
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
        y_col = "emissionen_gesamt_t"
        y_title = "t CO₂e/Jahr"
        y_fmt = lambda x: f"{x:.2f}" if pd.notna(x) else "-"
        better = "min"
    elif metric == "Verbrauch (kWh/Jahr)":
        y_col = "jahresverbrauch_kwh"
        y_title = "kWh/Jahr"
        y_fmt = lambda x: f"{int(round(x)):,}".replace(",", "'") if pd.notna(x) else "-"
        better = "min"
    elif metric == "Emissionen pro m² (t CO₂e/m²)":
        y_col = "emissionen_pro_m2"
        y_title = "t CO₂e/m²"
        y_fmt = lambda x: f"{x:.4f}" if pd.notna(x) else "-"
        better = "min"
    else:
        y_col = "verbrauch_pro_m2"
        y_title = "kWh/m²"
        y_fmt = lambda x: f"{x:.1f}" if pd.notna(x) else "-"
        better = "min"

    plot_df = vdf[["gebaeude_id", "heizung_typ", y_col]].copy()
    if sort_on != "keine":
        plot_df = plot_df.sort_values(y_col, ascending=(sort_on == "aufsteigend"))

    if normalize:
        vals = plot_df[y_col].astype(float)
        vmin, vmax = vals.min(), vals.max()
        if pd.notna(vmin) and pd.notna(vmax) and vmax != vmin:
            plot_df["y_plot"] = (vals - vmin) / (vmax - vmin)
        else:
            plot_df["y_plot"] = 0.0
        y_plot_col = "y_plot"
        y_axis_title = "normalisiert (0–1)"
    else:
        y_plot_col = y_col
        y_axis_title = y_title

    # Farben (nur Gruen)
    heiz_order = list(plot_df["heizung_typ"].dropna().unique())
    green_palette = [GREEN_DARK, GREEN_MAIN, GREEN_MED, GREEN_LIGHT]
    heiz_color_map = {h: green_palette[i % len(green_palette)] for i, h in enumerate(heiz_order)}

    # Tabelle (formatiert)
    table_cols = [
        "gebaeude_id",
        "heizung_typ",
        "jahresverbrauch_kwh",
        "emissionen_gesamt_t",
        "flaeche_m2",
        "verbrauch_pro_m2",
        "emissionen_pro_m2",
    ]
    table_cols = [c for c in table_cols if c in vdf.columns]
    tdf = vdf[table_cols].copy()

    if "jahresverbrauch_kwh" in tdf.columns:
        tdf["jahresverbrauch_kwh"] = tdf["jahresverbrauch_kwh"].apply(lambda x: f"{int(round(x)):,}".replace(",", "'") if pd.notna(x) else "-")
    if "emissionen_gesamt_t" in tdf.columns:
        tdf["emissionen_gesamt_t"] = tdf["emissionen_gesamt_t"].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "-")
    if "flaeche_m2" in tdf.columns:
        tdf["flaeche_m2"] = tdf["flaeche_m2"].apply(lambda x: f"{int(round(x)):,}".replace(",", "'") if pd.notna(x) else "-")
    if "verbrauch_pro_m2" in tdf.columns:
        tdf["verbrauch_pro_m2"] = tdf["verbrauch_pro_m2"].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "-")
    if "emissionen_pro_m2" in tdf.columns:
        tdf["emissionen_pro_m2"] = tdf["emissionen_pro_m2"].apply(lambda x: f"{x:.4f}" if pd.notna(x) else "-")

    st.dataframe(tdf, use_container_width=True)

    # Balkenplot
    st.subheader("Vergleich")
    fig = px.bar(
        plot_df,
        x="gebaeude_id",
        y=y_plot_col,
        color="heizung_typ",
        color_discrete_map=heiz_color_map,
        template=PLOTLY_TEMPLATE,
        title=f"{metric}",
    )
    fig.update_layout(
        xaxis_title="",
        yaxis_title=y_axis_title,
        legend_title_text="Heizung",
        bargap=0.25,
    )
    st.plotly_chart(fig, use_container_width=True)

    # ------------------------------------------------------------
    # Delta zum besten Gebäude (Prozent)
    # ------------------------------------------------------------
    st.subheader("Delta zum besten Gebäude")

    base_series = vdf[["gebaeude_id", y_col]].dropna().copy()
    if base_series.empty:
        st.info("Für diese Kennzahl fehlen Werte.")
    else:
        if better == "min":
            best_val = base_series[y_col].min()
            best_id = base_series.loc[base_series[y_col].idxmin(), "gebaeude_id"]
        else:
            best_val = base_series[y_col].max()
            best_id = base_series.loc[base_series[y_col].idxmax(), "gebaeude_id"]

        delta_df = base_series.copy()
        delta_df["best_gebaeude"] = best_id
        delta_df["best_wert"] = best_val
        delta_df["delta_prozent"] = ((delta_df[y_col] - best_val) / best_val) * 100 if best_val != 0 else 0

        # Schön formatieren
        delta_df["wert"] = delta_df[y_col].apply(y_fmt)
        delta_df["delta_prozent"] = delta_df["delta_prozent"].apply(lambda x: f"{x:+.1f}%" if pd.notna(x) else "-")

        # Sort: best oben
        delta_df = delta_df.sort_values(y_col, ascending=(better == "min"))

        st.caption(f"Bestes Gebäude: **{best_id}** ({y_fmt(best_val)} {y_title})")
        st.dataframe(delta_df[["gebaeude_id", "wert", "delta_prozent"]], use_container_width=True)

    # ------------------------------------------------------------
    # Spider / Radar (3–4 Kennzahlen)
    # ------------------------------------------------------------
    st.subheader("Spider/Radar (normalisiert)")

    # Kennzahlen, die wir im Radar zeigen wollen
    # Emissionen/Verbrauch pro m² nur wenn Fläche vorhanden
    radar_metrics = [
        ("Emissionen", "emissionen_gesamt_t"),
        ("Verbrauch", "jahresverbrauch_kwh"),
    ]
    if "flaeche_m2" in vdf.columns:
        radar_metrics += [
            ("Emissionen pro m²", "emissionen_pro_m2"),
            ("Verbrauch pro m²", "verbrauch_pro_m2"),
        ]

    # Optional: Investition (wenn vorhanden)
    invest_cols = [c for c in ["investition_netto_chf", "investition_chf", "investition"] if c in vdf.columns]
    if invest_cols:
        radar_metrics += [("Investition", invest_cols[0])]

    # Auswahl 3–4 Kennzahlen
    options = [name for name, _ in radar_metrics]
    default_sel = options[:4] if len(options) >= 4 else options
    chosen = st.multiselect("Radar-Kennzahlen (3–4)", options, default=default_sel)

    if len(chosen) < 3:
        st.info("Bitte mindestens 3 Kennzahlen für den Radar auswählen.")
        return

    chosen = chosen[:4]
    chosen_cols = [col for name, col in radar_metrics if name in chosen]
    chosen_names = [name for name, col in radar_metrics if name in chosen]

    radar_df = vdf[["gebaeude_id"] + chosen_cols].copy()

    # Normalisieren pro Kennzahl (0–1), kleiner = besser -> invertieren
    # Für Emissionen/Verbrauch gilt: kleiner ist besser
    invert_if = set(["emissionen_gesamt_t", "jahresverbrauch_kwh", "emissionen_pro_m2", "verbrauch_pro_m2"] + invest_cols)

    for col in chosen_cols:
        vals = radar_df[col].astype(float)
        vmin, vmax = vals.min(), vals.max()
        if pd.isna(vmin) or pd.isna(vmax) or vmax == vmin:
            radar_df[col] = 0.0
        else:
            norm = (vals - vmin) / (vmax - vmin)
            radar_df[col] = (1 - norm) if col in invert_if else norm

    # Plotly Radar
    fig_r = go.Figure()
    for i, gid in enumerate(radar_df["gebaeude_id"].tolist()):
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
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 1]),
        ),
        showlegend=True,
        title="Radar: 1.0 = besser (normalisiert)",
    )
    st.plotly_chart(fig_r, use_container_width=True)

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
