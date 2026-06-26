#!/usr/bin/env python3
"""
Johann's Portfolio Tracker
Birthday Investment Portfolio Dashboard Generator

Investment date: 23 June 2026
Birthday capital: 13,000 EUR (three equities + cash); LEO Coin held separately.
"""

import warnings
warnings.filterwarnings("ignore")

import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import date, datetime, timedelta
import sys

# ═══════════════════════════════════════════════════════════════════════════════
# PORTFOLIO CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

START_DATE = date(2026, 6, 23)
# Uninvested cash held since inception (stored statically, like each holding's
# cost basis). The three equities cost ~€7,128, which with this cash makes up
# the €13,000 birthday capital; LEO Coin is an additional holding on top.
INITIAL_CASH = 5_871.95  # EUR

HOLDINGS = {
    "VWRD.L": {
        "name": "FTSE All World ETF (VWRD)",
        "isin": "IE00B3RBWM25",
        "units": 31.541,
        "initial_price_eur": 158.5,
        "currency": "USD",  # VWRD.L (USD-distributing) quotes in US dollars on the LSE
        "asset_type": "Benchmark ETF",
    },
    "RHM.DE": {
        "name": "Rheinmetall AG",
        "isin": "DE0007030009",
        "units": 1.0,
        "initial_price_eur": 1_078.8,
        "currency": "EUR",
        "asset_type": "Individual Equity",
    },
    "TTWO": {
        "name": "Take-Two Interactive",
        "isin": "US8740541094",
        "units": 5.0,
        "initial_price_eur": 210.0,
        "currency": "USD",
        "asset_type": "Individual Equity",
    },
    "LEO-USD": {
        "name": "LEO Coin",
        "isin": "—",
        "units": 150.0,
        "initial_price_eur": 2.0,    # cost basis per coin (drives performance)
        "currency": "USD",           # LEO-USD quotes in US dollars
        "asset_type": "Crypto",
    },
}

# Tickers that represent listed equity (used for country-exposure analytics,
# which does not apply to crypto holdings).
EQUITY_TICKERS = [t for t, h in HOLDINGS.items() if h["asset_type"] != "Crypto"]

ECB_DEPOSIT_RATE = 0.0225  # 2.25 % p.a.

INITIAL_INVESTED = sum(h["units"] * h["initial_price_eur"] for h in HOLDINGS.values())
INITIAL_EQUITY_INVESTED = sum(
    HOLDINGS[t]["units"] * HOLDINGS[t]["initial_price_eur"] for t in EQUITY_TICKERS
)
# Total cost basis deployed = static cash + every holding's cost basis.
INITIAL_CAPITAL = INITIAL_CASH + INITIAL_INVESTED

# Approximate FTSE All-World country weights (%)
FTSE_COUNTRY_WEIGHTS = {
    "United States": 61.2,
    "Japan": 5.7,
    "Canada": 3.3,
    "Taiwan": 3.2,
    "United Kingdom": 3.1,
    "China": 3.0,
    "South Korea": 2.4,
    "Switzerland": 2.0,
    "Germany": 1.9,
    "France": 1.9,
    "Australia": 1.6,
    "India": 1.6,
    "Netherlands": 1.4,
    "Other": 5.7,
}

COUNTRY_ISO3 = {
    "United States": "USA", "Japan": "JPN", "Canada": "CAN",
    "Taiwan": "TWN", "United Kingdom": "GBR", "China": "CHN",
    "South Korea": "KOR", "Switzerland": "CHE", "Germany": "DEU",
    "France": "FRA", "Australia": "AUS", "India": "IND",
    "Netherlands": "NLD", "Brazil": "BRA", "South Africa": "ZAF",
    "Saudi Arabia": "SAU", "Denmark": "DNK", "Sweden": "SWE",
    "Spain": "ESP", "Singapore": "SGP", "Italy": "ITA",
    "Hong Kong": "HKG", "Israel": "ISR", "Norway": "NOR",
}

