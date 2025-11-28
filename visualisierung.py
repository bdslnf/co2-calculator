"""
Visualisierungen für CO₂-Emissionsanalyse
Erstellt interaktive Plotly-Diagramme
"""

from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


def erstelle_balkendiagramm_gesamt(
    df: pd.DataFrame, 
    output_path: Path
) -> Path:
    """
    Balkendiagramm: Kumulierte Gesamt-Emissionen pro Gebäude.
    
    Args:
        df: DataFrame mit aggregierten Daten
        output_path: Pfad zum Speichern der HTML-Datei
        
    Returns:
        Pfad zur erstellten Datei
    """
    # Gesamtsumme pro Gebäude
    total = df.groupby("gebaeude_id", as_index=False).agg({
        "emissionen_gesamt_t": "sum"
    })
    total = total.sort_values("emissionen_gesamt_t", ascending=False)
    
    fig = px.bar(
        total,
        x="gebaeude_id",
        y="emissionen_gesamt_t",
        text="emissionen_gesamt_t",
        title="Kumulierte CO₂-Emissionen pro Gebäude (Gesamtzeitraum)",
        labels={
            "gebaeude_id": "Gebäude-ID",
            "emissionen_gesamt_t": "CO₂-Emissionen [t CO₂e]"
        },
        color="emissionen_gesamt_t",
        color_continuous_scale="Reds"
    )
    
    fig.update_traces(
        texttemplate="%{text:.1f} t",
        textposition="outside"
    )
    
    fig.update_layout(
        showlegend=False,
        height=500,
        font=dict(size=12),
        xaxis_title="Gebäude",
        yaxis_title="CO₂-Emissionen [t CO₂e]"
    )
    
    fig.write_html(output_path)
    return output_path


def erstelle_liniendiagramm_jaehrlich(
    df: pd.DataFrame,
    output_path: Path
) -> Path:
    """
    Liniendiagramm: Jährliche Emissionen (nicht kumuliert) pro Gebäude.
    
    Args:
        df: DataFrame mit Jahreswerten
        output_path: Pfad zum Speichern
        
    Returns:
        Pfad zur erstellten Datei
    """
    fig = px.line(
        df,
        x="jahr",
        y="emissionen_gesamt_t",
        color="gebaeude_id",
        markers=True,
        title="Jährliche CO₂-Emissionen pro Gebäude",
        labels={
            "jahr": "Jahr",
            "emissionen_gesamt_t": "CO₂-Emissionen [t CO₂e/Jahr]",
            "gebaeude_id": "Gebäude"
        }
    )
    
    fig.update_layout(
        height=500,
        hovermode="x unified",
        legend=dict(
            title="Gebäude",
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02
        )
    )
    
    fig.write_html(output_path)
    return output_path


def erstelle_liniendiagramm_kumuliert(
    df: pd.DataFrame,
    output_path: Path
) -> Path:
    """
    Liniendiagramm: Kumulierte Emissionen über Zeit pro Gebäude.
    
    Args:
        df: DataFrame mit kumulierten Werten
        output_path: Pfad zum Speichern
        
    Returns:
        Pfad zur erstellten Datei
    """
    fig = px.line(
        df,
        x="jahr",
        y="emissionen_kumuliert_t",
        color="gebaeude_id",
        markers=True,
        title="Kumulierte CO₂-Emissionen über Zeit",
        labels={
            "jahr": "Jahr",
            "emissionen_kumuliert_t": "Kumulierte CO₂-Emissionen [t CO₂e]",
            "gebaeude_id": "Gebäude"
        }
    )
    
    fig.update_layout(
        height=500,
        hovermode="x unified",
        legend=dict(
            title="Gebäude",
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02
        )
    )
    
    fig.write_html(output_path)
    return output_path


def erstelle_alle_visualisierungen(
    df_yearly: pd.DataFrame,
    df_kumuliert: pd.DataFrame,
    output_dir: Path
) -> dict:
    """
    Erstellt alle drei Standard-Visualisierungen.
    
    Args:
        df_yearly: DataFrame mit jährlichen Werten
        df_kumuliert: DataFrame mit kumulierten Werten
        output_dir: Ausgabeordner
        
    Returns:
        Dictionary mit Pfaden zu allen erstellten Dateien
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    paths = {
        "balken": erstelle_balkendiagramm_gesamt(
            df_yearly,
            output_dir / "01_balken_kumuliert_gesamt.html"
        ),
        "linien_jaehrlich": erstelle_liniendiagramm_jaehrlich(
            df_yearly,
            output_dir / "02_linien_jaehrlich.html"
        ),
        "linien_kumuliert": erstelle_liniendiagramm_kumuliert(
            df_kumuliert,
            output_dir / "03_linien_kumuliert.html"
        )
    }
    
    return paths
