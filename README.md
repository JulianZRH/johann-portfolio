# Johann's Portfolio Tracker

A single-file Python script that generates a self-contained, interactive HTML
dashboard for a birthday investment portfolio. It pulls live market data from
Yahoo Finance, valuates every holding in **EUR**, models the uninvested cash at
the ECB deposit rate, and renders the whole thing as a dark-themed dashboard
(`dashboard.html`) that opens automatically in your browser.

> Investment start: **23 June 2026** · Birthday capital: **€13,000** (three
> equities + cash) · LEO Coin held separately on top.

---

## What it does

Running `portfolio_tracker.py` performs the following steps:

1. **Fetches prices** — downloads daily close prices for every holding plus the
   `GBPEUR=X` and `EURUSD=X` FX pairs from Yahoo Finance (via `yfinance`),
   starting a few days before the investment date.
2. **Converts to EUR** — each holding's raw quote is converted from its native
   currency (USD or EUR) to EUR at the live FX rate, giving its true market
   value. The cost basis (`initial_price_eur`) is used only to measure
   performance, never to value a position.
3. **Builds a daily portfolio series** — combines holding values with cash that
   compounds daily at the ECB deposit-facility rate. The full rate history is
   fetched from the ECB Data Portal each run and the rate actually in effect on
   each day is applied, so accrued interest stays correct even if the ECB
   changes the rate mid-period (falls back to a flat hardcoded rate if offline).
4. **Runs analytics** — cumulative return of each pick vs. the FTSE All-World
   benchmark, and a blended *equity-only* country exposure (crypto is excluded
   from country analytics).
5. **Renders the dashboard** — KPI cards, per-position cards, a stacked net-worth
   area chart, an asset-allocation donut, a benchmark comparison, and a country
   exposure choropleth + bar chart (all built with Plotly).
6. **Opens it** — writes `dashboard.html` and launches it (Chrome on Windows if
   found, otherwise the default browser).

## Holdings

| Ticker    | Name                       | Units   | Cost basis | Currency | Asset type        |
|-----------|----------------------------|---------|------------|----------|-------------------|
| `VWRD.L`  | FTSE All-World ETF (VWRD)  | 31.541  | €158.50    | USD      | Benchmark ETF     |
| `RHM.DE`  | Rheinmetall AG             | 1.0     | €1,078.80  | EUR      | Individual Equity |
| `TTWO`    | Take-Two Interactive       | 5.0     | €210.00    | USD      | Individual Equity |
| `LEO-USD` | LEO Coin                   | 150.0   | €2.00      | USD      | Crypto            |

The three equities (~€7,128 at cost) plus **€5,871.95 of cash** make up the
€13,000 birthday capital. The cash figure is stored statically (`INITIAL_CASH`)
and accrues interest at the ECB rate. **LEO Coin is an additional holding** held
since inception — its €2.00 cost basis drives its performance figure, while its
value tracks the live `LEO-USD` price.

### Valuation

Every holding is valued at its **live market price** from Yahoo Finance,
converted from its native currency to EUR (`Currency` column above). Cost basis
is only used to compute each position's performance — so a position is always
shown at its real current price, regardless of what it was bought for. This is
what lets LEO Coin (cost €2.00, now ≈€8.14) and Rheinmetall (cost €1,078.80, now
≈€946.60) display correctly even though their cost basis differs from their value.

## Dashboard sections

- **KPI cards** — total portfolio value, total return, cash + interest earned,
  and equity value.
- **Position cards** — current value and return for each holding.
- **Net worth** — stacked area of cash + each holding over time, with a total
  line and the cost-basis reference line (cash + every holding's cost ≈ €13,300).
- **Asset allocation** — donut split across Risk-Free (Cash), Benchmark ETF,
  Individual Equity, and Crypto.
- **Individual shares vs. benchmark ETF** — cumulative % return of each
  individual share (and the VWRD benchmark) measured against its cost basis.
  Crypto is excluded from this comparison.
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

- `START_DATE` / `INITIAL_CASH` — investment date and the static starting cash.
  `INITIAL_CAPITAL` (total cost basis) is derived as cash + every holding's cost.
- `HOLDINGS` — add or edit positions (ticker, units, cost basis in EUR,
  `currency` of the Yahoo quote — `USD`, `EUR`, `GBP`, or `GBp` (pence) — and
  asset type). Set `asset_type` to `"Crypto"` to exclude a holding from the
  equity-only country analytics.
- `ECB_DEPOSIT_RATE` — fallback rate at which idle cash compounds. The script
  fetches the full ECB deposit-facility rate history from the ECB Data Portal
  each run (series `FM/D.U2.EUR.4F.KR.DFR.LEV`) and compounds cash using the
  rate in effect on each day; this constant is only used if the request fails.
- `FTSE_COUNTRY_WEIGHTS` — approximate benchmark country weights for the map.

## Notes

- Prices come from Yahoo Finance and may be delayed; FTSE All-World country
  weights are approximate. For informational purposes only — not financial
  advice.
- Cash interest uses the ECB deposit-facility rate in effect on each day (a
  step function over the rate's change dates), so ECB rate changes during the
  holding period are reflected accurately.