STOCK_COUNTRY = {
    "RHM.DE": "Germany",
    "TTWO": "United States",
}

# ─── Chart colours ─────────────────────────────────────────────────────────────
C = {
    "bg": "#0d1117",
    "card": "#161b22",
    "border": "#30363d",
    "primary": "#58a6ff",
    "green": "#3fb950",
    "red": "#f85149",
    "yellow": "#d29922",
    "text": "#c9d1d9",
    "muted": "#8b949e",
    "VWRD.L": "#58a6ff",
    "RHM.DE": "#f0c040",
    "TTWO": "#f78166",
    "LEO-USD": "#bc8cff",
    "cash": "#56d364",
    "Risk-Free (Cash)": "#56d364",
    "Benchmark ETF": "#58a6ff",
    "Individual Equity": "#f78166",
    "Crypto": "#bc8cff",
}

PLOTLY_LAYOUT = dict(
    paper_bgcolor=C["bg"],
    plot_bgcolor=C["card"],
    font=dict(color=C["text"], family="Inter, system-ui, sans-serif"),
    margin=dict(l=16, r=16, t=40, b=16),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor=C["border"], borderwidth=1),
)


# ═══════════════════════════════════════════════════════════════════════════════
# DATA FETCHING
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_data() -> pd.DataFrame:
    """Download daily close prices for all assets + FX pairs."""
    fetch_start = (datetime.combine(START_DATE, datetime.min.time()) - timedelta(days=7)).strftime("%Y-%m-%d")
    fetch_end   = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")

    tickers = list(HOLDINGS.keys()) + ["GBPEUR=X", "EURUSD=X"]
    print(f"  Fetching prices {fetch_start} to {date.today()} ...")

    raw = yf.download(tickers, start=fetch_start, end=fetch_end,
                      auto_adjust=True, progress=False)

    close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw
    close = close.ffill().bfill()

    # Keep only rows from START_DATE onward
    close = close[close.index >= pd.Timestamp(START_DATE)]
    if close.empty:
        sys.exit("ERROR: No price data available from the investment start date.")
    return close


def prices_to_eur(close: pd.DataFrame) -> pd.DataFrame:
    """
    Return each holding's market value in EUR per unit by converting the raw
    Yahoo Finance quote from its native currency.

    The cost basis (``initial_price_eur``) is used only to measure performance,
    never to value a position — so each holding is always shown at its true live
    price, regardless of what it was bought for.
    """
    gbpeur = close.get("GBPEUR=X", pd.Series(1.0, index=close.index))
    eurusd = close.get("EURUSD=X", pd.Series(1.0, index=close.index))

    eur = pd.DataFrame(index=close.index)
    for ticker, h in HOLDINGS.items():
        if ticker not in close.columns:
            eur[ticker] = h["initial_price_eur"]  # no feed: fall back to cost basis
            continue
        p = close[ticker]
        cur = h["currency"]
        if cur == "USD":
            eur[ticker] = p / eurusd          # USD → EUR (eurusd = USD per EUR)
        elif cur == "GBP":
            eur[ticker] = p * gbpeur          # GBP → EUR
        elif cur == "GBp":
            eur[ticker] = p / 100 * gbpeur    # pence → GBP → EUR
        else:                                 # EUR — already in target currency
            eur[ticker] = p
    return eur


def build_portfolio_series(close: pd.DataFrame) -> pd.DataFrame:
    """Build daily portfolio valuation in EUR."""
    eur = prices_to_eur(close)
    start_ts = pd.Timestamp(START_DATE)

    records = []
    for dt, row in eur.iterrows():
        days = max((dt - start_ts).days, 0)
        cash = INITIAL_CASH * (1 + ECB_DEPOSIT_RATE / 365) ** days
        holdings_values = {t: HOLDINGS[t]["units"] * row[t] for t in HOLDINGS}
        total = cash + sum(holdings_values.values())
        records.append({"date": dt, "cash": cash, **holdings_values, "total": total})

    df = pd.DataFrame(records).set_index("date")
    return df


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════════

