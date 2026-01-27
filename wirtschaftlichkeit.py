"""
Wirtschaftlichkeitsanalyse für Sanierungsmassnahmen
Berechnet ROI, NPV, Amortisation, Sensitivitäten

Hinweis:
- ROI wird als Jahres-ROI gerechnet (jaehrliche Einsparung / Netto-Investition)
- NPV wird ueber einen expliziten Betrachtungszeitraum gerechnet (Default: 25 Jahre)
"""

from typing import Dict, List, Optional, Any
import pandas as pd


# ------------------------------------------------------------
# Annahmen (Schweiz)
# ------------------------------------------------------------
ENERGIEPREISE = {
    "Gas": 0.12,         # CHF/kWh
    "Öl": 0.13,          # CHF/kWh
    "Fernwärme": 0.14,   # CHF/kWh
    "Strom": 0.25,       # CHF/kWh (Haushalt)
    "Wärmepumpe": 0.20,  # CHF/kWh (Niedertarif)
}

PREISSTEIGERUNG_PROZENT = 2.5   # jährliche Energiepreissteigerung
DISKONTIERUNGSSATZ = 2.0        # Zinssatz für NPV (in %)
CO2_ABGABE_CHF_PRO_T = 120      # CHF/t

# Expliziter Zeitraum fuer NPV
NPV_ZEITRAUM_JAHRE = 25


# ------------------------------------------------------------
# Helper
# ------------------------------------------------------------
def _to_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _get_brutto_investition(sanierung: Dict) -> float:
    """
    Robust: findet eine Brutto-Investition aus gaengigen Keys.
    """
    if "investition_brutto_chf" in sanierung:
        return _to_float(sanierung.get("investition_brutto_chf", 0.0))
    if "investition_chf" in sanierung:
        return _to_float(sanierung.get("investition_chf", 0.0))
    # Falls nur netto + foerderung existiert
    netto = _to_float(sanierung.get("investition_netto_chf", 0.0))
    foerd = _to_float(sanierung.get("foerderung_chf", 0.0))
    return max(0.0, netto + foerd)


def _get_netto_investition(sanierung: Dict) -> float:
    """
    Netto = Brutto - Foerderung (falls netto nicht direkt vorhanden).
    """
    if "investition_netto_chf" in sanierung:
        return max(0.0, _to_float(sanierung.get("investition_netto_chf", 0.0)))

    brutto = _get_brutto_investition(sanierung)
    foerd = _to_float(sanierung.get("foerderung_chf", 0.0))
    return max(0.0, brutto - foerd)


# ------------------------------------------------------------
# Einsparungen
# ------------------------------------------------------------
def berechne_jaehrliche_einsparung(
    sanierung: Dict,
    alte_heizung: str,
    alter_verbrauch_kwh: float,
    energiepreise: Optional[Dict[str, float]] = None,
    co2_abgabe_chf_pro_t: float = CO2_ABGABE_CHF_PRO_T,
) -> Dict:
    """
    Berechnet jährliche Kosteneinsparung durch Sanierung (Jahr 1).

    - energiepreise und co2_abgabe werden als Parameter erlaubt, damit Sensitivitaet
      ohne globale Mutation funktioniert.
    """
    if energiepreise is None:
        energiepreise = ENERGIEPREISE

    alter_preis = energiepreise.get(alte_heizung, 0.12)
    alte_kosten = _to_float(alter_verbrauch_kwh) * alter_preis

    # Neue Energiekosten
    if "neue_heizung" in sanierung:
        neuer_verbrauch = sanierung.get("neuer_verbrauch_kwh", alter_verbrauch_kwh)
        neuer_preis = energiepreise.get(sanierung["neue_heizung"], 0.12)
        neue_kosten = _to_float(neuer_verbrauch) * neuer_preis

    elif "energieeinsparung_kwh_jahr" in sanierung:
        einsparung = _to_float(sanierung.get("energieeinsparung_kwh_jahr", 0.0))
        neue_kosten = max(0.0, (_to_float(alter_verbrauch_kwh) - einsparung)) * alter_preis

    elif "eigenverbrauch_kwh" in sanierung:
        eigenverbrauch = _to_float(sanierung.get("eigenverbrauch_kwh", 0.0))
        strom_preis = energiepreise.get("Strom", 0.25)
        einsparung_chf = eigenverbrauch * strom_preis
        return {
            "alte_energiekosten_chf": 0.0,
            "neue_energiekosten_chf": 0.0,
            "energiekosteneinsparung_chf": einsparung_chf,
            "co2_abgabe_einsparung_chf": 0.0,
            "gesamteinsparung_chf_jahr": einsparung_chf,
        }

    else:
        neue_kosten = alte_kosten

    energiekosteneinsparung = alte_kosten - neue_kosten

    # CO2-Abgaben-Einsparung (Jahr 1)
    co2_einsparung_t = _to_float(sanierung.get("co2_einsparung_kg_jahr", 0.0)) / 1000.0
    co2_abgabe_einsparung = co2_einsparung_t * _to_float(co2_abgabe_chf_pro_t)

    gesamteinsparung = energiekosteneinsparung + co2_abgabe_einsparung

    return {
        "alte_energiekosten_chf": alte_kosten,
        "neue_energiekosten_chf": neue_kosten,
        "energiekosteneinsparung_chf": energiekosteneinsparung,
        "co2_abgabe_einsparung_chf": co2_abgabe_einsparung,
        "gesamteinsparung_chf_jahr": gesamteinsparung,
    }


