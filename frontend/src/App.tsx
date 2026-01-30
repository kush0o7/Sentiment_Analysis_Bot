import { useEffect, useMemo, useState } from 'react'
import Papa from 'papaparse'
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import './App.css'

type RawRow = Record<string, string>

type DataRow = {
  Date: string
  Open?: number
  High?: number
  Low?: number
  Close?: number
  Volume?: number
  sentiment?: number
  signal?: string
  equity?: number
  time?: number
}

const TICKERS = [
  { symbol: 'AAPL', label: 'Apple' },
  { symbol: 'MSFT', label: 'Microsoft' },
  { symbol: 'TSLA', label: 'Tesla' },
  { symbol: 'QQQ', label: 'Invesco QQQ' },
  { symbol: 'SPY', label: 'SPDR S&P 500' },
]

const numberOrUndefined = (value: string | number | null | undefined) => {
  if (value === null || value === undefined) return undefined
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : undefined
}

const formatPct = (value: number | undefined) => {
  if (value === undefined) return '—'
  const pct = value * 100
  const sign = pct > 0 ? '+' : ''
  return `${sign}${pct.toFixed(2)}%`
}

const formatNumber = (value: number | undefined) => {
  if (value === undefined) return '—'
  return value.toLocaleString('en-US', { maximumFractionDigits: 2 })
}

const formatDateLabel = (value: string) => {
  if (!value) return ''
  if (value.length >= 10) {
    return `${value.slice(5, 7)}/${value.slice(8, 10)}`
  }
  return value
}

const formatDateFromMs = (value: number) => {
  if (!Number.isFinite(value)) return ''
  const iso = new Date(value).toISOString().slice(0, 10)
  return formatDateLabel(iso)
}

const parseDateToTime = (value: string | undefined) => {
  if (!value) return undefined
  const cleaned = value.trim()
  let parsed = Date.parse(cleaned)
  if (!Number.isFinite(parsed)) {
    parsed = Date.parse(`${cleaned}T00:00:00Z`)
  }
  return Number.isFinite(parsed) ? parsed : undefined
}