def benchmark_returns(portfolio: pd.DataFrame) -> pd.DataFrame:
    """Cumulative % return of each position measured against its cost basis."""
    labels = {
        "VWRD.L": "FTSE All World (Benchmark)",
        "RHM.DE": "Rheinmetall",
        "TTWO": "Take-Two Interactive",
        "LEO-USD": "LEO Coin",
    }
    out = {}
    for ticker, label in labels.items():
        cost = HOLDINGS[ticker]["units"] * HOLDINGS[ticker]["initial_price_eur"]
        out[label] = (portfolio[ticker] / cost - 1) * 100
    return pd.DataFrame(out)


def country_exposure(portfolio: pd.DataFrame) -> pd.Series:
    """Blended equity-only country exposure (%)."""
    latest = portfolio.iloc[-1]
    total_equity = sum(latest[t] for t in EQUITY_TICKERS)

    exp: dict[str, float] = {}
    vwrd_w = latest["VWRD.L"] / total_equity
    for country, pct in FTSE_COUNTRY_WEIGHTS.items():
        exp[country] = exp.get(country, 0) + vwrd_w * pct

    for ticker in ["RHM.DE", "TTWO"]:
        w = latest[ticker] / total_equity
        c = STOCK_COUNTRY[ticker]
        exp[c] = exp.get(c, 0) + w * 100

    return pd.Series(exp).sort_values(ascending=False)


# ═══════════════════════════════════════════════════════════════════════════════
# CHARTS
# ═══════════════════════════════════════════════════════════════════════════════

def chart_networth(portfolio: pd.DataFrame) -> str:
    latest = portfolio.iloc[-1]
    total_return_pct = (latest["total"] / INITIAL_CAPITAL - 1) * 100
    color = C["green"] if total_return_pct >= 0 else C["red"]

    fig = go.Figure()

    def hex_to_rgba(hex_color: str, alpha: float = 0.4) -> str:
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b},{alpha})"

    # Stacked area per component
    components = [
        ("cash",    "Risk-Free (Cash)",          C["cash"]),
        ("VWRD.L",  "FTSE All World ETF",         C["VWRD.L"]),
        ("RHM.DE",  "Rheinmetall AG",             C["RHM.DE"]),
        ("TTWO",    "Take-Two Interactive",        C["TTWO"]),
        ("LEO-USD", "LEO Coin (Crypto)",          C["LEO-USD"]),
    ]
    cum = pd.Series(0.0, index=portfolio.index)
    for col, label, clr in components:
        cum = cum + portfolio[col]
        fig.add_trace(go.Scatter(
            x=portfolio.index, y=cum,
            name=label, fill="tonexty" if label != "Risk-Free (Cash)" else "tozeroy",
            mode="lines",
            line=dict(color=clr, width=1),
            fillcolor=hex_to_rgba(clr),
            hovertemplate="%{x|%d %b %Y}<br>" + label + ": €%{y:,.2f}<extra></extra>",
        ))

    # Total line
    fig.add_trace(go.Scatter(
        x=portfolio.index, y=portfolio["total"],
        name="Total Portfolio", mode="lines",
        line=dict(color="white", width=2, dash="dot"),
        hovertemplate="%{x|%d %b %Y}<br>Total: €%{y:,.2f}<extra></extra>",
    ))

    # Initial capital reference line
    fig.add_hline(y=INITIAL_CAPITAL, line=dict(color=C["muted"], dash="dash", width=1),
                  annotation_text=f"Cost basis €{INITIAL_CAPITAL:,.0f}", annotation_font_color=C["muted"])

    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text="Portfolio Net Worth", font=dict(size=16)),
        xaxis=dict(gridcolor=C["border"], zeroline=False),
        yaxis=dict(gridcolor=C["border"], zeroline=False, tickprefix="€", tickformat=",.0f"),
        hovermode="x unified",
        height=380,
    )
    return fig.to_html(full_html=False, include_plotlyjs=False)


