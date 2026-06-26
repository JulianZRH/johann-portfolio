# Johann's Portfolio Tracker

A single-file Python script that generates a self-contained, interactive HTML
dashboard for a birthday investment portfolio. It pulls live market data from
Yahoo Finance, valuates every holding in **EUR**, models the uninvested cash at
the ECB deposit rate, and renders the whole thing as a dark-themed dashboard
(`dashboard.html`) that opens automatically in your browser.

> Investment start: **23 June 2026** · Initial capital: **€13,000**

---

## What it does

Running `portfolio_tracker.py` performs the following steps:

1. **Fetches prices** — downloads daily close prices for every holding plus the
   `GBPEUR=X` and `EURUSD=X` FX pairs from Yahoo Finance (via `yfinance`),
   starting a few days before the investment date.
2. **Converts to EUR** — each holding's confirmed purchase price (in EUR) is used
   as the base and scaled by the percentage change of the raw quote *and* the
   relevant FX movement. This avoids any assumption about which currency Yahoo
   reports a given ticker in.
3. **Builds a daily portfolio series** — combines holding values with cash that
   compounds daily at the ECB deposit-facility rate (2.25 % p.a.).
4. **Runs analytics** — cumulative return of each pick vs. the FTSE All-World
   benchmark, and a blended *equity-only* country exposure (crypto is excluded
   from country analytics).
5. **Renders the dashboard** — KPI cards, per-position cards, a stacked net-worth
   area chart, an asset-allocation donut, a benchmark comparison, and a country
   exposure choropleth + bar chart (all built with Plotly).
6. **Opens it** — writes `dashboard.html` and launches it (Chrome on Windows if
   found, otherwise the default browser).

## Holdings

| Ticker   | Name                       | Units   | Cost basis | Currency | Asset type        |
|----------|----------------------------|---------|------------|----------|-------------------|
| `VWRD.L` | FTSE All-World ETF (VWRD)  | 31.541  | €158.50    | GBp      | Benchmark ETF     |
| `RHM.DE` | Rheinmetall AG             | 1.0     | €1,078.80  | EUR      | Individual Equity |
| `TTWO`   | Take-Two Interactive       | 5.0     | €210.00    | USD      | Individual Equity |
| `LEO`    | LEO Coin                   | 150.0   | €2.00      | EUR      | Crypto            |

The remainder of the €13,000 (after the invested positions) is held as cash and
accrues interest at the ECB rate.

### Manually-priced holdings

Most holdings are valued live from Yahoo Finance. LEO Coin has no reliable feed,
so it is **valued manually**: `initial_price_eur` is the cost basis (€2.00, drives
performance) and `current_price_eur` is the latest market price (€8.14). Its value
is ramped from cost basis at inception to the current price on the latest date.
To refresh it, edit `current_price_eur` in the `HOLDINGS` config. Any holding can
be made manual by adding `"manual_price": True` with a `current_price_eur`.

## Dashboard sections

- **KPI cards** — total portfolio value, total return, cash + interest earned,
  and equity value.
- **Position cards** — current value and return for each holding.
- **Net worth** — stacked area of cash + each holding over time, with a total
  line and the €13,000 reference line.
- **Asset allocation** — donut split across Risk-Free (Cash), Benchmark ETF,
  Individual Equity, and Crypto.
- **Picks vs. benchmark** — cumulative % return of each pick against VWRD.
- **Country exposure** — choropleth map and top-12 bar chart (equity only).

## Requirements

- Python 3.10+
- Dependencies in [`requirements.txt`](requirements.txt):

```
yfinance>=0.2.40
pandas>=2.0
numpy>=1.26
plotly>=5.22
```

## Usage

```bash
pip install -r requirements.txt
python portfolio_tracker.py
```

This writes `dashboard.html` to the project directory and opens it in your
browser. Re-run any time to refresh with the latest market data.

## Configuration

Everything is configured at the top of `portfolio_tracker.py`:

- `START_DATE` / `INITIAL_CAPITAL` — investment date and starting capital.
- `HOLDINGS` — add or edit positions (ticker, units, cost basis in EUR,
  currency, asset type). Set `asset_type` to `"Crypto"` to exclude a holding
  from the equity-only country analytics. Add `"manual_price": True` plus
  `current_price_eur` to value a holding manually instead of via Yahoo Finance.
- `ECB_DEPOSIT_RATE` — the rate at which idle cash compounds.
- `FTSE_COUNTRY_WEIGHTS` — approximate benchmark country weights for the map.

## Notes

- Prices come from Yahoo Finance and may be delayed; FTSE All-World country
  weights are approximate. For informational purposes only — not financial
  advice.
