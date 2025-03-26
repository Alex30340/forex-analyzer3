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
    '4 Heures (H4)': '60m',
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
    html.Button('Analyser', id='analyze-button', n_clicks=0, className='btn btn-primary mt-2'),
    html.Div(id='results', className='mt-4'),
    dcc.Graph(id='chart'),
    html.Hr(),
    html.H4("Graphique interactif TradingView"),
    html.Div(id='tv-container')
], fluid=True)

@app.callback(
    Output('tv-container', 'children'),
    Input('pair-selector', 'value')
)
def update_tv_widget(symbol):
    tv_symbol_map = {
        'BTC-USD': 'BINANCE:BTCUSDT',
        'GC=F': 'TVC:GOLD',
        'GBPJPY=X': 'FX:GBPJPY',
        'EURNZD=X': 'FX:EURNZD',
        'EURCAD=X': 'FX:EURCAD'
    }
    tv_symbol = tv_symbol_map.get(symbol, 'BINANCE:BTCUSDT')
    iframe_code = f'''
        <div id="tradingview_widget"></div>
        <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
        <script type="text/javascript">
          new TradingView.widget({{
            "width": "100%",
            "height": 500,
            "symbol": "{tv_symbol}",
            "interval": "D",
            "timezone": "Etc/UTC",
            "theme": "dark",
            "style": "1",
            "locale": "fr",
            "toolbar_bg": "#f1f3f6",
            "enable_publishing": false,
            "withdateranges": true,
            "hide_side_toolbar": false,
            "allow_symbol_change": true,
            "save_image": false,
            "container_id": "tradingview_widget"
          }});
        </script>
    '''
    return html.Iframe(
        srcDoc=iframe_code,
        style={"border": "none", "width": "100%", "height": "550px"},
    )

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
        period = "7d"

    df = yf.download(symbol, period=period, interval=interval)
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

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name="Bougies"
    ))
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], mode='lines', name='SMA 50'))
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA_200'], mode='lines', name='SMA 200'))
    fig.add_hline(y=entry, line_color="blue", line_dash="dot", annotation_text="Entrée", annotation_position="top left")
    fig.add_hline(y=tp, line_color="green", line_dash="dash", annotation_text="TP", annotation_position="top left")
    fig.add_hline(y=sl, line_color="red", line_dash="dash", annotation_text="SL", annotation_position="bottom left")
    fig.update_layout(
        title=f"Analyse : {symbol} - {interval}",
        xaxis_title="Date",
        yaxis_title="Prix",
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        height=600
    )

    return html.Div([
        html.P(f"Entrée : {entry:.2f} € | SL : {sl:.2f} € | TP : {tp:.2f} €"),
        html.P(f"Risque/Rendement : {rr}"),
        html.Ul([html.Li(alert) for alert in alerts]) if alerts else html.P("Aucune alerte détectée.")
    ]), fig
