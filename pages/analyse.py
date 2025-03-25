from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import ta
from core.app_instance import app
from data.session import trade_data

pairs = {
    'BTC/USD': 'BTC-USD',
    'XAU/USD': 'GC=F',
    'GBP/JPY': 'GBPJPY=X',
    'EUR/NZD': 'EURNZD=X',
    'EUR/CAD': 'EURCAD=X'
}

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

    close = df['Close'].squeeze()

    df['RSI'] = ta.momentum.RSIIndicator(close).rsi()
    macd = ta.trend.MACD(close)
    df['MACD'] = macd.macd()
    df['MACD_signal'] = macd.macd_signal()
    df['SMA_50'] = ta.trend.SMAIndicator(close, 50).sma_indicator()
    df['SMA_200'] = ta.trend.SMAIndicator(close, 200).sma_indicator()

    entry = float(df['Close'].iloc[-1])
    sl = round(entry * 0.98, 2)
    tp = round(entry * 1.03, 2)
    rr = round(abs(tp - entry) / abs(entry - sl), 2)

    alerts = []
    if df['RSI'].iloc[-1] > 70:
        alerts.append("RSI en surachat (>70)")
    elif df['RSI'].iloc[-1] < 30:
        alerts.append("RSI en survente (<30)")
    if df['MACD'].iloc[-1] > df['MACD_signal'].iloc[-1]:
        alerts.append("MACD haussier")
    elif df['MACD'].iloc[-1] < df['MACD_signal'].iloc[-1]:
        alerts.append("MACD baissier")

    trade_data.append({
        "pair": symbol,
        "entry": round(entry, 2),
        "sl": sl,
        "tp": tp,
        "rr": rr
    })

   def detect_levels(df, window=5):
    levels = []
    for i in range(window, len(df) - window):
        low = df['Low'].iloc[i]
        high = df['High'].iloc[i]
        if all(low < df['Low'].iloc[i - j] for j in range(1, window + 1)) and \
           all(low < df['Low'].iloc[i + j] for j in range(1, window + 1)):
            levels.append((df.index[i], low))
        if all(high > df['High'].iloc[i - j] for j in range(1, window + 1)) and \
           all(high > df['High'].iloc[i + j] for j in range(1, window + 1)):
            levels.append((df.index[i], high))
    return levels

    levels = detect_levels(df)

    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name="Bougies"
    ))

    fig.add_trace(go.Bar(
        x=df.index, y=df['Volume'],
        name="Volume", yaxis='y2',
        marker_color='lightblue', opacity=0.3
    ))

    fig.add_hline(y=entry, line_color="blue", line_dash="dot", annotation_text="Entrée", annotation_position="top left")
    fig.add_hline(y=tp, line_color="green", line_dash="dash", annotation_text="TP", annotation_position="top left")
    fig.add_hline(y=sl, line_color="red", line_dash="dash", annotation_text="SL", annotation_position="bottom left")

    for date, level in levels:
        fig.add_shape(type='line', x0=date, x1=date,
                      y0=level * 0.995, y1=level * 1.005,
                      line=dict(color="purple", width=1, dash="dot"))

    fig.update_layout(
        title=f"Analyse : {symbol}",
        xaxis_title="Date",
        yaxis_title="Prix",
        xaxis_rangeslider_visible=False,
        yaxis=dict(domain=[0.25, 1]),
        yaxis2=dict(domain=[0, 0.2], showgrid=False),
        height=600,
        template="plotly_white"
    )

    return html.Div([
        html.P(f"Entrée : {entry:.2f} € | SL : {sl:.2f} € | TP : {tp:.2f} €"),
        html.P(f"Risque/Rendement : {rr}"),
        html.Ul([html.Li(alert) for alert in alerts]) if alerts else html.P("Aucune alerte détectée.")
    ]), fig
