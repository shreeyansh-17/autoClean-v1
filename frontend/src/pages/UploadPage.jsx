import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Upload,
  FileSpreadsheet,
  FileCode,
  FileText,
  Trash2,
  Play,
  Sliders,
  Sparkles,
  CheckCircle2,
  Table,
  Loader,
  AlertTriangle,
} from 'lucide-react'
import { useDataset } from '../context/DatasetContext'
import { openFileDialog, isPyWebView } from '../services/pywebview'
import styles from './UploadPage.module.css'

function UploadPage() {
  const navigate = useNavigate()
  const {
    fileInfo,
    previewRows,
    columns,
    isLoadingFile,
    fileError,
    loadDatasetFile,
    runProfiling,
    runGenerateRecommendations,
    isProfiling,
    isLoadingRecs,
  } = useDataset()

  const [isDragging, setIsDragging] = useState(false)
  const [autoImpute, setAutoImpute] = useState(true)
  const [removeDuplicates, setRemoveDuplicates] = useState(true)
  const [normalizeTypes, setNormalizeTypes] = useState(true)
  const [aiAssisted, setAiAssisted] = useState(true)
  const [actionError, setActionError] = useState(null)
  const fileInputRef = useRef(null)

  const handlePickFile = async () => {
    setActionError(null)
    if (isPyWebView()) {
      try {
        const dialogRes = await openFileDialog()
        if (dialogRes && dialogRes.path) {
          await loadDatasetFile(dialogRes.path)
        }
      } catch (err) {
        setActionError(err.message || 'Failed to open file.')
      }
    } else {
      fileInputRef.current?.click()
    }
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = () => {
    setIsDragging(false)
  }

  const handleDrop = async (e) => {
    e.preventDefault()
    setIsDragging(false)
    setActionError(null)
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const dropped = e.dataTransfer.files[0]
      // In electron/pywebview, dropped file has a .path property
      const filePath = dropped.path || dropped.name
      try {
        await loadDatasetFile(filePath)
      } catch (err) {
        setActionError(err.message || 'Failed to process dropped file.')
      }
    }
  }

  const handleFileInputChange = async (e) => {
    setActionError(null)
    if (e.target.files && e.target.files.length > 0) {
      const selected = e.target.files[0]
      const filePath = selected.path || selected.name
      try {
        await loadDatasetFile(filePath)
      } catch (err) {
        setActionError(err.message || 'Failed to process selected file.')
      }
    }
  }

  const handleStartPipeline = async () => {
    setActionError(null)
    try {
      // 1. Trigger profiling
      await runProfiling()
      // 2. Start recommendations in background
      if (aiAssisted) {
        runGenerateRecommendations().catch((e) => console.warn('Recs background warning:', e))
      }
      navigate('/profiling')
    } catch (err) {
      setActionError(err.message || 'Pipeline startup failed.')
    }
  }

  const previewCols = columns.slice(0, 6)
  const isWorking = isLoadingFile || isProfiling || isLoadingRecs

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>New Cleaning</h1>
        <p className={styles.subtitle}>
          Upload a CSV, Excel, or JSON dataset to profile issues and trigger the AI cleaning engine.
        </p>
      </header>

      {/* Errors */}
      {(fileError || actionError) && (
        <div className="card" style={{ background: 'rgba(248, 113, 113, 0.1)', borderColor: 'rgba(248, 113, 113, 0.3)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--accent-red)' }}>
            <AlertTriangle size={16} strokeWidth={2} />
            <span style={{ fontSize: 13, fontWeight: 500 }}>{fileError || actionError}</span>
          </div>
        </div>
      )}

      {/* Drag & Drop Zone */}
      {!fileInfo && (
        <div
          className={[styles.dropzone, isDragging ? styles.dropzoneDragging : ''].join(' ')}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={handlePickFile}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileInputChange}
            accept=".csv,.xlsx,.xls,.json"
            style={{ display: 'none' }}
          />
          <div className={styles.dropzoneIconWrap}>
            {isLoadingFile ? (
              <Loader size={32} strokeWidth={2} color="var(--accent-purple)" className={styles.spin} />
            ) : (
              <Upload size={36} strokeWidth={1.5} color="var(--accent-purple)" />
            )}
          </div>
          <div className={styles.dropzoneText}>
            <h3>{isLoadingFile ? 'Loading & Parsing Dataset...' : 'Drop your dataset here'}</h3>
            <p>or click to browse from local storage (CSV, XLSX, XLS, JSON)</p>
          </div>
          <div className={styles.formats}>
            <span className="badge badge-blue">CSV</span>
            <span className="badge badge-green">XLSX</span>
            <span className="badge badge-green">XLS</span>
            <span className="badge badge-purple">JSON</span>
          </div>
        </div>
      )}

      {/* Selected File Details */}
      {fileInfo && (
        <div className="card">
          <div className={styles.fileCard}>
            <div className={styles.fileDetails}>
              <div className={styles.fileIcon}>
                {fileInfo.format === 'JSON' ? (
                  <FileCode size={24} strokeWidth={1.75} color="var(--accent-purple)" />
                ) : (
                  <FileSpreadsheet size={24} strokeWidth={1.75} color="var(--accent-green)" />
                )}
              </div>
              <div>
                <div className={styles.fileName}>{fileInfo.name}</div>
                <div className={styles.fileMeta}>
                  {fileInfo.size_kb} KB &bull; {fileInfo.format} &bull; {fileInfo.row_count?.toLocaleString()} Rows &bull; {fileInfo.column_count} Columns
                </div>
              </div>
            </div>
            <button className="btn btn-ghost" onClick={handlePickFile} disabled={isWorking}>
              Choose Another File
            </button>
          </div>

          {/* Real Dataset Preview */}
          {previewRows && previewRows.length > 0 && (
            <div className={styles.previewSection}>
              <div className={styles.previewHeader}>
                <div className={styles.previewTitle}>
                  <Table size={15} strokeWidth={1.75} />
                  Dataset Preview (First {previewRows.length} Rows)
                </div>
                <span className="badge badge-purple">
                  Showing {previewCols.length} of {columns.length} columns
                </span>
              </div>
              <div className={styles.tableWrapper}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th style={{ width: 44 }}>#</th>
                      {previewCols.map((c) => (
                        <th key={c}>{c}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {previewRows.map((row, idx) => (
                      <tr key={row._row_id || idx}>
                        <td style={{ color: 'var(--text-muted)' }}>{idx + 1}</td>
                        {previewCols.map((c) => {
                          const val = row[c]
                          const isNull = val === null || val === undefined || val === ''
                          return (
                            <td key={c} className={isNull ? styles.missingCell : ''}>
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
          )}
        </div>
      )}

      {/* Pipeline Configuration */}
      <div className="card">
        <div className={styles.sectionHeading}>
          <Sliders size={16} strokeWidth={1.75} color="var(--accent-purple)" />
          <h3>Cleaning Configuration</h3>
        </div>

        <div className={styles.optionsList}>
          <div className={styles.optionRow}>
            <div>
              <div className={styles.optionLabel}>Auto-fix missing values</div>
              <div className={styles.optionDesc}>
                Detects nulls and placeholders, imputing or tagging according to column type.
              </div>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={autoImpute}
              onClick={() => setAutoImpute(!autoImpute)}
              className={[styles.toggle, autoImpute ? styles.toggleOn : ''].join(' ')}
            >
              <span className={styles.toggleThumb} />
            </button>
          </div>

          <div className={styles.optionRow}>
            <div>
              <div className={styles.optionLabel}>Deduplicate identical records</div>
              <div className={styles.optionDesc}>
                Removes redundant rows while archiving copies for reference.
              </div>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={removeDuplicates}
              onClick={() => setRemoveDuplicates(!removeDuplicates)}
              className={[styles.toggle, removeDuplicates ? styles.toggleOn : ''].join(' ')}
            >
              <span className={styles.toggleThumb} />
            </button>
          </div>

          <div className={styles.optionRow}>
            <div>
              <div className={styles.optionLabel}>Standardize data types & dates</div>
              <div className={styles.optionDesc}>
                Normalizes date formats to ISO 8601 and sanitizes mixed numerical types.
              </div>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={normalizeTypes}
              onClick={() => setNormalizeTypes(!normalizeTypes)}
              className={[styles.toggle, normalizeTypes ? styles.toggleOn : ''].join(' ')}
            >
              <span className={styles.toggleThumb} />
            </button>
          </div>

          <div className={styles.optionRow}>
            <div>
              <div className={styles.optionLabel}>
                <span className={styles.aiTag}>
                  <Sparkles size={13} strokeWidth={1.75} />
                  AI Recommendations Engine (Groq)
                </span>
              </div>
              <div className={styles.optionDesc}>
                Generates contextual cleaning strategies using your configured LLM and fallback rules.
              </div>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={aiAssisted}
              onClick={() => setAiAssisted(!aiAssisted)}
              className={[styles.toggle, aiAssisted ? styles.toggleOn : ''].join(' ')}
            >
              <span className={styles.toggleThumb} />
            </button>
          </div>
        </div>

        <div className={styles.actionFooter}>
          <button
            className="btn btn-primary"
            disabled={!fileInfo || isWorking}
            onClick={handleStartPipeline}
            style={{ width: '100%', justifyContent: 'center', padding: '12px' }}
          >
            {isWorking ? (
              <>
                <Loader size={16} strokeWidth={2} className={styles.spin} />
                Analyzing Dataset & Building Profile...
              </>
            ) : (
              <>
                <Play size={16} strokeWidth={1.75} />
                Analyze & Start Pipeline
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

export default UploadPage