def chart_allocation(portfolio: pd.DataFrame) -> str:
    latest = portfolio.iloc[-1]
    total = latest["total"]

    labels = ["Risk-Free (Cash)", "Benchmark ETF", "Individual Equity", "Crypto"]
    values = [
        latest["cash"],
        latest["VWRD.L"],
        latest["RHM.DE"] + latest["TTWO"],
        latest["LEO-USD"],
    ]
    colors = [C["Risk-Free (Cash)"], C["Benchmark ETF"], C["Individual Equity"], C["Crypto"]]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        marker=dict(colors=colors, line=dict(color=C["bg"], width=2)),
        hole=0.55,
        textinfo="label+percent",
        textfont=dict(color=C["text"], size=12),
        hovertemplate="%{label}<br>€%{value:,.2f}<br>%{percent}<extra></extra>",
    ))
    fig.add_annotation(
        text=f"€{total:,.0f}",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=18, color="white"),
    )
    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text="Total Asset Allocation", font=dict(size=16)),
        showlegend=True,
        height=380,
    )
    return fig.to_html(full_html=False, include_plotlyjs=False)


def chart_benchmark(bench: pd.DataFrame) -> str:
    colors = {
        "FTSE All World (Benchmark)": C["VWRD.L"],
        "Rheinmetall": C["RHM.DE"],
        "Take-Two Interactive": C["TTWO"],
        "LEO Coin": C["LEO-USD"],
    }
    fig = go.Figure()
    fig.add_hline(y=0, line=dict(color=C["muted"], dash="dash", width=1))

    for col in bench.columns:
        fig.add_trace(go.Scatter(
            x=bench.index, y=bench[col],
            name=col, mode="lines+markers",
            line=dict(color=colors.get(col, C["primary"]), width=2),
            marker=dict(size=5),
            hovertemplate="%{x|%d %b %Y}<br>" + col + ": %{y:+.2f}%<extra></extra>",
        ))

    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text="Individual Picks vs Benchmark (% return vs cost basis)", font=dict(size=16)),
        xaxis=dict(gridcolor=C["border"], zeroline=False),
        yaxis=dict(gridcolor=C["border"], zeroline=True, ticksuffix="%",
                   zerolinecolor=C["border"]),
        hovermode="x unified",
        height=340,
    )
    return fig.to_html(full_html=False, include_plotlyjs=False)


