"""
Wirtschaftlichkeitsanalyse für Sanierungsmassnahmen
Berechnet ROI, NPV, Amortisation, Sensitivitäten
"""

from typing import Dict, List
import pandas as pd


# Annahmen für Wirtschaftlichkeitsberechnung (Schweiz 2025)
ENERGIEPREISE = {
    "Gas": 0.12,  # CHF/kWh
    "Öl": 0.13,   # CHF/kWh
    "Fernwärme": 0.14,  # CHF/kWh
    "Strom": 0.25,  # CHF/kWh (Haushalt)
    "Wärmepumpe": 0.20,  # CHF/kWh (Niedertarif)
}

PREISSTEIGERUNG_PROZENT = 2.5  # Jährliche Energiepreissteigerung
DISKONTIERUNGSSATZ = 2.0  # Zinssatz für NPV
CO2_ABGABE_CHF_PRO_T = 120  # Aktuelle CO₂-Abgabe (wird steigen)


def berechne_jaehrliche_einsparung(
    sanierung: Dict,
    alte_heizung: str,
    alter_verbrauch_kwh: float
) -> Dict:
    """
    Berechnet jährliche Kosteneinsparung durch Sanierung.
    
    Args:
        sanierung: Sanierungsszenario-Dict
        alte_heizung: Typ der alten Heizung
        alter_verbrauch_kwh: Alter Energieverbrauch
        
    Returns:
        Dictionary mit Einsparungen
    """
    # Alte Energiekosten
    alter_preis = ENERGIEPREISE.get(alte_heizung, 0.12)
    alte_kosten = alter_verbrauch_kwh * alter_preis
    
    # Neue Energiekosten
    if "neue_heizung" in sanierung:
        # Heizungsersatz
        neuer_verbrauch = sanierung.get("neuer_verbrauch_kwh", alter_verbrauch_kwh)
        neuer_preis = ENERGIEPREISE.get(sanierung["neue_heizung"], 0.12)
        neue_kosten = neuer_verbrauch * neuer_preis
    elif "energieeinsparung_kwh_jahr" in sanierung:
        # Dämmung
        einsparung = sanierung["energieeinsparung_kwh_jahr"]
        neue_kosten = (alter_verbrauch_kwh - einsparung) * alter_preis
    elif "eigenverbrauch_kwh" in sanierung:
        # Solar PV
        eigenverbrauch = sanierung["eigenverbrauch_kwh"]
        strom_preis = ENERGIEPREISE["Strom"]
        neue_kosten = 0  # PV reduziert Stromkosten
        einsparung_chf = eigenverbrauch * strom_preis
        return {
            "alte_energiekosten_chf": 0,
            "neue_energiekosten_chf": 0,
            "energiekosteneinsparung_chf": einsparung_chf,
            "co2_abgabe_einsparung_chf": 0,  # PV keine direkte CO₂-Abgabe
            "gesamteinsparung_chf_jahr": einsparung_chf,
        }
    else:
        neue_kosten = alte_kosten
    
    energiekosteneinsparung = alte_kosten - neue_kosten
    
    # CO₂-Abgaben-Einsparung
    co2_einsparung_t = sanierung.get("co2_einsparung_kg_jahr", 0) / 1000
    co2_abgabe_einsparung = co2_einsparung_t * CO2_ABGABE_CHF_PRO_T
    
    gesamteinsparung = energiekosteneinsparung + co2_abgabe_einsparung
    
    return {
        "alte_energiekosten_chf": alte_kosten,
        "neue_energiekosten_chf": neue_kosten,
        "energiekosteneinsparung_chf": energiekosteneinsparung,
        "co2_abgabe_einsparung_chf": co2_abgabe_einsparung,
        "gesamteinsparung_chf_jahr": gesamteinsparung,
    }


def berechne_amortisation(
    netto_investition: float,
    jaehrliche_einsparung: float
) -> float:
    """
    Berechnet einfache Amortisationszeit.
    
    Args:
        netto_investition: Investition nach Förderung
        jaehrliche_einsparung: Jährliche Kosteneinsparung
        
    Returns:
        Amortisationszeit in Jahren (float)
    """
    if jaehrliche_einsparung <= 0:
        return float('inf')
    
    return netto_investition / jaehrliche_einsparung


