import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const DEFAULT_START = '2026-01-01'
const DEFAULT_END = '2026-01-31'

function formatNumber(value, digits = 0) {
  if (value === null || value === undefined) return '—'
  return new Intl.NumberFormat('en-GB', {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  }).format(value)
}

function formatTime(value, includeDate = true) {
  if (!value) return 'Not selected'
  return new Intl.DateTimeFormat('en-GB', {
    day: includeDate ? '2-digit' : undefined,
    month: includeDate ? 'short' : undefined,
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'UTC',
    timeZoneName: 'short',
  }).format(new Date(value))
}

function MetricCard({ label, value, unit, detail, tone = 'default' }) {
  return (
    <article className={`metric-card metric-${tone}`}>
      <p className="metric-label">{label}</p>
      <p className="metric-value">{value}<span>{unit}</span></p>
      <p className="metric-detail">{detail}</p>
    </article>
  )
}

function Legend() {
  return (
    <div className="legend" aria-label="Chart legend">
      <span><i className="legend-dot forecast-dot" /> Forecast</span>
      <span><i className="legend-dot actual-dot" /> Actual</span>
    </div>
  )
}

function TimeSeriesChart({ intervals }) {
  const points = intervals.filter((item) => item.forecast_mw !== null && item.forecast_mw !== undefined)
  if (!points.length) {
    return <div className="empty-chart">No matched forecast intervals for this period.</div>
  }

  const width = 900
  const height = 300
  const padding = { top: 24, right: 20, bottom: 42, left: 58 }
  const values = points.flatMap((item) => [item.forecast_mw, item.actual_mw])
  const max = Math.max(...values, 1)
  const x = (index) => padding.left + (index / Math.max(points.length - 1, 1)) * (width - padding.left - padding.right)
  const y = (value) => height - padding.bottom - (value / max) * (height - padding.top - padding.bottom)
  const path = (key) => points.map((item, index) => `${index ? 'L' : 'M'} ${x(index)} ${y(item[key])}`).join(' ')
  const yTicks = [0, 0.25, 0.5, 0.75, 1]

  return (
    <div className="chart-wrap">
      <svg className="chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Forecast and actual wind generation by delivery interval">
        {yTicks.map((tick) => (
          <g key={tick}>
            <line className="grid-line" x1={padding.left} x2={width - padding.right} y1={y(max * tick)} y2={y(max * tick)} />
            <text className="axis-label" x={padding.left - 10} y={y(max * tick) + 4} textAnchor="end">{formatNumber(max * tick / 1000, 0)}k</text>
          </g>
        ))}
        <path className="series forecast-series" d={path('forecast_mw')} />
        <path className="series actual-series" d={path('actual_mw')} />
        {points.map((item, index) => (
          <g key={`${item.delivery_time}-${index}`}>
            <title>{`${formatTime(item.delivery_time)} · Forecast ${formatNumber(item.forecast_mw)} MW · Actual ${formatNumber(item.actual_mw)} MW`}</title>
            <circle className="point forecast-point" cx={x(index)} cy={y(item.forecast_mw)} r="2.5" />
            <circle className="point actual-point" cx={x(index)} cy={y(item.actual_mw)} r="2.5" />
          </g>
        ))}
        <text className="axis-label" x={padding.left} y={height - 12}>Start of selected period</text>
        <text className="axis-label" x={width - padding.right} y={height - 12} textAnchor="end">End of selected period</text>
      </svg>
    </div>
  )
}