# ------------------------------------------------------------
# KPIs
# ------------------------------------------------------------
def berechne_amortisation(netto_investition: float, jaehrliche_einsparung: float) -> float:
    """
    Einfache Amortisationszeit in Jahren.
    """
    netto = _to_float(netto_investition)
    save = _to_float(jaehrliche_einsparung)

    if save <= 0:
        return float("inf")
    return netto / save


def berechne_npv(
    netto_investition: float,
    jaehrliche_einsparung: float,
    zeitraum_jahre: int,
    diskontierungssatz: float = DISKONTIERUNGSSATZ,
    preissteigerung: float = PREISSTEIGERUNG_PROZENT,
) -> float:
    """
    NPV ueber fixen Betrachtungszeitraum (explizit).
    Einsparungen steigen mit PREISSTEIGERUNG_PROZENT, werden diskontiert.
    """
    netto = _to_float(netto_investition)
    save0 = _to_float(jaehrliche_einsparung)

    r = _to_float(diskontierungssatz) / 100.0
    g = _to_float(preissteigerung) / 100.0

    npv = -netto
    for jahr in range(1, int(zeitraum_jahre) + 1):
        einsparung_jahr = save0 * ((1 + g) ** jahr)
        barwert = einsparung_jahr / ((1 + r) ** jahr)
        npv += barwert

    return npv


def berechne_roi(netto_investition: float, jaehrliche_einsparung: float) -> float:
    """
    ROI als Jahres-ROI (statisch, ohne fixen Zeitraum).
    ROI [%] = jaehrliche Einsparung / Netto-Investition * 100
    """
    netto = _to_float(netto_investition)
    save = _to_float(jaehrliche_einsparung)

    if netto <= 0:
        return 0.0
    return (save / netto) * 100.0


def berechne_roi_lebensdauer(netto_investition: float, jaehrliche_einsparung: float, zeitraum_jahre: int) -> float:
    """
    Optional: ROI ueber Lebensdauer (Summe Einsparungen - Investition) / Investition.
    Diese Kennzahl ist NICHT der Jahres-ROI, kann aber fuer Zusatzinfos nuetzlich sein.
    """
    netto = _to_float(netto_investition)
    save = _to_float(jaehrliche_einsparung)

    if netto <= 0:
        return 0.0

    gesamtertrag = save * int(zeitraum_jahre)
    return ((gesamtertrag - netto) / netto) * 100.0


# ------------------------------------------------------------
# Cashflows
# ------------------------------------------------------------
def erstelle_cashflow_tabelle(
    sanierung: Dict,
    jaehrliche_einsparung: float,
    zeitraum_jahre: Optional[int] = None,
) -> pd.DataFrame:
    """
    Cashflow-Tabelle (nicht diskontiert): Jahr 0 Investition, danach Einsparungen mit Preissteigerung.
    """
    if zeitraum_jahre is None:
        zeitraum_jahre = int(sanierung.get("lebensdauer_jahre", NPV_ZEITRAUM_JAHRE))

    netto_inv = _get_netto_investition(sanierung)

    jahre = list(range(0, int(zeitraum_jahre) + 1))
    cashflows, kumuliert = [], []

    for jahr in jahre:
        if jahr == 0:
            cf = -netto_inv
            kum = cf
        else:
            cf = _to_float(jaehrliche_einsparung) * ((1 + PREISSTEIGERUNG_PROZENT / 100.0) ** jahr)
            kum = kumuliert[-1] + cf

        cashflows.append(cf)
        kumuliert.append(kum)

    return pd.DataFrame(
        {"jahr": jahre, "cashflow_chf": cashflows, "cashflow_kumuliert_chf": kumuliert}
    )