function App() {
  const [ticker, setTicker] = useState(TICKERS[0].symbol)
  const [rows, setRows] = useState<DataRow[]>([])
  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showEquity, setShowEquity] = useState(true)
  const [source, setSource] = useState<'api' | 'csv'>('csv')
  const [period, setPeriod] = useState('6mo')
  const [entity, setEntity] = useState('Warren Buffett')
  const [entityRows, setEntityRows] = useState<DataRow[]>([])
  const [entityLoading, setEntityLoading] = useState(false)
  const [entityError, setEntityError] = useState<string | null>(null)
  const [holdings, setHoldings] = useState<
    { issuer: string; title: string; value: string; shares: string }[]
  >([])
  const [holdingsLoading, setHoldingsLoading] = useState(false)
  const [holdingsError, setHoldingsError] = useState<string | null>(null)
  const [insiders, setInsiders] = useState<
    { filing_date: string; accession: string; document: string }[]
  >([])
  const [insidersLoading, setInsidersLoading] = useState(false)
  const [insidersError, setInsidersError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    setLoading(true)
    setError(null)
    setRows([])

    const loadFromCsv = () =>
      fetch(`/data/${ticker}_merged.csv`).then(async (res) => {
        if (!res.ok) {
          throw new Error(`Missing data for ${ticker} (HTTP ${res.status})`)
        }
        const text = await res.text()
        const parsed = Papa.parse<RawRow>(text, {
          header: true,
          skipEmptyLines: true,
        })
        if (parsed.errors.length) {
          throw new Error(parsed.errors[0].message)
        }
        return parsed.data
          .map((row) => {
            const time = parseDateToTime(row.Date)
            return {
              Date: row.Date,
              Open: numberOrUndefined(row.Open),
              High: numberOrUndefined(row.High),
              Low: numberOrUndefined(row.Low),
              Close: numberOrUndefined(row.Close),
              Volume: numberOrUndefined(row.Volume),
              sentiment: numberOrUndefined(row.sentiment),
              signal: row.signal,
              equity: numberOrUndefined(row.equity),
              time: Number.isFinite(time) ? (time as number) : undefined,
            }
          })
          .filter((row) => Boolean(row.Date))
      })

    const loadFromApi = (forceRefresh = false) =>
      fetch(
        `/api/data?ticker=${ticker}&period=${period}&sentiment_model=vader${forceRefresh ? '&refresh=true' : ''}`,
      ).then(async (res) => {
        if (!res.ok) {
          throw new Error(`API error (HTTP ${res.status})`)
        }
        const json = (await res.json()) as { data?: RawRow[] }
        if (!json.data) {
          throw new Error('API response missing data.')
        }
        return json.data.map((row) => {
          const time = parseDateToTime(row.Date)
          return {
            Date: row.Date,
            Open: numberOrUndefined(row.Open),
            High: numberOrUndefined(row.High),
            Low: numberOrUndefined(row.Low),
            Close: numberOrUndefined(row.Close),
            Volume: numberOrUndefined(row.Volume),
            sentiment: numberOrUndefined(row.sentiment),
            signal: row.signal,
            equity: numberOrUndefined(row.equity),
            time: Number.isFinite(time) ? (time as number) : undefined,
          }
        })
      })

    loadFromApi()
      .then((nextRows) => {
        if (mounted) {
          setRows(nextRows)
          setSource('api')
          setLoading(false)
        }
      })
      .catch(() =>
        loadFromCsv()
          .then((nextRows) => {
            if (mounted) {
              setRows(nextRows)
              setSource('csv')
              setLoading(false)
            }
          })
          .catch((err) => {
            if (mounted) {
              setError(err.message || 'Failed to load data.')
              setLoading(false)
            }
          }),
      )

    return () => {
      mounted = false
    }
  }, [ticker, period])

  useEffect(() => {
    let mounted = true
    setEntityLoading(true)
    setEntityError(null)

    fetch(`/api/entity?name=${encodeURIComponent(entity)}&sentiment_model=vader`)
      .then(async (res) => {
        if (!res.ok) {
          throw new Error(`Entity API error (HTTP ${res.status})`)
        }
        const json = (await res.json()) as { data?: RawRow[] }
        if (!json.data) {
          throw new Error('Entity response missing data.')
        }
        return json.data.map((row) => {
          const time = parseDateToTime(row.Date)
          return {
            Date: row.Date,
            sentiment: numberOrUndefined(row.sentiment),
            time: Number.isFinite(time) ? (time as number) : undefined,
          }
        })
      })
      .then((nextRows) => {
        if (mounted) {
          setEntityRows(nextRows)
          setEntityLoading(false)
        }
      })
      .catch((err) => {
        if (mounted) {
          setEntityError(err.message || 'Failed to load entity data.')
          setEntityLoading(false)
        }
      })

    return () => {
      mounted = false
    }
  }, [entity])

  useEffect(() => {
    let mounted = true
    setHoldingsLoading(true)
    setHoldingsError(null)

    fetch(`/api/holdings?name=${encodeURIComponent(entity)}&max_rows=20`)
      .then(async (res) => {
        if (!res.ok) {
          throw new Error(`Holdings API error (HTTP ${res.status})`)
        }
        const json = (await res.json()) as { holdings?: any[] }
        if (!json.holdings) {
          throw new Error('Holdings response missing data.')
        }
        return json.holdings.map((row) => ({
          issuer: row.issuer,
          title: row.title,
          value: row.value,
          shares: row.shares,
        }))
      })
      .then((rows) => {
        if (mounted) {
          setHoldings(rows)
          setHoldingsLoading(false)
        }
      })
      .catch((err) => {
        if (mounted) {
          setHoldingsError(err.message || 'Failed to load holdings.')
          setHoldingsLoading(false)
        }
      })

    return () => {
      mounted = false
    }
  }, [entity])

  useEffect(() => {
    let mounted = true
    setInsidersLoading(true)
    setInsidersError(null)

    fetch(`/api/insiders?ticker=${ticker}&max_filings=8`)
      .then(async (res) => {
        if (!res.ok) {
          throw new Error(`Insiders API error (HTTP ${res.status})`)
        }
        const json = (await res.json()) as { filings?: any[] }
        if (!json.filings) {
          throw new Error('Insiders response missing data.')
        }
        return json.filings.map((row) => ({
          filing_date: row.filing_date,
          accession: row.accession,
          document: row.document,
        }))
      })
      .then((rows) => {
        if (mounted) {
          setInsiders(rows)
          setInsidersLoading(false)
        }
      })
      .catch((err) => {
        if (mounted) {
          setInsidersError(err.message || 'Failed to load insider filings.')
          setInsidersLoading(false)
        }
      })

    return () => {
      mounted = false
    }
  }, [ticker])

  const stats = useMemo(() => {
    if (!rows.length) {
      return {
        range: '—',
        lastClose: undefined,
        totalReturn: undefined,
        lastSignal: '—',
        equity: undefined,
      }
    }
    const first = rows[0]
    const last = rows[rows.length - 1]
    const totalReturn =
      first.Close && last.Close ? last.Close / first.Close - 1 : undefined
    const equity =
      first.equity && last.equity ? last.equity / first.equity - 1 : undefined
    return {
      range: `${first.Date} → ${last.Date}`,
      lastClose: last.Close,
      totalReturn,
      lastSignal: last.signal || '—',
      equity,
    }
  }, [rows])

  const recentRows = useMemo(() => rows.slice(-12).reverse(), [rows])
  const normalizedRows = useMemo(
    () =>
      rows.map((row) => {
        if (row.time !== undefined) {
          return row
        }
        const parsed = parseDateToTime(row.Date)
        return {
          ...row,
          time: Number.isFinite(parsed) ? (parsed as number) : undefined,
        }
      }),
    [rows],
  )
  const priceRows = useMemo(
    () =>
      normalizedRows
        .filter((row) => row.Close !== undefined && row.time !== undefined)
        .sort((a, b) => (a.time ?? 0) - (b.time ?? 0)),
    [normalizedRows],
  )
  const buyRows = useMemo(
    () => priceRows.filter((row) => row.signal === 'Buy'),
    [priceRows],
  )
  const sellRows = useMemo(
    () => priceRows.filter((row) => row.signal === 'Sell'),
    [priceRows],
  )
  const hasSentiment = useMemo(
    () => rows.some((row) => row.sentiment !== undefined),
    [rows],
  )
  const chartRows = useMemo(
    () =>
      normalizedRows
        .map((row, idx) => ({ ...row, idx }))
        .filter((row) => row.Close !== undefined),
    [normalizedRows],
  )
  const sentimentRows = useMemo(
    () =>
      normalizedRows
        .filter((row) => row.sentiment !== undefined)
        .map((row, idx) => ({ ...row, idx })),
    [normalizedRows],
  )
  const entityChartRows = useMemo(
    () =>
      entityRows
        .filter((row) => row.sentiment !== undefined)
        .map((row, idx) => ({ ...row, idx })),
    [entityRows],
  )
  const formatIndexLabel = (value: number, rowsRef: Array<{ Date: string }>) => {
    const idx = Math.round(value)
    const row = rowsRef[idx]
    return row ? formatDateLabel(row.Date) : ''
  }

  return (
    <div className="page">
      <header className="hero">
        <div className="hero-text">
          <p className="eyebrow">Sentiment Analysis Bot</p>
          <h1>Market Pulse Console</h1>
          <p className="subhead">
            Explore merged price + signal data with a clean, fast TypeScript
            UI. Select a ticker and inspect recent sentiment-driven moves.
          </p>
        </div>
        <div className="hero-card">
          <div className="card-title">Select stock</div>
          <div className="select-row">
            <select
              value={ticker}
              onChange={(event) => setTicker(event.target.value)}
            >
              {TICKERS.map((item) => (
                <option key={item.symbol} value={item.symbol}>
                  {item.symbol} · {item.label}
                </option>
              ))}
            </select>
            <select
              value={period}
              onChange={(event) => setPeriod(event.target.value)}
            >
              <option value="3mo">3 months</option>
              <option value="6mo">6 months</option>
              <option value="1y">1 year</option>
              <option value="2y">2 years</option>
            </select>
            <button
              className="refresh"
              onClick={() => {
                setRefreshing(true)
                setError(null)
                fetch(
                  `/api/data?ticker=${ticker}&period=${period}&sentiment_model=vader&refresh=true`,
                )
                  .then(async (res) => {
                    if (!res.ok) {
                      throw new Error(`API error (HTTP ${res.status})`)
                    }
                    const json = (await res.json()) as { data?: RawRow[] }
                    if (!json.data) {
                      throw new Error('API response missing data.')
                    }
                    return json.data.map((row) => {
                      const time = parseDateToTime(row.Date)
                      return {
                        Date: row.Date,
                        Open: numberOrUndefined(row.Open),
                        High: numberOrUndefined(row.High),
                        Low: numberOrUndefined(row.Low),
                        Close: numberOrUndefined(row.Close),
                        Volume: numberOrUndefined(row.Volume),
                        sentiment: numberOrUndefined(row.sentiment),
                        signal: row.signal,
                        equity: numberOrUndefined(row.equity),
                        time: Number.isFinite(time) ? (time as number) : undefined,
                      }
                    })
                  })
                  .then((nextRows) => {
                    setRows(nextRows)
                    setSource('api')
                  })
                  .catch((err) => {
                    setError(err.message || 'Failed to refresh data.')
                  })
                  .finally(() => {
                    setRefreshing(false)
                  })
              }}
              type="button"
            >
              {refreshing ? 'Refreshing…' : 'Refresh data'}
            </button>
            <label className="toggle">
              <input
                type="checkbox"
                checked={showEquity}
                onChange={(event) => setShowEquity(event.target.checked)}
              />
              <span>Show equity curve</span>
            </label>
          </div>
          <div className="mini-grid">
            <div>
              <span className="mini-label">Date range</span>
              <div className="mini-value">{stats.range}</div>
            </div>
            <div>
              <span className="mini-label">Last close</span>
              <div className="mini-value">{formatNumber(stats.lastClose)}</div>
            </div>
            <div>
              <span className="mini-label">Total return</span>
              <div className="mini-value">{formatPct(stats.totalReturn)}</div>
            </div>
            <div>
              <span className="mini-label">Signal</span>
              <div className="mini-value">{stats.lastSignal}</div>
            </div>
            <div>
              <span className="mini-label">Equity return</span>
              <div className="mini-value">{formatPct(stats.equity)}</div>
            </div>
            <div>
              <span className="mini-label">Source</span>
              <div className="mini-value">{source.toUpperCase()}</div>
            </div>
          </div>
        </div>
      </header>

      <main className="main">
        <section className="panel">
          <div className="panel-header">
            <div>
              <h2>Price trend</h2>
              <p>Daily close with optional equity overlay.</p>
            </div>
            <span className="pill">
              {source === 'api'
                ? 'LIVE: /api/data'
                : `CSV: /data/${ticker}_merged.csv`}
            </span>
          </div>

          <div className="chart-wrap">
            {loading && <div className="status">Loading data…</div>}
            {error && <div className="status error">{error}</div>}
            {!loading && !error && rows.length === 0 && (
              <div className="status">No rows available.</div>
            )}
            {!loading && !error && rows.length > 0 && (
              <ResponsiveContainer width="100%" height={320}>
                <LineChart data={chartRows}>
                  <XAxis
                    dataKey="idx"
                    type="number"
                    domain={[0, Math.max(0, chartRows.length - 1)]}
                    tickFormatter={(value) => formatIndexLabel(value, chartRows)}
                    minTickGap={20}
                  />
                  <YAxis
                    tickFormatter={(value) => Number(value).toFixed(0)}
                    width={50}
                  />
                  <Tooltip />
                  <Line
                    type="linear"
                    dataKey="Close"
                    stroke="#1f6feb"
                    strokeWidth={3}
                    dot={false}
                    connectNulls
                    isAnimationActive={false}
                  />
                  {showEquity && (
                    <Line
                      type="linear"
                      dataKey="equity"
                      stroke="#2bb673"
                      strokeWidth={2}
                      dot={false}
                      connectNulls
                      isAnimationActive={false}
                    />
                  )}
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </section>

        <section className="panel">
          <div className="panel-header">
            <div>
              <h2>Sentiment pulse</h2>
              <p>Smoothed sentiment values aligned to trading days.</p>
            </div>
            <span className="pill">Signals: Buy / Sell markers</span>
          </div>
          <div className="chart-wrap">
            {!hasSentiment && (
              <div className="status">No sentiment column in this CSV.</div>
            )}
            {hasSentiment && (
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={sentimentRows}>
                  <XAxis
                    dataKey="idx"
                    type="number"
                    domain={[0, Math.max(0, sentimentRows.length - 1)]}
                    tickFormatter={(value) => formatIndexLabel(value, sentimentRows)}
                    minTickGap={20}
                  />
                  <YAxis width={50} />
                  <Tooltip />
                  <Line
                    type="monotone"
                    dataKey="sentiment"
                    stroke="#0f172a"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </section>

        <section className="panel">
          <div className="panel-header">
            <div>
              <h2>Market voices</h2>
              <p>News sentiment around notable traders and investors.</p>
            </div>
            <span className="pill">Source: Google News RSS</span>
          </div>
          <div className="select-row">
            <select value={entity} onChange={(event) => setEntity(event.target.value)}>
              <option value="Warren Buffett">Warren Buffett</option>
              <option value="Cathie Wood">Cathie Wood</option>
              <option value="Ray Dalio">Ray Dalio</option>
              <option value="Michael Burry">Michael Burry</option>
              <option value="Bill Ackman">Bill Ackman</option>
              <option value="George Soros">George Soros</option>
            </select>
          </div>
          <div className="chart-wrap">
            {entityLoading && <div className="status">Loading sentiment…</div>}
            {entityError && <div className="status error">{entityError}</div>}
            {!entityLoading && !entityError && entityRows.length === 0 && (
              <div className="status">No sentiment data for this name.</div>
            )}
            {!entityLoading && !entityError && entityRows.length > 0 && (
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={entityChartRows}>
                  <XAxis
                    dataKey="idx"
                    type="number"
                    domain={[0, Math.max(0, entityChartRows.length - 1)]}
                    tickFormatter={(value) => formatIndexLabel(value, entityChartRows)}
                    minTickGap={20}
                  />
                  <YAxis width={50} />
                  <Tooltip />
                  <Line
                    type="monotone"
                    dataKey="sentiment"
                    stroke="#111b2b"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </section>

        <section className="panel">
          <div className="panel-header">
            <div>
              <h2>Institutional holdings (13F)</h2>
              <p>Quarterly reported holdings for the selected investor.</p>
            </div>
            <span className="pill">Source: SEC EDGAR</span>
          </div>
          <div className="table-wrap">
            {holdingsLoading && <div className="status">Loading holdings…</div>}
            {holdingsError && <div className="status error">{holdingsError}</div>}
            {!holdingsLoading && !holdingsError && holdings.length === 0 && (
              <div className="status">No holdings found for this name.</div>
            )}
            {!holdingsLoading && !holdingsError && holdings.length > 0 && (
              <table>
                <thead>
                  <tr>
                    <th>Issuer</th>
                    <th>Class</th>
                    <th>Value ($000)</th>
                    <th>Shares</th>
                  </tr>
                </thead>
                <tbody>
                  {holdings.map((row) => (
                    <tr key={`${row.issuer}-${row.shares}`}>
                      <td>{row.issuer}</td>
                      <td>{row.title}</td>
                      <td>{row.value}</td>
                      <td>{row.shares}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </section>

        <section className="panel">
          <div className="panel-header">
            <div>
              <h2>Insider filings (Form 4)</h2>
              <p>Latest insider filings for the selected ticker.</p>
            </div>
            <span className="pill">Source: SEC EDGAR</span>
          </div>
          <div className="table-wrap">
            {insidersLoading && <div className="status">Loading Form 4 filings…</div>}
            {insidersError && <div className="status error">{insidersError}</div>}
            {!insidersLoading && !insidersError && insiders.length === 0 && (
              <div className="status">No Form 4 filings found.</div>
            )}
            {!insidersLoading && !insidersError && insiders.length > 0 && (
              <table>
                <thead>
                  <tr>
                    <th>Filing date</th>
                    <th>Accession</th>
                    <th>Document</th>
                  </tr>
                </thead>
                <tbody>
                  {insiders.map((row) => (
                    <tr key={row.accession}>
                      <td>{row.filing_date}</td>
                      <td>{row.accession}</td>
                      <td>{row.document}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </section>

        <section className="panel">
          <div className="panel-header">
            <div>
              <h2>Recent rows</h2>
              <p>Latest 12 rows from the merged dataset.</p>
            </div>
            <span className="pill">Rows: {rows.length || 0}</span>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Close</th>
                  <th>Signal</th>
                  <th>Sentiment</th>
                  <th>Equity</th>
                </tr>
              </thead>
              <tbody>
                {recentRows.map((row) => (
                  <tr key={row.Date}>
                    <td>{row.Date}</td>
                    <td>{formatNumber(row.Close)}</td>
                    <td>{row.signal || '—'}</td>
                    <td>{row.sentiment ?? '—'}</td>
                    <td>{formatNumber(row.equity)}</td>
                  </tr>
                ))}
                {!recentRows.length && (
                  <tr>
                    <td colSpan={5}>No data available.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  )
}

export default App