def berechne_npv(
    netto_investition: float,
    jaehrliche_einsparung: float,
    lebensdauer_jahre: int,
    diskontierungssatz: float = DISKONTIERUNGSSATZ,
    preissteigerung: float = PREISSTEIGERUNG_PROZENT
) -> float:
    """
    Berechnet Nettobarwert (NPV) der Sanierung.
    
    Args:
        netto_investition: Investition nach Förderung
        jaehrliche_einsparung: Einsparung im ersten Jahr
        lebensdauer_jahre: Lebensdauer der Massnahme
        diskontierungssatz: Zinssatz für Abzinsung
        preissteigerung: Jährliche Energiepreissteigerung
        
    Returns:
        NPV in CHF
    """
    npv = -netto_investition  # Initiale Investition (negativ)
    
    for jahr in range(1, lebensdauer_jahre + 1):
        # Einsparung steigt mit Energiepreissteigerung
        einsparung_jahr = jaehrliche_einsparung * ((1 + preissteigerung / 100) ** jahr)
        
        # Abzinsung
        barwert = einsparung_jahr / ((1 + diskontierungssatz / 100) ** jahr)
        
        npv += barwert
    
    return npv


def berechne_roi(
    netto_investition: float,
    jaehrliche_einsparung: float,
    lebensdauer_jahre: int
) -> float:
    """
    Berechnet Return on Investment (ROI) in Prozent.
    
    Args:
        netto_investition: Investition nach Förderung
        jaehrliche_einsparung: Jährliche Einsparung
        lebensdauer_jahre: Lebensdauer
        
    Returns:
        ROI in Prozent
    """
    if netto_investition <= 0:
        return 0
    
    gesamtertrag = jaehrliche_einsparung * lebensdauer_jahre
    roi = ((gesamtertrag - netto_investition) / netto_investition) * 100
    
    return roi


def erstelle_cashflow_tabelle(
    sanierung: Dict,
    jaehrliche_einsparung: float,
    lebensdauer_jahre: int = None
) -> pd.DataFrame:
    """
    Erstellt detaillierte Cashflow-Tabelle über Lebensdauer.
    
    Args:
        sanierung: Sanierungsszenario
        jaehrliche_einsparung: Einsparung im Jahr 1
        lebensdauer_jahre: Optional, sonst aus sanierung
        
    Returns:
        DataFrame mit jährlichen Cashflows
    """
    if lebensdauer_jahre is None:
        lebensdauer_jahre = sanierung.get("lebensdauer_jahre", 20)
    
    netto_inv = sanierung["investition_netto_chf"]
    
    jahre = list(range(0, lebensdauer_jahre + 1))
    cashflows = []
    kumuliert = []
    
    for jahr in jahre:
        if jahr == 0:
            # Jahr 0: Investition
            cf = -netto_inv
            kum = cf
        else:
            # Einsparung mit Preissteigerung
            einsparung = jaehrliche_einsparung * ((1 + PREISSTEIGERUNG_PROZENT / 100) ** jahr)
            cf = einsparung
            kum = kumuliert[-1] + cf
        
        cashflows.append(cf)
        kumuliert.append(kum)
    
    df = pd.DataFrame({
        "jahr": jahre,
        "cashflow_chf": cashflows,
        "cashflow_kumuliert_chf": kumuliert,
    })
    
    return df


def wirtschaftlichkeitsanalyse(
    sanierung: Dict,
    gebaeude: pd.Series
) -> Dict:
    """
    Vollständige Wirtschaftlichkeitsanalyse für eine Sanierung.
    
    Args:
        sanierung: Sanierungsszenario-Dict
        gebaeude: Gebäudedaten
        
    Returns:
        Dictionary mit allen Wirtschaftlichkeits-KPIs
    """
    # Jährliche Einsparung
    einsparungen = berechne_jaehrliche_einsparung(
        sanierung,
        gebaeude["heizung_typ"],
        gebaeude["jahresverbrauch_kwh"]
    )
    
    jaehrliche_einsparung = einsparungen["gesamteinsparung_chf_jahr"]
    netto_inv = sanierung["investition_netto_chf"]
    lebensdauer = sanierung.get("lebensdauer_jahre", 20)
    
    # KPIs
    amortisation = berechne_amortisation(netto_inv, jaehrliche_einsparung)
    npv = berechne_npv(netto_inv, jaehrliche_einsparung, lebensdauer)
    roi = berechne_roi(netto_inv, jaehrliche_einsparung, lebensdauer)
    
    # Gesamtertrag über Lebensdauer
    gesamtertrag = sum([
        jaehrliche_einsparung * ((1 + PREISSTEIGERUNG_PROZENT / 100) ** j)
        for j in range(1, lebensdauer + 1)
    ])
    
    # Cashflow-Tabelle
    cashflow_df = erstelle_cashflow_tabelle(sanierung, jaehrliche_einsparung, lebensdauer)
    
    return {
        **sanierung,  # Alle Sanierungsdaten
        **einsparungen,  # Einsparungs-Details
        "amortisation_jahre": amortisation,
        "npv_chf": npv,
        "roi_prozent": roi,
        "gesamtertrag_chf": gesamtertrag,
        "nettogewinn_chf": gesamtertrag - netto_inv,
        "cashflow_tabelle": cashflow_df,
    }