# ------------------------------------------------------------
# Hauptanalyse
# ------------------------------------------------------------
def wirtschaftlichkeitsanalyse(sanierung: Dict, gebaeude: pd.Series) -> Dict:
    """
    Vollstaendige Wirtschaftlichkeitsanalyse fuer eine Sanierung.

    Output:
    - amortisation_jahre
    - npv_chf + npv_zeitraum_jahre
    - roi_prozent (Jahres-ROI)
    - roi_lebensdauer_prozent (optional)
    - cashflow_tabelle (DataFrame)
    """
    alte_heizung = str(gebaeude.get("heizung_typ", "Gas"))
    alter_verbrauch = _to_float(gebaeude.get("jahresverbrauch_kwh", 0.0))

    einsparungen = berechne_jaehrliche_einsparung(sanierung, alte_heizung, alter_verbrauch)

    jaehrliche_einsparung = _to_float(einsparungen.get("gesamteinsparung_chf_jahr", 0.0))
    netto_inv = _get_netto_investition(sanierung)

    # Expliziter NPV-Zeitraum: default 25 Jahre, falls Szenario nichts setzt
    zeitraum = int(sanierung.get("lebensdauer_jahre", NPV_ZEITRAUM_JAHRE))

    amortisation = berechne_amortisation(netto_inv, jaehrliche_einsparung)
    npv = berechne_npv(netto_inv, jaehrliche_einsparung, zeitraum)
    roi_jahr = berechne_roi(netto_inv, jaehrliche_einsparung)
    roi_ld = berechne_roi_lebensdauer(netto_inv, jaehrliche_einsparung, zeitraum)

    # Gesamtertrag (nicht diskontiert) ueber Zeitraum
    gesamtertrag = sum(
        [jaehrliche_einsparung * ((1 + PREISSTEIGERUNG_PROZENT / 100.0) ** j) for j in range(1, zeitraum + 1)]
    )

    cashflow_df = erstelle_cashflow_tabelle(sanierung, jaehrliche_einsparung, zeitraum)

    out = {
        **sanierung,
        **einsparungen,
        "investition_netto_chf": netto_inv,
        "amortisation_jahre": amortisation,
        "npv_chf": npv,
        "npv_zeitraum_jahre": zeitraum,
        "diskontierungssatz_prozent": DISKONTIERUNGSSATZ,
        "preissteigerung_prozent": PREISSTEIGERUNG_PROZENT,
        "roi_prozent": roi_jahr,  # Jahres-ROI
        "roi_lebensdauer_prozent": roi_ld,
        "gesamtertrag_chf": gesamtertrag,
        "nettogewinn_chf": gesamtertrag - netto_inv,
        "cashflow_tabelle": cashflow_df,
        "jaehrliche_einsparung_chf": jaehrliche_einsparung,  # hilfreich fuer UI/Sensitivitaet
    }
    return out


