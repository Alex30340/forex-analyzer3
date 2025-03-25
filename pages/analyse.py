from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import ta
from core.app_instance import app
from data.session import trade_data
@app.callback(
    Output('results', 'children'),
    Output('chart', 'figure'),
    Input('analyze-button', 'n_clicks'),
    State('pair-selector', 'value')
)
def run_analysis(n, symbol):
    if not symbol:
        return "Sélectionnez une paire", go.Figure()

    df = yf.download(symbol, period="6mo", interval="1d")
    if df.empty:
        return "Données non disponibles.", go.Figure()

    df.dropna(inplace=True)

    # Indicateurs
    df['RSI'] = ta.momentum.RSIIndicator(df['Close']).rsi()
    macd = ta.trend.MACD(df['Close'])
    df['MACD'] = macd.macd()
    df['MACD_signal'] = macd.macd_signal()
    df['SMA_50'] = ta.trend.SMAIndicator(df['Close'], 50).sma_indicator()
    df['SMA_200'] = ta.trend.SMAIndicator(df['Close'], 200).sma_indicator()

    # Setup trade
    entry = float(df['Close'].iloc[-1])
    sl = round(entry * 0.98, 2)
    tp = round(entry * 1.03, 2)
    rr = round(abs(tp - entry) / abs(entry - sl), 2)

    # Alerte
    alerts = []
    if df['RSI'].iloc[-1] > 70:
        alerts.append("RSI en surachat (>70)")
    elif df['RSI'].iloc[-1] < 30:
        alerts.append("RSI en survente (<30)")
    if df['MACD'].iloc[-1] > df['MACD_signal'].iloc[-1]:
        alerts.append("MACD haussier")
    elif df['MACD'].iloc[-1] < df['MACD_signal'].iloc[-1]:
        alerts.append("MACD baissier")

    # Enregistrer la position
    trade_data.append({
        "pair": symbol,
        "entry": round(entry, 2),
        "sl": sl,
        "tp": tp,
        "rr": rr
    })

    # Détection de niveaux (résistances/supports simplifiées)
    def detect_levels(df, window=5):
        levels = []
        for i in range(window, len(df) - window):
            low = df['Low'][i]
            high = df['High'][i]
            if all(low < df['Low'][i - j] for j in range(1, window + 1)) and all(low < df['Low'][i + j] for j in range(1, window + 1)):
                levels.append((df.index[i], low))
            if all(high > df['High'][i - j] for j in range(1, window + 1)) and all(high > df['High'][i + j] for j in range(1, window + 1)):
                levels.append((df.index[i], high))
        return levels

    levels = detect_levels(df)

    # Graphique
    fig = go.Figure()

    # Bougies japonaises
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name="Bougies"
    ))

    # Volume
    fig.add_trace(go.Bar(
        x=df.index, y=df['Volume'],
        name="Volume", yaxis='y2',
        marker_color='lightblue', opacity=0.3
    ))

    # Lignes SL/TP/Entrée
    fig.add_hline(y=entry, line_color="blue", line_dash="dot", annotation_text="Entrée", annotation_position="top left")
    fig.add_hline(y=tp, line_color="green", line_dash="dash", annotation_text="TP", annotation_position="top left")
    fig.add_hline(y=sl, line_color="red", line_dash="dash", annotation_text="SL", annotation_position="bottom left")

    # Lignes de niveaux
    for date, level in levels:
        fig.add_shape(type='line', x0=date, x1=date,
                      y0=level * 0.995, y1=level * 1.005,
                      line=dict(color="purple", width=1, dash="dot"))

    layout = dbc.Container([
    html.H4("Analyse Technique Automatique"),
    dcc.Dropdown(
        id='pair-selector',
        options=[{'label': k, 'value': v} for k, v in pairs.items()],
        value='BTC-USD',
        style={'width': '300px'}
    ),
    html.Button('Analyser', id='analyze-button', n_clicks=0, className='btn btn-primary mt-2'),
    html.Div(id='results', className='mt-4'),
    dcc.Graph(id='chart')
], fluid=True)


    return html.Div([
        html.P(f"Entrée : {entry:.2f} € | SL : {sl:.2f} € | TP : {tp:.2f} €"),
        html.P(f"Risque/Rendement : {rr}"),
        html.Ul([html.Li(alert) for alert in alerts]) if alerts else html.P("Aucune alerte détectée.")
    ]), fig
layout = dbc.Container([
    html.H4("Analyse Technique Automatique"),
    dcc.Dropdown(
        id='pair-selector',
        options=[{'label': k, 'value': v} for k, v in pairs.items()],
        value='BTC-USD',
        style={'width': '300px'}
    ),
    html.Button('Analyser', id='analyze-button', n_clicks=0, className='btn btn-primary mt-2'),
    html.Div(id='results', className='mt-4'),
    dcc.Graph(id='chart')
], fluid=True)

