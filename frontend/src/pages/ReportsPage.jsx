import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  FileText,
  Download,
  Eye,
  Plus,
  Clock,
  FileSpreadsheet,
  CheckCircle2,
  Filter,
} from 'lucide-react'
import { useDataset } from '../context/DatasetContext'
import styles from './ReportsPage.module.css'

function ReportsPage() {
  const { historyRecords = [], cleaningResults, exportFile } = useDataset()
  const [activeFilter, setActiveFilter] = useState('all')

  const handleDownloadReport = async () => {
    try {
      await exportFile('report')
    } catch (err) {
      console.error('Download report error:', err)
    }
  }

  // Derive reports from history
  const reports = historyRecords.map((item, idx) => ({
    id: item.id || idx + 1,
    title: `Cleaning Audit: ${item.name}`,
    dataset: item.name,
    date: item.date || 'Recently generated',
    size: `${Math.max(12, Math.round((item.cleaned_rows || 100) / 100))} KB`,
    status: item.status || 'Verified',
  }))

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Reports & Audits</h1>
          <p className={styles.subtitle}>
            Exportable compliance documentation, transformation summaries, and data quality matrices.
          </p>
        </div>

        {cleaningResults && (
          <button className="btn btn-primary" onClick={handleDownloadReport}>
            <Download size={15} strokeWidth={1.75} />
            Export Current Report
          </button>
        )}
      </header>

      {/* Filter Row */}
      <div className={styles.filterRow}>
        <div className={styles.filterGroup}>
          {['all', 'this-week', 'this-month'].map((f) => (
            <button
              key={f}
              onClick={() => setActiveFilter(f)}
              className={[
                styles.filterTab,
                activeFilter === f ? styles.filterTabActive : '',
              ].join(' ')}
            >
              {f === 'all' ? 'All Reports' : f === 'this-week' ? 'This Week' : 'This Month'}
            </button>
          ))}
        </div>
        <span className={styles.countText}>{reports.length} audit records</span>
      </div>

      {/* Grid of Report Cards */}
      <div className={styles.reportsGrid}>
        {reports.length === 0 ? (
          <div className="card" style={{ gridColumn: '1 / -1', padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
            No cleaning reports generated yet.{' '}
            <Link to="/upload" style={{ color: 'var(--accent-purple)' }}>
              Execute a cleaning run to produce an audit report.
            </Link>
          </div>
        ) : (
          reports.map((r) => (
            <div key={r.id} className={['card', styles.reportCard].join(' ')}>
              <div className={styles.cardTop}>
                <div className={styles.iconWrap}>
                  <FileText size={20} strokeWidth={1.75} color="var(--accent-purple)" />
                </div>
                <span className="badge badge-purple">{r.size}</span>
              </div>

              <div className={styles.cardContent}>
                <h3 className={styles.reportTitle}>{r.title}</h3>
                <div className={styles.reportMeta}>
                  <div className={styles.metaRow}>
                    <FileSpreadsheet size={13} strokeWidth={1.75} color="var(--text-muted)" />
                    <span>{r.dataset}</span>
                  </div>
                  <div className={styles.metaRow}>
                    <Clock size={13} strokeWidth={1.75} color="var(--text-muted)" />
                    <span>{r.date}</span>
                  </div>
                </div>
              </div>

              <hr className="divider" />

              <div className={styles.cardFooter}>
                <Link to="/results">
                  <button className="btn btn-ghost" style={{ padding: '6px 10px', fontSize: 12 }}>
                    <Eye size={14} strokeWidth={1.75} />
                    View Details
                  </button>
                </Link>
                <button
                  className="btn btn-secondary"
                  style={{ padding: '6px 12px', fontSize: 12 }}
                  onClick={handleDownloadReport}
                >
                  <Download size={14} strokeWidth={1.75} />
                  Download
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default ReportsPage