def chart_country_map(exposure: pd.Series) -> str:
    # Exclude "Other" bucket (no ISO code)
    mapped = exposure.drop("Other", errors="ignore")
    iso = [COUNTRY_ISO3.get(c) for c in mapped.index]
    valid = [(c, i, v) for c, i, v in zip(mapped.index, iso, mapped.values) if i]
    if not valid:
        return "<p>No country data available.</p>"

    countries, isos, values = zip(*valid)

    # Log-transform z so low-weight countries stay visually distinct despite
    # the USA outlier dominating the linear scale (same effect as reference).
    raw_values = np.array(list(values), dtype=float)
    z_log = np.log1p(raw_values)
    z_log_norm = z_log / z_log.max()  # 0-1

    # Colorscale matching reference: pale-green → green → orange → red → near-black
    colorscale = [
        [0.00, "#f7fbe8"],
        [0.05, "#c5e09a"],
        [0.15, "#8dc87a"],
        [0.30, "#f5a623"],
        [0.50, "#e04010"],
        [0.70, "#980000"],
        [1.00, "#1a0000"],
    ]

    # Build colorbar tick positions in log-normalised space at round % values
    tick_pcts = [0.0, 0.2, 0.9, 2.1, 3.7, 5.7, round(raw_values.max(), 1)]
    tick_vals = [np.log1p(p) / z_log.max() for p in tick_pcts]
    tick_text = [f"{p:.1f}%" for p in tick_pcts]

    fig = go.Figure(go.Choropleth(
        locations=list(isos),
        z=z_log_norm.tolist(),
        text=list(countries),
        customdata=raw_values.tolist(),
        colorscale=colorscale,
        zmin=0,
        zmax=1,
        marker=dict(line=dict(color=C["bg"], width=0.5)),
        colorbar=dict(
            title=dict(text="% equity", side="right", font=dict(color=C["text"])),
            tickvals=tick_vals,
            ticktext=tick_text,
            tickfont=dict(color=C["text"]),
            bgcolor="rgba(0,0,0,0)",
            outlinecolor=C["border"],
            outlinewidth=1,
            len=0.75,
        ),
        hovertemplate="%{text}<br>%{customdata:.1f}%<extra></extra>",
    ))

    fig.update_geos(
        projection_type="natural earth",
        showland=True, landcolor="#1c2128",
        showocean=True, oceancolor=C["bg"],
        showframe=False, showcountries=True,
        countrycolor=C["border"],
        bgcolor=C["bg"],
    )
    layout = {**PLOTLY_LAYOUT, "margin": dict(l=0, r=0, t=40, b=0)}
    fig.update_layout(
        **layout,
        title=dict(text="Portfolio Country Exposure (Equity)", font=dict(size=16)),
        height=420,
    )
    return fig.to_html(full_html=False, include_plotlyjs=False)


def chart_top_countries(exposure: pd.Series) -> str:
    top = exposure.drop("Other", errors="ignore").nlargest(12)
    colors = [C["red"] if c == "United States" else C["primary"] for c in top.index]

    fig = go.Figure(go.Bar(
        x=top.values,
        y=top.index,
        orientation="h",
        marker=dict(color=colors),
        text=[f"{v:.1f}%" for v in top.values],
        textposition="auto",
        textfont=dict(color="white"),
        hovertemplate="%{y}: %{x:.2f}%<extra></extra>",
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text="Top 12 Country Exposures", font=dict(size=16)),
        xaxis=dict(gridcolor=C["border"], ticksuffix="%", zeroline=False),
        yaxis=dict(gridcolor=C["border"], zeroline=False, autorange="reversed"),
        height=420,
    )
    return fig.to_html(full_html=False, include_plotlyjs=False)


# ═══════════════════════════════════════════════════════════════════════════════
# HTML DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

