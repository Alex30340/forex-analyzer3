from dash import html, dash_table
import dash_bootstrap_components as dbc
from data.session import trade_data
from core.app_instance import app
from dash.dependencies import Input, Output

capital = 500
risk_pct = 0.02

def compute_portfolio():
    rows = []
    total_risked = 0
    for trade in trade_data:
        risk_amount = capital * risk_pct
        size = round(risk_amount / abs(trade["entry"] - trade["sl"]), 2)
        position = {
            "Paire": trade["pair"],
            "Entrée (€)": trade["entry"],
            "SL (€)": trade["sl"],
            "TP (€)": trade["tp"],
            "Taille (€)": size,
            "R/R": trade["rr"]
        }
        total_risked += risk_amount
        rows.append(position)
    return rows, capital - total_risked

layout = dbc.Container([
    html.H4("Tableau de Bord - Portefeuille Virtuel"),
    html.Div(id="portfolio-content")
], fluid=True)

@app.callback(
    Output("portfolio-content", "children"),
    Input("url", "pathname")
)
def update_dashboard(path):
    rows, remaining = compute_portfolio()
    table = dash_table.DataTable(
        columns=[{"name": i, "id": i} for i in rows[0].keys()] if rows else [],
        data=rows,
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'left'},
    ) if rows else html.P("Aucune position enregistrée.")
    return html.Div([
        html.P(f"💰 Capital disponible : {remaining:.2f} €"),
        html.Br(),
        table
    ])