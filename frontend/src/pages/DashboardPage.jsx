import { Link } from 'react-router-dom'
import {
  Database,
  Table,
  AlertTriangle,
  Target,
  TrendingUp,
  TrendingDown,
  FileSpreadsheet,
  Upload,
  Sparkles,
  Download,
  Play,
} from 'lucide-react'
import { useDataset } from '../context/DatasetContext'
import styles from './DashboardPage.module.css'

function DashboardPage() {
  const { historyRecords = [], fileInfo } = useDataset()

  // Dynamic calculations from real persistent history
  const totalDatasets = historyRecords.length
  const totalRowsCleaned = historyRecords.reduce((sum, r) => sum + (r.cleaned_rows || 0), 0)
  const totalIssuesDetected = historyRecords.reduce((sum, r) => sum + (r.issues || 0), 0)

  const statCards = [
    {
      label: 'DATASETS PROCESSED',
      value: totalDatasets.toString(),
      icon: <Database size={18} color="var(--accent-blue)" />,
      trendIcon: <TrendingUp size={12} color="var(--accent-green)" />,
      trendText: totalDatasets > 0 ? `${totalDatasets} datasets recorded` : 'Ready for input',
    },
    {
      label: 'ROWS CLEANED',
      value: totalRowsCleaned.toLocaleString(),
      icon: <Table size={18} color="var(--accent-purple)" />,
      trendIcon: <TrendingUp size={12} color="var(--accent-green)" />,
      trendText: totalRowsCleaned > 0 ? 'Verified data output' : '0 rows processed',
    },
    {
      label: 'ISSUES RESOLVED',
      value: totalIssuesDetected.toLocaleString(),
      icon: <AlertTriangle size={18} color="var(--accent-yellow)" />,
      trendIcon: <TrendingUp size={12} color="var(--accent-green)" />,
      trendText: totalIssuesDetected > 0 ? 'Applied via pipeline' : '0 issues flagged',
    },
    {
      label: 'ACTIVE STATUS',
      value: fileInfo ? 'Ready' : 'Idle',
      icon: <Target size={18} color="var(--accent-green)" />,
      trendIcon: <TrendingUp size={12} color="var(--accent-green)" />,
      trendText: fileInfo ? fileInfo.name : 'No active dataset',
    },
  ]

  const recentFiles = historyRecords.slice(0, 5)

  return (
    <div className={styles.page}>
      {/* Page Header */}
      <div>
        <h1 style={{ fontSize: '20px', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
          Dashboard
        </h1>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: '4px 0 0' }}>
          Overview of your automated dataset cleaning activity
        </p>
      </div>

      {/* Stat Cards */}
      <div className={styles.statsGrid}>
        {statCards.map((card) => (
          <div key={card.label} className={`card ${styles.statCard}`}>
            <div className={styles.statHeader}>
              <span className={styles.statLabel}>{card.label}</span>
              {card.icon}
            </div>
            <div className={styles.statValue}>{card.value}</div>
            <div className={styles.statTrend}>
              {card.trendIcon}
              <span>{card.trendText}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Recent Activity */}
      <div>
        <p className="section-title">Recent Activity</p>
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          {recentFiles.length === 0 ? (
            <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)' }}>
              No cleaning jobs have been executed yet.{' '}
              <Link to="/upload" style={{ color: 'var(--accent-purple)' }}>
                Start your first cleaning
              </Link>
            </div>
          ) : (
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>File Name</th>
                  <th>Original Rows</th>
                  <th>Cleaned Rows</th>
                  <th>Issues Resolved</th>
                  <th>Status</th>
                  <th>Date</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {recentFiles.map((file, idx) => (
                  <tr key={file.id || idx}>
                    <td>
                      <span className={styles.fileName}>
                        <FileSpreadsheet size={14} color="var(--accent-blue)" />
                        {file.name}
                      </span>
                    </td>
                    <td>{file.original_rows?.toLocaleString() || '—'}</td>
                    <td>{file.cleaned_rows?.toLocaleString() || '—'}</td>
                    <td>{file.issues || 0}</td>
                    <td>
                      <span className="badge badge-green">{file.status || 'Completed'}</span>
                    </td>
                    <td>{file.date}</td>
                    <td>
                      <Link to="/results">
                        <button
                          className="btn btn-ghost"
                          style={{ fontSize: '12px', padding: '4px 10px' }}
                        >
                          View Results
                        </button>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div className={styles.quickActions}>
        <div className={`card ${styles.quickCard}`}>
          <Upload size={20} color="var(--accent-purple)" />
          <h3>Start New Cleaning</h3>
          <p>Upload a CSV, XLSX or JSON file to begin.</p>
          <Link to="/upload">
            <button className="btn btn-primary" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Upload size={14} />
              Upload File
            </button>
          </Link>
        </div>

        <div className={`card ${styles.quickCard}`}>
          <Sparkles size={20} color="var(--accent-blue)" />
          <h3>AI Insights</h3>
          <p>Review AI-suggested cleaning actions.</p>
          <Link to="/recommendations">
            <button className="btn btn-secondary">Open Recommendations</button>
          </Link>
        </div>

        <div className={`card ${styles.quickCard}`}>
          <Download size={20} color="var(--accent-green)" />
          <h3>Download Reports</h3>
          <p>Export cleaning reports and logs.</p>
          <Link to="/reports">
            <button className="btn btn-secondary">Export Reports</button>
          </Link>
        </div>
      </div>
    </div>
  )
}

export default DashboardPage
