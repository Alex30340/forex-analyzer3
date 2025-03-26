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
