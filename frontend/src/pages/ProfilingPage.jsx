import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  Columns,
  Table2,
  AlertCircle,
  Copy,
  BarChart2,
  AlertTriangle,
  FileSpreadsheet,
  Upload,
  Loader,
  ArrowRight,
} from 'lucide-react'
import { useDataset } from '../context/DatasetContext'
import styles from './ProfilingPage.module.css'

function getSimpleType(dtype) {
  if (!dtype) return 'Str'
  const dt = String(dtype).toLowerCase()
  if (dt.includes('int')) return 'Int'
  if (dt.includes('float')) return 'Float'
  if (dt.includes('date') || dt.includes('time')) return 'Date'
  return 'Str'
}

const typeBadgeClass = {
  Int: 'badge badge-blue',
  Str: 'badge badge-purple',
  Float: 'badge badge-green',
  Date: 'badge badge-yellow',
}

const tabs = [
  { key: 'overview',   label: 'Overview'       },
  { key: 'missing',    label: 'Missing Values' },
  { key: 'duplicates', label: 'Duplicates'     },
  { key: 'outliers',   label: 'Outliers'       },
  { key: 'statistics', label: 'Statistics'     },
]

function OverviewTab({ activeColData, typeDistribution, totalRows }) {
  if (!activeColData) return <div className="card">Select a column to inspect its profile.</div>

  const num = activeColData.numeric_stats || {}
  const statChips = [
    { label: 'Total Rows', value: totalRows?.toLocaleString() || '—' },
    { label: 'Missing', value: `${activeColData.missing_count} (${activeColData.missing_pct}%)` },
    { label: 'Unique Values', value: activeColData.unique_count?.toLocaleString() || '—' },
    { label: 'Mean', value: num.mean !== undefined && num.mean !== null ? Number(num.mean).toFixed(2) : 'N/A' },
    { label: 'Std Dev', value: num.std !== undefined && num.std !== null ? Number(num.std).toFixed(2) : 'N/A' },
    { label: 'Min', value: num.min !== undefined && num.min !== null ? String(num.min) : 'N/A' },
    { label: 'Max', value: num.max !== undefined && num.max !== null ? String(num.max) : 'N/A' },
    { label: 'Outliers (IQR)', value: num.outlier_count !== undefined && num.outlier_count !== null ? String(num.outlier_count) : 'N/A' },
  ]

  return (
    <div className="card">
      <div className={styles.tabSectionHeader}>
        <h3 className={styles.cardHeading}>Column Summary: {activeColData.name}</h3>
        <span className={typeBadgeClass[getSimpleType(activeColData.dtype)]}>
          Type: {activeColData.dtype}
        </span>
      </div>

      <div className={styles.statsGrid}>
        {statChips.map((c) => (
          <div key={c.label} className={styles.statChip}>
            <div className={styles.statChipLabel}>{c.label}</div>
            <div className={styles.statChipValue}>{c.value}</div>
          </div>
        ))}
      </div>

      {activeColData.sample_values && activeColData.sample_values.length > 0 && (
        <div style={{ marginTop: 14 }}>
          <div className={styles.subHeading}>Sample Values from Column</div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {activeColData.sample_values.map((val, idx) => (
              <span key={idx} className="badge badge-purple" style={{ fontFamily: 'monospace', fontSize: 11 }}>
                {String(val)}
              </span>
            ))}
          </div>
        </div>
      )}

      <hr className="divider" />

      <div style={{ marginTop: 16 }}>
        <div className={styles.subHeading}>Dataset Type Distribution</div>
        {typeDistribution && typeDistribution.map((d) => (
          <div key={d.label} className={styles.barRow}>
            <span className={styles.barLabel}>{d.label}</span>
            <div className={styles.barTrack}>
              <div
                className={styles.barFill}
                style={{
                  width: `${Math.max(d.pct, 4)}%`,
                  background:
                    d.label === 'Integer'
                      ? 'var(--accent-blue)'
                      : d.label === 'Float'
                      ? 'var(--accent-green)'
                      : d.label === 'Date'
                      ? 'var(--accent-yellow)'
                      : 'var(--accent-purple)',
                }}
              />
            </div>
            <span className={styles.barCount}>
              {d.count} ({d.pct}%)
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

function MissingTab({ columns }) {
  const missingCols = columns.filter((c) => c.missing_count > 0)

  return (
    <div className="card">
      <div className={styles.tabSectionHeader}>
        <div>
          <h3 className={styles.cardHeading}>Missing Values Breakdown</h3>
          <p className={styles.cardSubtext}>
            {missingCols.length} of {columns.length} columns contain missing or null values.
          </p>
        </div>
        <span className="badge badge-yellow">
          {missingCols.reduce((sum, c) => sum + c.missing_count, 0).toLocaleString()} Missing Cells
        </span>
      </div>

      {missingCols.length === 0 ? (
        <div style={{ padding: 24, textAlign: 'center', color: 'var(--accent-green)' }}>
          No missing values detected across any columns in this dataset.
        </div>
      ) : (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Column</th>
              <th>Data Type</th>
              <th>Missing Count</th>
              <th>Percentage</th>
              <th>Visual Impact</th>
            </tr>
          </thead>
          <tbody>
            {missingCols.map((c) => (
              <tr key={c.name}>
                <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{c.name}</td>
                <td>
                  <span className={typeBadgeClass[getSimpleType(c.dtype)]}>{c.dtype}</span>
                </td>
                <td>{c.missing_count.toLocaleString()} rows</td>
                <td>{c.missing_pct}%</td>
                <td style={{ width: 160 }}>
                  <div className={styles.barTrack}>
                    <div
                      className={styles.barFill}
                      style={{
                        width: `${Math.min(c.missing_pct * 2, 100)}%`,
                        background: c.missing_pct > 20 ? 'var(--accent-red)' : 'var(--accent-yellow)',
                      }}
                    />
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

function DuplicatesTab({ rowAnalysis }) {
  const exactDups = rowAnalysis?.exact_duplicate_rows || 0
  const nearDups = rowAnalysis?.near_duplicate_rows_incl_exact || 0
  const emptyRows = rowAnalysis?.fully_empty_rows || 0
  const sparseRows = rowAnalysis?.sparse_rows_over_50pct_blank || 0

  return (
    <div className="card">
      <div className={styles.tabSectionHeader}>
        <div>
          <h3 className={styles.cardHeading}>Duplicate & Redundant Rows Analysis</h3>
          <p className={styles.cardSubtext}>
            Evaluates row content ignoring index-like columns.
          </p>
        </div>
        <span className={exactDups > 0 ? 'badge badge-red' : 'badge badge-green'}>
          {exactDups} Exact Duplicates
        </span>
      </div>

      <div className={styles.statsGrid}>
        <div className={styles.statChip}>
          <div className={styles.statChipLabel}>Exact Duplicate Rows</div>
          <div className={styles.statChipValue}>{exactDups}</div>
        </div>
        <div className={styles.statChip}>
          <div className={styles.statChipLabel}>Near Duplicates (Normalized)</div>
          <div className={styles.statChipValue}>{nearDups}</div>
        </div>
        <div className={styles.statChip}>
          <div className={styles.statChipLabel}>Fully Blank Rows</div>
          <div className={styles.statChipValue}>{emptyRows}</div>
        </div>
        <div className={styles.statChip}>
          <div className={styles.statChipLabel}>Sparse Rows (&gt;50% Blank)</div>
          <div className={styles.statChipValue}>{sparseRows}</div>
        </div>
      </div>

      {rowAnalysis?.example_row_labels?.duplicate && rowAnalysis.example_row_labels.duplicate.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <div className={styles.subHeading}>Example Duplicate Row Indices</div>
          <div style={{ display: 'flex', gap: 6 }}>
            {rowAnalysis.example_row_labels.duplicate.map((idx) => (
              <span key={idx} className="badge badge-red">
                Row #{idx}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function OutliersTab({ columns }) {
  const outlierCols = columns.filter(
    (c) => c.numeric_stats && c.numeric_stats.outlier_count > 0
  )

  return (
    <div className="card">
      <div className={styles.tabSectionHeader}>
        <div>
          <h3 className={styles.cardHeading}>Statistical Outlier Analysis (1.5x IQR)</h3>
          <p className={styles.cardSubtext}>
            Values lying beyond 1.5 times the Interquartile Range for each numeric column.
          </p>
        </div>
      </div>

      {outlierCols.length === 0 ? (
        <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)' }}>
          No statistical outliers detected in numeric columns.
        </div>
      ) : (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Column</th>
              <th>Outlier Count</th>
              <th>Min Value</th>
              <th>Max Value</th>
              <th>Mean</th>
              <th>Std Dev</th>
            </tr>
          </thead>
          <tbody>
            {outlierCols.map((c) => (
              <tr key={c.name}>
                <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{c.name}</td>
                <td>
                  <span className="badge badge-yellow">
                    {c.numeric_stats.outlier_count} outliers
                  </span>
                </td>
                <td>{c.numeric_stats.min}</td>
                <td>{c.numeric_stats.max}</td>
                <td>{c.numeric_stats.mean?.toFixed(2)}</td>
                <td>{c.numeric_stats.std?.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

function StatisticsTab({ columns }) {
  const numCols = columns.filter((c) => c.numeric_stats)

  return (
    <div className="card">
      <h3 className={styles.cardHeading}>Descriptive Numerical Statistics</h3>
      {numCols.length === 0 ? (
        <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)' }}>
          No numerical columns found in this dataset.
        </div>
      ) : (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Column</th>
              <th>Type</th>
              <th>Mean</th>
              <th>Std Dev</th>
              <th>Min</th>
              <th>Max</th>
              <th>Unique</th>
              <th>Outliers</th>
            </tr>
          </thead>
          <tbody>
            {numCols.map((c) => (
              <tr key={c.name}>
                <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{c.name}</td>
                <td>
                  <span className="badge badge-blue">{c.dtype}</span>
                </td>
                <td>{c.numeric_stats.mean !== null ? c.numeric_stats.mean.toFixed(2) : '—'}</td>
                <td>{c.numeric_stats.std !== null ? c.numeric_stats.std.toFixed(2) : '—'}</td>
                <td>{c.numeric_stats.min ?? '—'}</td>
                <td>{c.numeric_stats.max ?? '—'}</td>
                <td>{c.unique_count}</td>
                <td>
                  <span className={c.numeric_stats.outlier_count > 0 ? 'badge badge-yellow' : 'badge badge-green'}>
                    {c.numeric_stats.outlier_count}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

function ProfilingPage() {
  const { fileInfo, profilingData, isProfiling, runProfiling } = useDataset()
  const [selectedColName, setSelectedColName] = useState(null)
  const [activeTab, setActiveTab] = useState('overview')

  // Auto-run profiling if dataset is loaded but not yet profiled
  useEffect(() => {
    if (fileInfo && !profilingData && !isProfiling) {
      runProfiling().catch((e) => console.warn('Profiling error:', e))
    }
  }, [fileInfo, profilingData, isProfiling, runProfiling])

  // Select first column by default
  useEffect(() => {
    if (profilingData && profilingData.columns && profilingData.columns.length > 0 && !selectedColName) {
      setSelectedColName(profilingData.columns[0].name)
    }
  }, [profilingData, selectedColName])

  if (!fileInfo) {
    return (
      <div className={styles.page}>
        <header className={styles.header}>
          <h1 className={styles.title}>Data Profiling</h1>
          <p className={styles.subtitle}>No dataset is currently loaded.</p>
        </header>
        <div className="card" style={{ padding: 48, textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 }}>
          <Upload size={36} color="var(--accent-purple)" />
          <div>
            <h3 style={{ fontSize: 16, marginBottom: 4 }}>Upload a dataset to see its profile</h3>
            <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
              Supports CSV, XLSX, XLS, and JSON files.
            </p>
          </div>
          <Link to="/upload" className="btn btn-primary">
            Go to New Cleaning
          </Link>
        </div>
      </div>
    )
  }

  if (isProfiling && !profilingData) {
    return (
      <div className={styles.page}>
        <div className="card" style={{ padding: 48, textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 }}>
          <Loader size={32} color="var(--accent-purple)" className={styles.spin} />
          <div>
            <h3 style={{ fontSize: 16 }}>Profiling dataset: {fileInfo.name}</h3>
            <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
              Evaluating null distributions, types, duplicates, and outliers...
            </p>
          </div>
        </div>
      </div>
    )
  }

  const columnsList = profilingData?.columns || []
  const activeColData = columnsList.find((c) => c.name === selectedColName) || columnsList[0]

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.titleWrap}>
          <h1 className={styles.title}>Data Profiling</h1>
          <div className={styles.datasetBadge}>
            <FileSpreadsheet size={14} strokeWidth={1.75} color="var(--accent-blue)" />
            <span>{profilingData?.file_name || fileInfo.name}</span>
          </div>
          <Link to="/recommendations" className="btn btn-secondary" style={{ marginLeft: 'auto', fontSize: 12 }}>
            View AI Recommendations <ArrowRight size={13} />
          </Link>
        </div>
        <p className={styles.subtitle}>
          In-depth structural breakdown of distributions, data types, nulls, duplicates, and outliers.
        </p>
      </header>

      {/* Top 4 KPI Metrics */}
      <div className={styles.topStats}>
        <div className={['card', styles.kpiCard].join(' ')}>
          <div className={styles.kpiHeader}>
            <span className={styles.kpiLabel}>TOTAL COLUMNS</span>
            <Columns size={16} strokeWidth={1.75} color="var(--accent-blue)" />
          </div>
          <div className={styles.statValue}>{profilingData?.total_columns || fileInfo.column_count}</div>
          <div className={styles.kpiDesc}>Schema validated</div>
        </div>

        <div className={['card', styles.kpiCard].join(' ')}>
          <div className={styles.kpiHeader}>
            <span className={styles.kpiLabel}>TOTAL ROWS</span>
            <Table2 size={16} strokeWidth={1.75} color="var(--accent-purple)" />
          </div>
          <div className={styles.statValue}>
            {profilingData?.total_rows?.toLocaleString() || fileInfo.row_count?.toLocaleString()}
          </div>
          <div className={styles.kpiDesc}>Loaded in memory</div>
        </div>

        <div className={['card', styles.kpiCard].join(' ')}>
          <div className={styles.kpiHeader}>
            <span className={styles.kpiLabel}>MISSING CELLS</span>
            <AlertCircle size={16} strokeWidth={1.75} color="var(--accent-yellow)" />
          </div>
          <div className={styles.statValue}>
            {profilingData?.total_missing_cells?.toLocaleString() || 0}
          </div>
          <div className={styles.kpiDesc}>{profilingData?.missing_cells_pct || 0}% of all cells</div>
        </div>

        <div className={['card', styles.kpiCard].join(' ')}>
          <div className={styles.kpiHeader}>
            <span className={styles.kpiLabel}>EXACT DUPLICATES</span>
            <Copy size={16} strokeWidth={1.75} color="var(--accent-red)" />
          </div>
          <div className={styles.statValue}>{profilingData?.exact_duplicate_rows || 0}</div>
          <div className={styles.kpiDesc}>Redundant records</div>
        </div>
      </div>

      {/* Main Two-Column Layout */}
      <div className={styles.contentArea}>
        {/* Left Column Explorer */}
        <aside className={styles.leftPanel}>
          <div className="section-title">Column Explorer ({columnsList.length})</div>
          <div className={['card', styles.columnCard].join(' ')}>
            <ul className={styles.columnList}>
              {columnsList.map((c) => {
                const sType = getSimpleType(c.dtype)
                return (
                  <li
                    key={c.name}
                    onClick={() => setSelectedColName(c.name)}
                    className={[
                      styles.columnItem,
                      selectedColName === c.name ? styles.columnItemActive : '',
                    ].join(' ')}
                  >
                    <span className={styles.columnName} title={c.name}>
                      {c.name}
                    </span>
                    <span className={typeBadgeClass[sType]}>{sType}</span>
                  </li>
                )
              })}
            </ul>
          </div>
        </aside>

        {/* Right Tabbed Analysis Area */}
        <div className={styles.rightPanel}>
          <div className={styles.tabs}>
            {tabs.map((t) => (
              <button
                key={t.key}
                onClick={() => setActiveTab(t.key)}
                className={[styles.tab, activeTab === t.key ? styles.tabActive : ''].join(' ')}
              >
                {t.label}
              </button>
            ))}
          </div>

          <div className={styles.tabContent}>
            {activeTab === 'overview' && (
              <OverviewTab
                activeColData={activeColData}
                typeDistribution={profilingData?.type_distribution}
                totalRows={profilingData?.total_rows}
              />
            )}
            {activeTab === 'missing' && <MissingTab columns={columnsList} />}
            {activeTab === 'duplicates' && (
              <DuplicatesTab rowAnalysis={profilingData?.row_analysis} />
            )}
            {activeTab === 'outliers' && <OutliersTab columns={columnsList} />}
            {activeTab === 'statistics' && <StatisticsTab columns={columnsList} />}
          </div>
        </div>
      </div>
    </div>
  )
}

export default ProfilingPage
