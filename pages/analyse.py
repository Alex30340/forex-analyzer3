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

intervals = {
    '1 Heure (H1)': '60m',
    '4 Heures (H4)': '60m',  # fallback temporaire vers 60m
    '1 Jour (D1)': '1d',
    '1 Semaine (W1)': '1wk'
}

layout = dbc.Container([
    html.H4("Analyse Technique Automatique"),
    dcc.Dropdown(
        id='pair-selector',
        options=[{'label': k, 'value': v} for k, v in pairs.items()],
        value='BTC-USD',
        style={'width': '300px'}
    ),
    dcc.Dropdown(
        id='interval-selector',
        options=[{'label': k, 'value': v} for k, v in intervals.items()],
        value='1d',
        style={'width': '300px', 'marginTop': '10px'}
    ),
    html.Button(
        'Analyser',
        id='analyze-button',
        n_clicks=0,
        className='btn btn-primary mt-2'
    ),
    html.Div(id='results', className='mt-4'),
    dcc.Graph(id='chart')
], fluid=True)

def detect_levels(df, window=5):
    levels = []
    for i in range(window, len(df) - window):
        low = df['Low'].iloc[i].item() if hasattr(df['Low'].iloc[i], 'item') else df['Low'].iloc[i]
        high = df['High'].iloc[i].item() if hasattr(df['High'].iloc[i], 'item') else df['High'].iloc[i]

        is_support = all(
            (low < df['Low'].iloc[i - j].item() if hasattr(df['Low'].iloc[i - j], 'item') else df['Low'].iloc[i - j]) and
            (low < df['Low'].iloc[i + j].item() if hasattr(df['Low'].iloc[i + j], 'item') else df['Low'].iloc[i + j])
            for j in range(1, window + 1)
        )
        is_resistance = all(
            (high > df['High'].iloc[i - j].item() if hasattr(df['High'].iloc[i - j], 'item') else df['High'].iloc[i - j]) and
            (high > df['High'].iloc[i + j].item() if hasattr(df['High'].iloc[i + j], 'item') else df['High'].iloc[i + j])
            for j in range(1, window + 1)
        )

        if is_support:
            levels.append((df.index[i], low))
        if is_resistance:
            levels.append((df.index[i], high))
    return levels

@app.callback(
    Output('results', 'children'),
    Output('chart', 'figure'),
    Input('analyze-button', 'n_clicks'),
    State('pair-selector', 'value'),
    State('interval-selector', 'value')
)
def run_analysis(n, symbol, interval):
    if not symbol:
        return "Sélectionnez une paire", go.Figure()

    period = "60d"
    if interval.endswith("m"):
        period = "7d"  # pour les données intraday

    df = yf.download(symbol, period=period, interval=interval)
    if df.empty:
        return "Données non disponibles.", go.Figure()
    df.dropna(inplace=True)

    if df.empty or any(col not in df.columns for col in ['Open', 'High', 'Low', 'Close']):
        return "Données insuffisantes pour afficher le graphique.", go.Figure()

    if df[['Open', 'High', 'Low', 'Close']].nunique().sum() == 0:
        return "Pas de variation de prix suffisante pour afficher les bougies.", go.Figure()

    df.index = pd.to_datetime(df.index)
    close = df['Close'].squeeze()

    df['RSI'] = ta.momentum.RSIIndicator(close).rsi()
    macd = ta.trend.MACD(close)
    df['MACD'] = macd.macd()
    df['MACD_signal'] = macd.macd_signal()
    df['SMA_50'] = ta.trend.SMAIndicator(close, 50).sma_indicator()
    df['SMA_200'] = ta.trend.SMAIndicator(close, 200).sma_indicator()

    entry = float(df['Close'].iloc[-1].item())
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

    levels = detect_levels(df)

    df['High'] = df[['High', 'Low']].max(axis=1) + 0.0001
    df['Low'] = df[['High', 'Low']].min(axis=1) - 0.0001

    fig = go.Figure()

    try:
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name="Bougies",
            increasing_line_color='lime',
            decreasing_line_color='red',
            increasing_line_width=3,
            decreasing_line_width=3
        ))
    except Exception as e:
        print("Erreur bougies :", e)

    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['Close'],
        mode='lines',
        name='Clôture',
        line=dict(color='white', width=1, dash='dot')
    ))

    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['SMA_50'],
        mode='lines',
        name='SMA 50',
        line=dict(color='blue', width=1)
    ))

    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['SMA_200'],
        mode='lines',
        name='SMA 200',
        line=dict(color='orange', width=1)
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
        title=f"Analyse : {symbol} - {interval}",
        xaxis_title="Date",
        yaxis_title="Prix",
        xaxis_rangeslider_visible=False,
        yaxis=dict(domain=[0.25, 1]),
        yaxis2=dict(domain=[0, 0.2], showgrid=False),
        dragmode='zoom',
        xaxis=dict(fixedrange=False),
        height=700,
        template="plotly_dark"
    )

    # 🔧 Forcer une plage visuelle même en cas de prix plats
    min_price = df['Low'].min()
    max_price = df['High'].max()
    if max_price - min_price < 0.01:
        center = (max_price + min_price) / 2
        min_price = center - 0.01
        max_price = center + 0.01

    fig.update_yaxes(range=[min_price, max_price], fixedrange=False)

    return html.Div([
        html.P(f"Entrée : {entry:.2f} € | SL : {sl:.2f} € | TP : {tp:.2f} €"),
        html.P(f"Risque/Rendement : {rr}"),
        html.Ul([html.Li(alert) for alert in alerts]) if alerts else html.P("Aucune alerte détectée.")
    ]), fig