def kpi_card(label: str, value: str, sub: str = "", color: str = "white") -> str:
    return f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value" style="color:{color}">{value}</div>
        <div class="kpi-sub">{sub}</div>
    </div>"""


def build_dashboard(portfolio: pd.DataFrame, bench: pd.DataFrame, exposure: pd.Series) -> str:
    latest = portfolio.iloc[-1]
    total = latest["total"]
    total_ret_pct = (total / INITIAL_CAPITAL - 1) * 100
    total_ret_eur = total - INITIAL_CAPITAL

    # KPI values per position
    pos_returns = []
    for ticker, h in HOLDINGS.items():
        initial_val = h["units"] * h["initial_price_eur"]
        current_val = latest[ticker]
        ret_pct = (current_val / initial_val - 1) * 100
        ret_eur = current_val - initial_val
        pos_returns.append((h["name"], current_val, ret_pct, ret_eur, h["asset_type"]))

    cash_interest = latest["cash"] - INITIAL_CASH
    total_ret_color = C["green"] if total_ret_pct >= 0 else C["red"]

    # Chart HTML
    html_networth    = chart_networth(portfolio)
    html_allocation  = chart_allocation(portfolio)
    html_benchmark   = chart_benchmark(bench)
    html_map         = chart_country_map(exposure)
    html_countries   = chart_top_countries(exposure)

    # KPI row
    kpi_row = "".join([
        kpi_card("Total Portfolio Value", f"€{total:,.2f}",
                 f"Initial: €{INITIAL_CAPITAL:,.0f}"),
        kpi_card("Total Return",
                 f"{total_ret_pct:+.2f}%",
                 f"{'▲' if total_ret_eur >= 0 else '▼'} €{total_ret_eur:+,.2f} total return",
                 total_ret_color),
        kpi_card("Cash (ECB 2.25%)", f"€{latest['cash']:,.2f}",
                 f"Interest earned: €{cash_interest:,.2f}", C["green"]),
        kpi_card("Equity Value", f"€{sum(latest[t] for t in EQUITY_TICKERS):,.2f}",
                 f"of €{INITIAL_EQUITY_INVESTED:,.2f} invested"),
    ])

    # Position cards
    pos_cards = ""
    for name, val, ret_pct, ret_eur, atype in pos_returns:
        clr = C["green"] if ret_pct >= 0 else C["red"]
        arrow = "▲" if ret_eur >= 0 else "▼"
        pos_cards += f"""
        <div class="pos-card">
            <div class="pos-type">{atype}</div>
            <div class="pos-name">{name}</div>
            <div class="pos-value">€{val:,.2f}</div>
            <div class="pos-return" style="color:{clr}">{arrow} {ret_pct:+.2f}% &nbsp;(€{ret_eur:+,.2f})</div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Johann's Portfolio Dashboard</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js" charset="utf-8"></script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  :root {{
    --bg: {C["bg"]};
    --card: {C["card"]};
    --border: {C["border"]};
    --text: {C["text"]};
    --muted: {C["muted"]};
    --green: {C["green"]};
    --red: {C["red"]};
    --primary: {C["primary"]};
  }}
  body {{ background: var(--bg); color: var(--text); font-family: 'Inter', sans-serif; min-height: 100vh; }}
  header {{
    background: linear-gradient(135deg, #0d1117 0%, #161b22 100%);
    border-bottom: 1px solid var(--border);
    padding: 24px 32px;
    display: flex; justify-content: space-between; align-items: center;
  }}
  header h1 {{ font-size: 22px; font-weight: 700; color: white; }}
  header h1 span {{ color: var(--primary); }}
  header .subtitle {{ font-size: 13px; color: var(--muted); margin-top: 4px; }}
  header .stamp {{
    background: var(--card); border: 1px solid var(--border);
    border-radius: 8px; padding: 8px 16px; text-align: right; font-size: 12px;
  }}
  header .stamp strong {{ display: block; font-size: 14px; color: white; }}

  main {{ max-width: 1600px; margin: 0 auto; padding: 24px 32px; }}

  .kpi-row {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }}
  .kpi-card {{
    background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 20px;
  }}
  .kpi-label {{ font-size: 11px; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); margin-bottom: 6px; }}
  .kpi-value {{ font-size: 26px; font-weight: 700; color: white; }}
  .kpi-sub {{ font-size: 12px; color: var(--muted); margin-top: 4px; }}

  .pos-row {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 24px; }}
  .pos-card {{
    background: var(--card); border: 1px solid var(--border); border-radius: 10px;
    padding: 16px 20px;
  }}
  .pos-type {{ font-size: 10px; text-transform: uppercase; letter-spacing: .1em; color: var(--muted); margin-bottom: 4px; }}
  .pos-name {{ font-size: 14px; font-weight: 600; color: white; margin-bottom: 8px; }}
  .pos-value {{ font-size: 20px; font-weight: 700; }}
  .pos-return {{ font-size: 13px; margin-top: 4px; font-weight: 500; }}

  .chart-card {{
    background: var(--card); border: 1px solid var(--border); border-radius: 10px;
    padding: 4px; margin-bottom: 24px; overflow: hidden;
  }}
  .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 24px; }}
  .grid-map {{ display: grid; grid-template-columns: 2fr 1fr; gap: 24px; margin-bottom: 24px; }}

  footer {{
    border-top: 1px solid var(--border); text-align: center;
    padding: 16px; font-size: 11px; color: var(--muted);
  }}
  @media (max-width: 900px) {{
    .kpi-row {{ grid-template-columns: repeat(2,1fr); }}
    .pos-row, .grid-2, .grid-map {{ grid-template-columns: 1fr; }}
  }}
