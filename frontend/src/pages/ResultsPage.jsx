import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  CheckCircle2,
  Download,
  FileText,
  Wrench,
  Trash2,
  Target,
  AlertTriangle,
  Clock,
  FileSpreadsheet,
  Upload,
  Check,
} from 'lucide-react'
import { useDataset } from '../context/DatasetContext'
import styles from './ResultsPage.module.css'

function ResultsPage() {
  const { fileInfo, cleaningResults, exportFile } = useDataset()
  const [activeTab, setActiveTab] = useState('summary')
  const [exportMessage, setExportMessage] = useState(null)
  const [isExporting, setIsExporting] = useState(false)

  const handleExport = async (type) => {
    setIsExporting(true)
    setExportMessage(null)
    try {
      const res = await exportFile(type)
      if (res && res.status === 'success') {
        setExportMessage(`Successfully exported to: ${res.saved_path}`)
        setTimeout(() => setExportMessage(null), 5000)
      } else if (res && res.status === 'cancelled') {
        // user dismissed dialog
      }
    } catch (err) {
      setExportMessage(`Export error: ${err.message}`)
    } finally {
      setIsExporting(false)
    }
  }

  if (!cleaningResults || cleaningResults.status !== 'success') {
    return (
      <div className={styles.page}>
        <header className={styles.header}>
          <h1 className={styles.title}>Cleaning Results</h1>
          <p className={styles.subtitle}>No cleaning run has been executed yet.</p>
        </header>
        <div className="card" style={{ padding: 48, textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 }}>
          <Upload size={36} color="var(--accent-purple)" />
          <div>
            <h3 style={{ fontSize: 16, marginBottom: 4 }}>
              {fileInfo ? `Dataset loaded: ${fileInfo.name}` : 'No dataset loaded'}
            </h3>
            <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
              {fileInfo
                ? 'Review and execute AI recommendations to inspect cleaned results.'
                : 'Upload a dataset to begin the cleaning pipeline.'}
            </p>
          </div>
          {fileInfo ? (
            <Link to="/recommendations" className="btn btn-primary">
              View Recommendations
            </Link>
          ) : (
            <Link to="/upload" className="btn btn-primary">
              Upload Dataset
            </Link>
          )}
        </div>
      </div>
    )
  }

  const {
    file_name,
    original_rows,
    cleaned_rows,
    rows_removed,
    issues_resolved,
    execution_log = [],
    before_rows = [],
    after_rows = [],
    columns = [],
  } = cleaningResults

  const appliedLogs = execution_log.filter((e) => e.status === 'applied')

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <div className={styles.titleWrap}>
            <h1 className={styles.title}>Cleaning Results</h1>
            <div className={styles.datasetBadge}>
              <FileSpreadsheet size={14} strokeWidth={1.75} color="var(--accent-blue)" />
              <span>{file_name}</span>
            </div>
          </div>
          <p className={styles.subtitle}>
            Pipeline execution completed with {appliedLogs.length} verified operations.
          </p>
        </div>

        <div className={styles.downloadGroup}>
          <button
            className="btn btn-primary"
            onClick={() => handleExport('cleaned')}
            disabled={isExporting}
          >
            <Download size={14} strokeWidth={1.75} />
            Export Cleaned CSV
          </button>
          <button
            className="btn btn-secondary"
            onClick={() => handleExport('report')}
            disabled={isExporting}
          >
            <FileText size={14} strokeWidth={1.75} />
            Export Report (.md)
          </button>
        </div>
      </header>

      {/* Export notification message */}
      {exportMessage && (
        <div className="card" style={{ background: 'rgba(52, 211, 153, 0.1)', borderColor: 'rgba(52, 211, 153, 0.3)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--accent-green)', fontSize: 13 }}>
            <Check size={16} strokeWidth={2} />
            <span>{exportMessage}</span>
          </div>
        </div>
      )}

      {/* Status Bar */}
      <div className={['card', styles.statusBar].join(' ')}>
        <div className={styles.statusLead}>
          <CheckCircle2 size={18} strokeWidth={2} color="var(--accent-green)" />
          <span>Cleaning Pipeline Completed Successfully</span>
        </div>
        <div className={styles.statusDivider} />
        <div className={styles.statusItem}>
          <span className={styles.statusLabel}>Rows Processed:</span>
          <span className={styles.statusVal}>{original_rows?.toLocaleString()}</span>
        </div>
        <div className={styles.statusDivider} />
        <div className={styles.statusItem}>
          <span className={styles.statusLabel}>Cleaned Rows:</span>
          <span className={styles.statusVal}>{cleaned_rows?.toLocaleString()}</span>
        </div>
        <div className={styles.statusDivider} />
        <div className={styles.statusItem}>
          <span className={styles.statusLabel}>Issues Resolved:</span>
          <span className={styles.statusVal}>{issues_resolved}</span>
        </div>
      </div>

      {/* KPI Cards Row */}
      <div className={styles.statsGrid}>
        <div className={['card', styles.statCard].join(' ')}>
          <div className={styles.statHeader}>
            <span className={styles.statLabel}>ROWS BEFORE</span>
            <CheckCircle2 size={16} strokeWidth={1.75} color="var(--accent-green)" />
          </div>
          <div className={styles.statValue}>{original_rows?.toLocaleString()}</div>
          <div className={styles.statDesc}>Original input records</div>
        </div>

        <div className={['card', styles.statCard].join(' ')}>
          <div className={styles.statHeader}>
            <span className={styles.statLabel}>ISSUES RESOLVED</span>
            <Wrench size={16} strokeWidth={1.75} color="var(--accent-purple)" />
          </div>
          <div className={styles.statValue}>{issues_resolved}</div>
          <div className={styles.statDesc}>Actions executed</div>
        </div>

        <div className={['card', styles.statCard].join(' ')}>
          <div className={styles.statHeader}>
            <span className={styles.statLabel}>REDUNDANT ROWS</span>
            <Trash2 size={16} strokeWidth={1.75} color="var(--accent-red)" />
          </div>
          <div className={styles.statValue}>{rows_removed}</div>
          <div className={styles.statDesc}>Duplicates & sparse rows</div>
        </div>

        <div className={['card', styles.statCard].join(' ')}>
          <div className={styles.statHeader}>
            <span className={styles.statLabel}>CLEANED ROWS</span>
            <Target size={16} strokeWidth={1.75} color="var(--accent-blue)" />
          </div>
          <div className={styles.statValue}>{cleaned_rows?.toLocaleString()}</div>
          <div className={styles.statDesc}>Validated data output</div>
        </div>
      </div>

      {/* Tabs */}
      <div className={styles.tabs}>
        {[
          { key: 'summary',     label: 'Summary' },
          { key: 'beforeafter', label: 'Before / After Comparison' },
          { key: 'changelog',   label: 'Change Log' },
          { key: 'downloads',   label: 'Download Center' },
        ].map((t) => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            className={[styles.tab, activeTab === t.key ? styles.tabActive : ''].join(' ')}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab 1: Summary */}
      {activeTab === 'summary' && (
        <div className={styles.summaryGrid}>
          <div className="card">
            <h3 className={styles.cardHeading}>Modifications Applied</h3>
            <div className={styles.changesList}>
              {appliedLogs.length === 0 ? (
                <div style={{ color: 'var(--text-muted)' }}>No modifications were necessary.</div>
              ) : (
                appliedLogs.map((log, idx) => (
                  <div key={idx} className={styles.changeItem}>
                    <CheckCircle2 size={15} strokeWidth={2} color="var(--accent-green)" />
                    <span>
                      <strong>{log.action?.replace(/_/g, ' ')?.toUpperCase()}</strong> on column{' '}
                      <code>{log.column}</code>: {log.reason}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="card">
            <h3 className={styles.cardHeading}>Dataset Row Composition</h3>
            <div className={styles.breakdownBar}>
              <div
                className={styles.segFixed}
                style={{
                  width: `${Math.max(Math.min((issues_resolved / (original_rows || 1)) * 100, 30), 5)}%`,
                }}
              />
              <div
                className={styles.segRemoved}
                style={{
                  width: `${Math.max(Math.min((rows_removed / (original_rows || 1)) * 100, 30), rows_removed > 0 ? 5 : 0)}%`,
                }}
              />
              <div className={styles.segUnchanged} style={{ flex: 1 }} />
            </div>
            <div className={styles.legend}>
              <div className={styles.legendItem}>
                <span className={styles.dot} style={{ background: 'var(--accent-green)' }} />
                <span>Modified Actions: {issues_resolved}</span>
              </div>
              <div className={styles.legendItem}>
                <span className={styles.dot} style={{ background: 'var(--accent-red)' }} />
                <span>Removed Redundant Rows: {rows_removed}</span>
              </div>
              <div className={styles.legendItem}>
                <span className={styles.dot} style={{ background: 'var(--bg-overlay)' }} />
                <span>Retained Clean Rows: {cleaned_rows?.toLocaleString()}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Before / After */}
      {activeTab === 'beforeafter' && (
        <div className={styles.compareLayout}>
          <div className={['card', styles.compareCard].join(' ')}>
            <div className={[styles.compareHeader, styles.headerBefore].join(' ')}>
              Original Data (Pre-Cleaning)
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th style={{ width: 44 }}>ID</th>
                    {columns.map((c) => (
                      <th key={c}>{c}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {before_rows.map((row, idx) => (
                    <tr key={idx}>
                      <td>#{row._row_id}</td>
                      {columns.map((c) => {
                        const val = row[c]
                        const isNull = val === null || val === undefined || val === ''
                        return (
                          <td key={c} className={isNull ? styles.cellDirty : ''}>
                            {isNull ? 'null' : String(val)}
                          </td>
                        )
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className={['card', styles.compareCard].join(' ')}>
            <div className={[styles.compareHeader, styles.headerAfter].join(' ')}>
              Cleaned Data (Normalized Output)
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th style={{ width: 44 }}>ID</th>
                    {columns.map((c) => (
                      <th key={c}>{c}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {after_rows.map((row, idx) => {
                    const beforeMatch = before_rows[idx]
                    return (
                      <tr key={idx}>
                        <td>#{row._row_id}</td>
                        {columns.map((c) => {
                          const val = row[c]
                          const bVal = beforeMatch ? beforeMatch[c] : null
                          const isChanged = bVal !== null && val !== bVal
                          return (
                            <td key={c} className={isChanged ? styles.cellCleaned : ''}>
                              {val === null || val === undefined ? 'null' : String(val)}
                            </td>
                          )
                        })}
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Change Log */}
      {activeTab === 'changelog' && (
        <div className="card">
          <h3 className={styles.cardHeading}>Audited Execution Change Log</h3>
          <div className={styles.logList}>
            {execution_log.map((entry, idx) => (
              <div key={idx} className={styles.logEntry}>
                <Clock size={13} strokeWidth={1.75} color="var(--text-muted)" />
                <span
                  className={
                    entry.status === 'applied'
                      ? 'badge badge-green'
                      : entry.status === 'failed'
                      ? 'badge badge-red'
                      : 'badge badge-yellow'
                  }
                >
                  {entry.status?.toUpperCase()}
                </span>
                <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                  {entry.action}
                </span>
                <span className={styles.logDesc}>
                  Column <code>{entry.column}</code> — {entry.reason}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 4: Download Center */}
      {activeTab === 'downloads' && (
        <div className={styles.downloadGrid}>
          <div className={['card', styles.downloadCard].join(' ')}>
            <div className={styles.downloadIconWrap}>
              <FileSpreadsheet size={24} strokeWidth={1.75} color="var(--accent-purple)" />
            </div>
            <div className={styles.downloadTitle}>Cleaned Dataset</div>
            <div className={styles.downloadMeta}>
              Export validated records ({cleaned_rows?.toLocaleString()} rows)
            </div>
            <button
              className="btn btn-primary"
              style={{ width: '100%', marginTop: 'auto' }}
              onClick={() => handleExport('cleaned')}
              disabled={isExporting}
            >
              <Download size={14} strokeWidth={1.75} />
              Save Cleaned Dataset
            </button>
          </div>

          <div className={['card', styles.downloadCard].join(' ')}>
            <div className={styles.downloadIconWrap}>
              <Trash2 size={24} strokeWidth={1.75} color="var(--accent-red)" />
            </div>
            <div className={styles.downloadTitle}>Purged Rows Archive</div>
            <div className={styles.downloadMeta}>
              Export dropped redundant/sparse rows ({rows_removed} rows)
            </div>
            <button
              className="btn btn-secondary"
              style={{ width: '100%', marginTop: 'auto' }}
              onClick={() => handleExport('removed_rows')}
              disabled={isExporting || rows_removed === 0}
            >
              <Download size={14} strokeWidth={1.75} />
              Save Dropped Rows
            </button>
          </div>

          <div className={['card', styles.downloadCard].join(' ')}>
            <div className={styles.downloadIconWrap}>
              <FileText size={24} strokeWidth={1.75} color="var(--accent-green)" />
            </div>
            <div className={styles.downloadTitle}>Audit & Compliance Report</div>
            <div className={styles.downloadMeta}>
              Markdown documentation of all pipeline steps
            </div>
            <button
              className="btn btn-secondary"
              style={{ width: '100%', marginTop: 'auto' }}
              onClick={() => handleExport('report')}
              disabled={isExporting}
            >
              <Download size={14} strokeWidth={1.75} />
              Save Markdown Report
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default ResultsPage