function App() {
  const [startDate, setStartDate] = useState(DEFAULT_START)
  const [endDate, setEndDate] = useState(DEFAULT_END)
  const [cutoffHour, setCutoffHour] = useState('23')
  const [data, setData] = useState(null)
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState('')
  const hasLoadedInitially = useRef(false)

  const loadAnalytics = useCallback(async (event) => {
    event?.preventDefault()
    setStatus('loading')
    setError('')
    try {
      const params = new URLSearchParams({ start_date: startDate, end_date: endDate, cutoff_hour: cutoffHour })
      const response = await fetch(`${API_BASE_URL}/api/analytics/summary?${params}`)
      if (!response.ok) {
        const body = await response.json().catch(() => ({}))
        throw new Error(body.detail || `The analytics API returned ${response.status}.`)
      }
      const result = await response.json()
      setData(result)
      setStatus(result.intervals?.length ? 'ready' : 'empty')
    } catch (requestError) {
      setStatus('error')
      setError(requestError.message || 'Unable to load analytics.')
    }
  }, [cutoffHour, endDate, startDate])

  useEffect(() => {
    if (!hasLoadedInitially.current) {
      hasLoadedInitially.current = true
      loadAnalytics()
    }
  }, [loadAnalytics])

  const largestErrors = useMemo(() => (
    [...(data?.intervals || [])]
      .filter((item) => item.absolute_error_mw !== null)
      .sort((a, b) => b.absolute_error_mw - a.absolute_error_mw)
      .slice(0, 5)
  ), [data])

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-mark" aria-hidden="true">W</div>
        <div>
          <p className="eyebrow">ENERGY INTELLIGENCE</p>
          <p className="brand-name">Wind Forecast Analytics</p>
        </div>
        <div className="topbar-status"><span /> Historical view · UK wind</div>
      </header>

      <main>
        <section className="hero">
          <div>
            <p className="eyebrow">JANUARY 2026 PURCHASING REVIEW</p>
            <h1>Forecast confidence,<br /><em>made visible.</em></h1>
            <p className="hero-copy">Compare Elexon wind generation forecasts with actual output and understand the uncertainty behind day-ahead decisions.</p>
          </div>
          <div className="hero-note">
            <span className="note-line" />
            <p>Forecasts are selected using only publications available before the configured day-ahead cutoff.</p>
          </div>
        </section>

        <section className="filter-panel" aria-label="Analytics filters">
          <form onSubmit={loadAnalytics}>
            <div className="filter-field">
              <label htmlFor="start-date">From</label>
              <input id="start-date" type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} />
            </div>
            <div className="filter-arrow" aria-hidden="true">→</div>
            <div className="filter-field">
              <label htmlFor="end-date">To</label>
              <input id="end-date" type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} />
            </div>
            <div className="filter-field cutoff-field">
              <label htmlFor="cutoff-hour">Decision cutoff</label>
              <select id="cutoff-hour" value={cutoffHour} onChange={(event) => setCutoffHour(event.target.value)}>
                <option value="22">22:00 UTC</option>
                <option value="23">23:00 UTC</option>
                <option value="0">00:00 UTC</option>
              </select>
            </div>
            <button type="submit" disabled={status === 'loading'}>{status === 'loading' ? 'Loading…' : 'Update view'} <span>↗</span></button>
          </form>
        </section>

        {status === 'error' && (
          <div className="state-card error-state" role="alert">
            <strong>We could not load this period.</strong>
            <span>{error}</span>
            <button type="button" onClick={loadAnalytics}>Try again</button>
          </div>
        )}
        {status === 'empty' && <div className="state-card"><strong>No intervals found.</strong><span>Try a different date range or check that the backend is running.</span></div>}

        {data && status !== 'error' && (
          <>
            <section className="metrics-grid" aria-label="Summary metrics">
              <MetricCard label="Mean absolute error" value={formatNumber(data.mae_mw)} unit=" MW" detail="Average magnitude of forecast error" tone="accent" />
              <MetricCard label="Root mean squared error" value={formatNumber(data.rmse_mw)} unit=" MW" detail="Weights larger misses more heavily" />
              <MetricCard label="Mean bias" value={formatNumber(data.bias_mw)} unit=" MW" detail={data.bias_mw >= 0 ? 'Positive means overestimation' : 'Negative means underestimation'} tone={data.bias_mw >= 0 ? 'warm' : 'cool'} />
              <MetricCard label="MAPE" value={formatNumber(data.mape_percent, 1)} unit="%" detail="Excludes intervals with zero actual output" />
            </section>

            <section className="chart-card card">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">OUTPUT PROFILE</p>
                  <h2>Forecast vs actual generation</h2>
                </div>
                <Legend />
              </div>
              <TimeSeriesChart intervals={data.intervals} />
              <div className="chart-footer"><span>MW · UTC delivery time</span><span>{data.matched_count} matched · {data.unmatched_count} unmatched intervals</span></div>
            </section>

            <section className="lower-grid">
              <div className="card errors-card">
                <div className="section-heading compact">
                  <div><p className="eyebrow">WHERE TO LOOK</p><h2>Largest forecast errors</h2></div>
                  <span className="count-badge">TOP 5</span>
                </div>
                <div className="error-list">
                  {largestErrors.map((item) => (
                    <div className="error-row" key={item.delivery_time}>
                      <div><strong>{formatNumber(item.absolute_error_mw)} MW</strong><span>{formatTime(item.delivery_time)}</span></div>
                      <div className="error-bar"><i style={{ width: `${Math.max(8, (item.absolute_error_mw / (largestErrors[0]?.absolute_error_mw || 1)) * 100)}%` }} /></div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="card methodology-card">
                <p className="eyebrow">METHODOLOGY</p>
                <h2>Decision-aware by design</h2>
                <p>Each hourly WINDFOR forecast is matched to the two half-hourly actual intervals in its hour. Only the latest publication before {cutoffHour.padStart(2, '0')}:00 UTC on the previous day is eligible.</p>
                <div className="method-rule"><span>error</span><b>=</b><span>forecast − actual</span></div>
              </div>
            </section>

            <section className="card table-card">
              <div className="section-heading">
                <div><p className="eyebrow">INTERVAL DETAIL</p><h2>Delivery observations</h2></div>
                <span className="table-caption">All times shown in UTC</span>
              </div>
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Delivery time</th><th>Forecast published</th><th>Forecast</th><th>Actual</th><th>Signed error</th><th>Absolute error</th></tr></thead>
                  <tbody>
                    {data.intervals.slice(0, 100).map((item) => (
                      <tr key={item.delivery_time}>
                        <td>{formatTime(item.delivery_time)}</td>
                        <td>{formatTime(item.forecast_publish_time)}</td>
                        <td>{formatNumber(item.forecast_mw)} MW</td>
                        <td>{formatNumber(item.actual_mw)} MW</td>
                        <td className={item.error_mw >= 0 ? 'positive' : 'negative'}>{formatNumber(item.error_mw)} MW</td>
                        <td>{formatNumber(item.absolute_error_mw)} MW</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {data.intervals.length > 100 && <p className="table-note">Showing the first 100 intervals in this view.</p>}
            </section>
          </>
        )}
      </main>
      <footer><span>Source: Elexon BMRS · FUELHH + WINDFOR</span><span>Wind Forecast Analytics · v0.1</span></footer>
    </div>
  )
}

export default App