</style>
</head>
<body>

<header>
  <div>
    <h1>Johann's <span>Portfolio</span> Dashboard</h1>
    <div class="subtitle">Birthday Investment · Started 23 June 2026 · Cost Basis: €{INITIAL_CAPITAL:,.0f}</div>
  </div>
  <div class="stamp">
    <strong>Last updated</strong>
    {datetime.now().strftime("%d %b %Y, %H:%M")}
  </div>
</header>

<main>

  <!-- KPI row -->
  <div class="kpi-row">{kpi_row}</div>

  <!-- Position cards -->
  <div class="pos-row">{pos_cards}</div>

  <!-- Net worth chart -->
  <div class="chart-card">{html_networth}</div>

  <!-- Allocation + Benchmark -->
  <div class="grid-2">
    <div class="chart-card">{html_allocation}</div>
    <div class="chart-card">{html_benchmark}</div>
  </div>

  <!-- Country map + bar chart -->
  <div class="grid-map">
    <div class="chart-card">{html_map}</div>
    <div class="chart-card">{html_countries}</div>
  </div>

</main>

<footer>
  Data sourced from Yahoo Finance via yfinance · ECB deposit facility rate {ECB_DEPOSIT_RATE*100:.2f}% p.a. ·
  FTSE All-World country weights approximate · For informational purposes only
</footer>

</body>
</html>"""
    return html


# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUT / EXPORT
# ═══════════════════════════════════════════════════════════════════════════════

def find_chrome() -> str | None:
    """Locate a Chrome/Chromium executable, or None if unavailable."""
    import os, sys, shutil
    if sys.platform == "win32":
        for exe in (
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ):
            if os.path.exists(exe):
                return exe
    return (shutil.which("google-chrome") or shutil.which("chrome")
            or shutil.which("chromium") or shutil.which("chromium-browser"))


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("\nJohann's Portfolio Tracker")
    print(f"   Investment date : {START_DATE}")
    print(f"   Initial capital : EUR {INITIAL_CAPITAL:,.2f}")
    print(f"   Invested        : EUR {INITIAL_INVESTED:,.2f}")
    print(f"   Cash (ECB 2.25%): EUR {INITIAL_CASH:,.2f}\n")

    print("Fetching live market data ...")
    close   = fetch_data()
    portfolio = build_portfolio_series(close)
    bench     = benchmark_returns(portfolio)
    exposure  = country_exposure(portfolio)

    latest = portfolio.iloc[-1]
    total  = latest["total"]
    ret    = (total / INITIAL_CAPITAL - 1) * 100
    print(f"\nLatest snapshot ({portfolio.index[-1].date()})")
    print(f"   Portfolio value : EUR {total:,.2f}")
    print(f"   Total return    : {ret:+.2f}%")
    for ticker, h in HOLDINGS.items():
        v = latest[ticker]
        r = (v / (h["units"] * h["initial_price_eur"]) - 1) * 100
        print(f"   {h['name']:<28}: EUR {v:,.2f}  ({r:+.2f}%)")
    print(f"   Cash            : EUR {latest['cash']:,.2f}")

    print("\nBuilding dashboard ...")
    html = build_dashboard(portfolio, bench, exposure)

    out_path = "dashboard.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Dashboard saved -> {out_path}")

    import webbrowser, os, subprocess
    abs_path = os.path.abspath(out_path)
    url = f"file:///{abs_path.replace(os.sep, '/')}"

    chrome = find_chrome()
    if chrome:
        subprocess.Popen([chrome, url])
    else:
        webbrowser.open(url)
    print("Dashboard opened in browser.\n")


if __name__ == "__main__":
    main()
