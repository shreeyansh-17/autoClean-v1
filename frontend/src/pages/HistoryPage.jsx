import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Search,
  Download,
  Eye,
  RefreshCw,
  Trash2,
  FileSpreadsheet,
  FileCode,
  FileText,
  ChevronLeft,
  ChevronRight,
  Filter,
} from 'lucide-react'
import { useDataset } from '../context/DatasetContext'
import styles from './HistoryPage.module.css'

function HistoryPage() {
  const { historyRecords = [] } = useDataset()
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')

  const filtered = historyRecords.filter((item) => {
    const matchesSearch = item.name.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesStatus =
      statusFilter === 'all' ||
      (item.status && item.status.toLowerCase() === statusFilter.toLowerCase())
    return matchesSearch && matchesStatus
  })

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>Cleaning History</h1>
        <p className={styles.subtitle}>
          Track past dataset transformations, audit logs, and download historical cleaning artifacts.
        </p>
      </header>

      {/* Filter and Search Bar */}
      <div className={styles.topBar}>
        <div className={styles.searchWrapper}>
          <Search size={15} strokeWidth={1.75} className={styles.searchIcon} />
          <input
            type="text"
            placeholder="Search datasets by filename..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className={styles.searchInput}
          />
        </div>

        <div className={styles.filterGroup}>
          <Filter size={15} strokeWidth={1.75} color="var(--text-muted)" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className={styles.statusSelect}
          >
            <option value="all">All Statuses</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
            <option value="processing">Processing</option>
          </select>
        </div>
      </div>

      {/* Table Card */}
      <div className={['card', styles.tableCard].join(' ')}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th style={{ width: 48 }}>#</th>
              <th>Dataset Name</th>
              <th>Format</th>
              <th>Original Rows</th>
              <th>Cleaned Rows</th>
              <th>Issues Resolved</th>
              <th>Status</th>
              <th>Execution Date</th>
              <th style={{ textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((row, idx) => (
              <tr key={row.id || idx}>
                <td style={{ color: 'var(--text-muted)' }}>{idx + 1}</td>
                <td>
                  <div className={styles.fileNameCell}>
                    {row.type === 'JSON' ? (
                      <FileCode size={15} strokeWidth={1.75} color="var(--accent-purple)" />
                    ) : (
                      <FileSpreadsheet size={15} strokeWidth={1.75} color="var(--accent-blue)" />
                    )}
                    <span>{row.name}</span>
                  </div>
                </td>
                <td>
                  <span
                    className={
                      row.type === 'CSV'
                        ? 'badge badge-blue'
                        : row.type === 'XLSX'
                        ? 'badge badge-green'
                        : 'badge badge-purple'
                    }
                  >
                    {row.type || 'CSV'}
                  </span>
                </td>
                <td>{row.original_rows?.toLocaleString() || '—'}</td>
                <td>{row.cleaned_rows?.toLocaleString() || '—'}</td>
                <td>
                  <span
                    style={{
                      fontWeight: 600,
                      color: row.issues > 0 ? 'var(--text-primary)' : 'var(--text-muted)',
                    }}
                  >
                    {row.issues || 0}
                  </span>
                </td>
                <td>
                  <span className="badge badge-green">
                    {row.status || 'Completed'}
                  </span>
                </td>
                <td style={{ color: 'var(--text-muted)' }}>{row.date}</td>
                <td>
                  <div className={styles.actionsCell}>
                    <Link to="/results">
                      <button className="btn btn-ghost" title="View Results">
                        <Eye size={14} strokeWidth={1.75} />
                      </button>
                    </Link>
                  </div>
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={9} style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
                  No historical datasets found.{' '}
                  <Link to="/upload" style={{ color: 'var(--accent-purple)' }}>
                    Upload a dataset to start.
                  </Link>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className={styles.pagination}>
        <span className={styles.paginationText}>
          Showing {filtered.length} of {historyRecords.length} records
        </span>
        <div className={styles.paginationControls}>
          <button className="btn btn-secondary" disabled>
            <ChevronLeft size={14} strokeWidth={1.75} />
          </button>
          <button className="btn btn-primary" style={{ minWidth: 32, justifyContent: 'center' }}>
            1
          </button>
          <button className="btn btn-secondary" disabled>
            <ChevronRight size={14} strokeWidth={1.75} />
          </button>
        </div>
      </div>
    </div>
  )
}

export default HistoryPage