def sensitivitaetsanalyse(
    sanierung: Dict,
    gebaeude: pd.Series,
    parameter: str = "energiepreis",
    variationen: List[float] = None
) -> pd.DataFrame:
    """
    Sensitivitätsanalyse für verschiedene Parameter.
    
    Args:
        sanierung: Sanierungsszenario
        gebaeude: Gebäudedaten
        parameter: "energiepreis", "co2_abgabe", "foerderung"
        variationen: Liste mit Variationsfaktoren (z.B. [0.8, 1.0, 1.2, 1.5])
        
    Returns:
        DataFrame mit Ergebnissen für verschiedene Szenarien
    """
    if variationen is None:
        variationen = [0.8, 0.9, 1.0, 1.1, 1.2, 1.5, 2.0]
    
    ergebnisse = []
    
    for faktor in variationen:
        # Kopie erstellen
        san_kopie = sanierung.copy()
        
        if parameter == "energiepreis":
            # Energiepreise anpassen
            global ENERGIEPREISE
            alte_preise = ENERGIEPREISE.copy()
            ENERGIEPREISE = {k: v * faktor for k, v in alte_preise.items()}
            
            analyse = wirtschaftlichkeitsanalyse(san_kopie, gebaeude)
            
            # Zurücksetzen
            ENERGIEPREISE = alte_preise
            
            ergebnisse.append({
                "szenario": f"Energiepreis {faktor:.1f}x",
                "faktor": faktor,
                "amortisation_jahre": analyse["amortisation_jahre"],
                "npv_chf": analyse["npv_chf"],
                "roi_prozent": analyse["roi_prozent"],
                "jaehrliche_einsparung_chf": analyse["gesamteinsparung_chf_jahr"],
            })
            
        elif parameter == "co2_abgabe":
            # CO₂-Abgabe anpassen
            global CO2_ABGABE_CHF_PRO_T
            alte_abgabe = CO2_ABGABE_CHF_PRO_T
            CO2_ABGABE_CHF_PRO_T = alte_abgabe * faktor
            
            analyse = wirtschaftlichkeitsanalyse(san_kopie, gebaeude)
            
            CO2_ABGABE_CHF_PRO_T = alte_abgabe
            
            ergebnisse.append({
                "szenario": f"CO₂-Abgabe {int(alte_abgabe * faktor)} CHF/t",
                "faktor": faktor,
                "amortisation_jahre": analyse["amortisation_jahre"],
                "npv_chf": analyse["npv_chf"],
                "roi_prozent": analyse["roi_prozent"],
                "jaehrliche_einsparung_chf": analyse["gesamteinsparung_chf_jahr"],
            })
            
        elif parameter == "foerderung":
            # Förderung anpassen
            san_kopie["foerderung_chf"] = sanierung["foerderung_chf"] * faktor
            san_kopie["investition_netto_chf"] = (
                sanierung["investition_brutto_chf"] - san_kopie["foerderung_chf"]
            )
            
            analyse = wirtschaftlichkeitsanalyse(san_kopie, gebaeude)
            
            ergebnisse.append({
                "szenario": f"Förderung {faktor:.1f}x",
                "faktor": faktor,
                "amortisation_jahre": analyse["amortisation_jahre"],
                "npv_chf": analyse["npv_chf"],
                "roi_prozent": analyse["roi_prozent"],
                "jaehrliche_einsparung_chf": analyse["gesamteinsparung_chf_jahr"],
            })
    
    return pd.DataFrame(ergebnisse)


def co2_preis_szenarien(
    sanierung: Dict,
    gebaeude: pd.Series,
    co2_preise: List[int] = None
) -> pd.DataFrame:
    """
    Berechnet Wirtschaftlichkeit bei verschiedenen CO₂-Preisen.
    
    Args:
        sanierung: Sanierungsszenario
        gebaeude: Gebäudedaten
        co2_preise: Liste mit CO₂-Preisen [CHF/t]
        
    Returns:
        DataFrame mit Ergebnissen
    """
    if co2_preise is None:
        # Realistische Szenarien für Schweiz
        co2_preise = [0, 120, 200, 300, 500]  # 120 = aktuell
    
    faktoren = [p / CO2_ABGABE_CHF_PRO_T for p in co2_preise]
    
    df = sensitivitaetsanalyse(sanierung, gebaeude, "co2_abgabe", faktoren)
    df["co2_preis_chf_pro_t"] = co2_preise
    
    return df