# ------------------------------------------------------------
# Sensitivitaeten (ohne globale Mutation)
# ------------------------------------------------------------
def sensitivitaetsanalyse(
    sanierung: Dict,
    gebaeude: pd.Series,
    parameter: str = "energiepreis",
    variationen: Optional[List[float]] = None,
) -> pd.DataFrame:
    """
    Sensitivitaet fuer:
    - energiepreis: skaliert ENERGIEPREISE
    - co2_abgabe: skaliert CO2_ABGABE_CHF_PRO_T
    - foerderung: skaliert foerderung_chf

    Funktioniert fuer alle Szenarien, auch wenn investition_brutto_chf nicht gesetzt ist.
    """
    if variationen is None:
        variationen = [0.8, 0.9, 1.0, 1.1, 1.2, 1.5, 2.0]

    alte_heizung = str(gebaeude.get("heizung_typ", "Gas"))
    alter_verbrauch = _to_float(gebaeude.get("jahresverbrauch_kwh", 0.0))

    ergebnisse = []
    base_brutto = _get_brutto_investition(sanierung)
    base_foerd = _to_float(sanierung.get("foerderung_chf", 0.0))

    for faktor in variationen:
        f = _to_float(faktor, 1.0)
        san_kopie = dict(sanierung)

        if parameter == "energiepreis":
            energiepreise_scaled = {k: v * f for k, v in ENERGIEPREISE.items()}
            eins = berechne_jaehrliche_einsparung(
                san_kopie, alte_heizung, alter_verbrauch, energiepreise=energiepreise_scaled, co2_abgabe_chf_pro_t=CO2_ABGABE_CHF_PRO_T
            )

            # Danach normale KPI-Rechnung auf Basis der Einsparung
            san_kopie["investition_netto_chf"] = _get_netto_investition(san_kopie)
            jaehr = _to_float(eins.get("gesamteinsparung_chf_jahr", 0.0))
            zeitraum = int(san_kopie.get("lebensdauer_jahre", NPV_ZEITRAUM_JAHRE))

            amort = berechne_amortisation(san_kopie["investition_netto_chf"], jaehr)
            npv = berechne_npv(san_kopie["investition_netto_chf"], jaehr, zeitraum)
            roi = berechne_roi(san_kopie["investition_netto_chf"], jaehr)

            ergebnisse.append(
                {
                    "szenario": f"Energiepreis {f:.1f}x",
                    "faktor": f,
                    "amortisation_jahre": amort,
                    "npv_chf": npv,
                    "roi_prozent": roi,
                    "jaehrliche_einsparung_chf": jaehr,
                }
            )

        elif parameter == "co2_abgabe":
            co2_abgabe_scaled = CO2_ABGABE_CHF_PRO_T * f
            eins = berechne_jaehrliche_einsparung(
                san_kopie, alte_heizung, alter_verbrauch, energiepreise=ENERGIEPREISE, co2_abgabe_chf_pro_t=co2_abgabe_scaled
            )

            san_kopie["investition_netto_chf"] = _get_netto_investition(san_kopie)
            jaehr = _to_float(eins.get("gesamteinsparung_chf_jahr", 0.0))
            zeitraum = int(san_kopie.get("lebensdauer_jahre", NPV_ZEITRAUM_JAHRE))

            amort = berechne_amortisation(san_kopie["investition_netto_chf"], jaehr)
            npv = berechne_npv(san_kopie["investition_netto_chf"], jaehr, zeitraum)
            roi = berechne_roi(san_kopie["investition_netto_chf"], jaehr)

            ergebnisse.append(
                {
                    "szenario": f"CO₂-Abgabe {int(co2_abgabe_scaled)} CHF/t",
                    "faktor": f,
                    "amortisation_jahre": amort,
                    "npv_chf": npv,
                    "roi_prozent": roi,
                    "jaehrliche_einsparung_chf": jaehr,
                }
            )

        elif parameter == "foerderung":
            # Foerderung skalieren -> Netto-Investition neu
            san_kopie["foerderung_chf"] = base_foerd * f
            san_kopie["investition_brutto_chf"] = base_brutto
            san_kopie["investition_netto_chf"] = max(0.0, base_brutto - _to_float(san_kopie["foerderung_chf"]))

            analyse = wirtschaftlichkeitsanalyse(san_kopie, gebaeude)

            ergebnisse.append(
                {
                    "szenario": f"Förderung {f:.1f}x",
                    "faktor": f,
                    "amortisation_jahre": analyse["amortisation_jahre"],
                    "npv_chf": analyse["npv_chf"],
                    "roi_prozent": analyse["roi_prozent"],
                    "jaehrliche_einsparung_chf": analyse["jaehrliche_einsparung_chf"],
                }
            )

        else:
            # Default: wie energiepreis behandeln
            energiepreise_scaled = {k: v * f for k, v in ENERGIEPREISE.items()}
            eins = berechne_jaehrliche_einsparung(
                san_kopie, alte_heizung, alter_verbrauch, energiepreise=energiepreise_scaled, co2_abgabe_chf_pro_t=CO2_ABGABE_CHF_PRO_T
            )
            san_kopie["investition_netto_chf"] = _get_netto_investition(san_kopie)
            jaehr = _to_float(eins.get("gesamteinsparung_chf_jahr", 0.0))
            zeitraum = int(san_kopie.get("lebensdauer_jahre", NPV_ZEITRAUM_JAHRE))

            amort = berechne_amortisation(san_kopie["investition_netto_chf"], jaehr)
            npv = berechne_npv(san_kopie["investition_netto_chf"], jaehr, zeitraum)
            roi = berechne_roi(san_kopie["investition_netto_chf"], jaehr)

            ergebnisse.append(
                {
                    "szenario": f"Variation {f:.1f}x",
                    "faktor": f,
                    "amortisation_jahre": amort,
                    "npv_chf": npv,
                    "roi_prozent": roi,
                    "jaehrliche_einsparung_chf": jaehr,
                }
            )

    return pd.DataFrame(ergebnisse)


def co2_preis_szenarien(
    sanierung: Dict,
    gebaeude: pd.Series,
    co2_preise: Optional[List[int]] = None,
) -> pd.DataFrame:
    """
    Wirtschaftlichkeit bei verschiedenen CO₂-Preisen (CHF/t).
    """
    if co2_preise is None:
        co2_preise = [0, 120, 200, 300, 500]

    # Faktor relativ zum Basispreis (120 CHF/t)
    faktoren = [(p / CO2_ABGABE_CHF_PRO_T) if CO2_ABGABE_CHF_PRO_T else 1.0 for p in co2_preise]
    df = sensitivitaetsanalyse(sanierung, gebaeude, "co2_abgabe", faktoren)
    df["co2_preis_chf_pro_t"] = co2_preise
    return df
