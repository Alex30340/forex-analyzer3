from dash import html, dcc
from dash.dependencies import Input, Output
from core.app_instance import app
import pages.analyse as analyse
import pages.dashboard as dashboard

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Nav([
        dcc.Link("Analyse", href="/", style={"margin": "10px"}),
        dcc.Link("Portefeuille", href="/dashboard", style={"margin": "10px"})
    ]),
    html.Div(id='page-content')
])

@app.callback(Output('page-content', 'children'), Input('url', 'pathname'))
def display_page(pathname):
    if pathname == '/dashboard':
        return dashboard.layout
    return analyse.layout

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8050)