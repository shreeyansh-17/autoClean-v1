import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  Sparkles,
  Check,
  X,
  Wand2,
  Trash2,
  RefreshCw,
  Type,
  AlertTriangle,
  Hash,
  Filter,
  Eye,
  CheckCircle2,
  Loader,
  Play,
  Upload,
} from 'lucide-react'
import { useDataset } from '../context/DatasetContext'
import styles from './RecommendationsPage.module.css'

function getActionIcon(actionType) {
  if (!actionType) return Wand2
  if (actionType.startsWith('drop_') || actionType === 'drop_column') return Trash2
  if (actionType.includes('date')) return RefreshCw
  if (actionType.includes('dtype') || actionType.includes('number')) return Type
  if (actionType.includes('outlier')) return AlertTriangle
  if (actionType.includes('casing') || actionType.includes('whitespace')) return Hash
  if (actionType.includes('sparse')) return Filter
  return Wand2
}

function RecommendationsPage() {
  const navigate = useNavigate()
  const {
    fileInfo,
    recommendations,
    planSource,
    llmError,
    isLoadingRecs,
    recError,
    runGenerateRecommendations,
    toggleAction,
    approveAllActions,
    runCleaning,
    isCleaning,
    cleanError,
  } = useDataset()

  const [filter, setFilter] = useState('all')

  // Auto-generate recommendations if dataset loaded and no recommendations yet
  useEffect(() => {
    if (fileInfo && (!recommendations || recommendations.length === 0) && !isLoadingRecs && !recError) {
      runGenerateRecommendations().catch((e) => console.warn('Recs generate warning:', e))
    }
  }, [fileInfo, recommendations, isLoadingRecs, recError, runGenerateRecommendations])

  const handleApplyToggle = (recId, currentStatus) => {
    toggleAction(recId, !currentStatus)
  }

  const handleExecute = async () => {
    try {
      await runCleaning()
      navigate('/results')
    } catch (err) {
      console.error('Execution failed:', err)
    }
  }

  if (!fileInfo) {
    return (
      <div className={styles.page}>
        <header className={styles.header}>
          <h1 className={styles.title}>AI Recommendations</h1>
          <p className={styles.subtitle}>No dataset is currently loaded.</p>
        </header>
        <div className="card" style={{ padding: 48, textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 }}>
          <Upload size={36} color="var(--accent-purple)" />
          <div>
            <h3 style={{ fontSize: 16, marginBottom: 4 }}>Upload a dataset to generate cleaning recommendations</h3>
            <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
              Uses the Groq LLM engine to analyze issues and propose precise cleaning steps.
            </p>
          </div>
          <Link to="/upload" className="btn btn-primary">
            Upload Dataset
          </Link>
        </div>
      </div>
    )
  }

  if (isLoadingRecs) {
    return (
      <div className={styles.page}>
        <div className="card" style={{ padding: 48, textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 }}>
          <Loader size={32} color="var(--accent-purple)" className={styles.spin} />
          <div>
            <h3 style={{ fontSize: 16 }}>Generating AI Cleaning Recommendations...</h3>
            <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
              Analyzing dataset profile against rule patterns and Groq LLM reasoning engine...
            </p>
          </div>
        </div>
      </div>
    )
  }

  const highCount = recommendations.filter((r) => r.priority === 'high').length
  const medCount = recommendations.filter((r) => r.priority === 'medium').length
  const lowCount = recommendations.filter((r) => r.priority === 'low').length
  const approvedCount = recommendations.filter((r) => r.approved).length

  const filteredRecs = recommendations.filter((r) => {
    if (filter === 'all') return true
    return r.priority === filter
  })

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.titleWrap}>
          <h1 className={styles.title}>AI Recommendations</h1>
          <span className="badge badge-purple">
            <Sparkles size={12} strokeWidth={1.75} />
            Source: {planSource.toUpperCase()}
          </span>
          {llmError && (
            <span className="badge badge-yellow" title={llmError}>
              Fallback Active
            </span>
          )}
          <button
            className="btn btn-primary"
            onClick={handleExecute}
            disabled={approvedCount === 0 || isCleaning}
            style={{ marginLeft: 'auto' }}
          >
            {isCleaning ? (
              <>
                <Loader size={14} strokeWidth={2} className={styles.spin} />
                Executing Pipeline...
              </>
            ) : (
              <>
                <Play size={14} strokeWidth={1.75} />
                Execute {approvedCount} Approved Actions
              </>
            )}
          </button>
        </div>
        <p className={styles.subtitle}>
          Intelligent, contextual cleaning actions evaluated for <strong>{fileInfo.name}</strong>. Approve or skip individual actions before applying.
        </p>
      </header>

      {/* Errors */}
      {(recError || cleanError) && (
        <div className="card" style={{ background: 'rgba(248, 113, 113, 0.1)', borderColor: 'rgba(248, 113, 113, 0.3)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--accent-red)', fontSize: 13 }}>
            <AlertTriangle size={16} strokeWidth={2} />
            <span>{recError || cleanError}</span>
          </div>
        </div>
      )}

      {/* Control Bar */}
      <div className={['card', styles.controlBar].join(' ')}>
        <div className={styles.statsOverview}>
          <div className={styles.statItem}>
            <span className={styles.statVal}>{recommendations.length}</span>
            <span className={styles.statLabel}>Total Proposals</span>
          </div>
          <div className={styles.statDivider} />
          <div className={styles.statItem}>
            <span className={[styles.statVal, styles.valHigh].join(' ')}>{highCount}</span>
            <span className={styles.statLabel}>High Priority</span>
          </div>
          <div className={styles.statDivider} />
          <div className={styles.statItem}>
            <span className={[styles.statVal, styles.valMed].join(' ')}>{medCount}</span>
            <span className={styles.statLabel}>Medium</span>
          </div>
          <div className={styles.statDivider} />
          <div className={styles.statItem}>
            <span className={[styles.statVal, styles.valLow].join(' ')}>{lowCount}</span>
            <span className={styles.statLabel}>Low</span>
          </div>
        </div>

        <div className={styles.actionControls}>
          <div className={styles.filterTabs}>
            {['all', 'high', 'medium', 'low'].map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={[styles.filterBtn, filter === f ? styles.filterBtnActive : ''].join(' ')}
              >
                {f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>

          <button className="btn btn-secondary" onClick={approveAllActions}>
            <Sparkles size={14} strokeWidth={1.75} />
            Approve All ({recommendations.length})
          </button>
        </div>
      </div>

      {/* Recommendations Cards List */}
      <div className={styles.recsList}>
        {filteredRecs.length === 0 ? (
          <div className="card" style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)' }}>
            No recommendations match the selected filter.
          </div>
        ) : (
          filteredRecs.map((rec) => {
            const IconComponent = getActionIcon(rec.action)
            const isApproved = rec.approved !== false

            const stripColor =
              rec.priority === 'high'
                ? 'var(--accent-red)'
                : rec.priority === 'medium'
                ? 'var(--accent-yellow)'
                : 'var(--accent-blue)'

            return (
              <div
                key={rec.id}
                className={['card', styles.recCard, !isApproved ? styles.cardApplied : ''].join(' ')}
              >
                <div className={styles.priorityStrip} style={{ background: stripColor }} />

                <div className={styles.recIconWrap}>
                  <IconComponent size={18} strokeWidth={1.75} color={stripColor} />
                </div>

                <div className={styles.recContent}>
                  <div className={styles.recHeaderRow}>
                    <div className={styles.recTitle}>
                      {rec.action?.replace(/_/g, ' ')?.toUpperCase()}
                    </div>
                    <span className="badge badge-purple">{rec.column}</span>
                    <span className={styles.confidenceScore}>{rec.confidence || 95}% confidence</span>
                  </div>

                  <p className={styles.recDesc}>{rec.reason}</p>

                  <div className={styles.recMetaRow}>
                    <span className="badge badge-yellow">
                      Affects {rec.affected_rows?.toLocaleString() || 0} rows
                    </span>
                    <span
                      className={
                        rec.priority === 'high'
                          ? 'badge badge-red'
                          : rec.priority === 'medium'
                          ? 'badge badge-yellow'
                          : 'badge badge-blue'
                      }
                    >
                      {rec.priority.toUpperCase()} PRIORITY
                    </span>
                    {rec.parameters?.target_dtype && (
                      <span className="badge badge-blue">Target: {rec.parameters.target_dtype}</span>
                    )}
                    {rec.parameters?.target_format && (
                      <span className="badge badge-green">Format: {rec.parameters.target_format}</span>
                    )}
                  </div>
                </div>

                <div className={styles.recActions}>
                  {isApproved ? (
                    <>
                      <span className="badge badge-green" style={{ padding: '6px 10px' }}>
                        <Check size={12} strokeWidth={2} />
                        Approved
                      </span>
                      <button
                        className="btn btn-ghost"
                        onClick={() => handleApplyToggle(rec.id, true)}
                        title="Skip this action"
                      >
                        <X size={14} strokeWidth={1.75} />
                        Skip
                      </button>
                    </>
                  ) : (
                    <>
                      <span className="badge" style={{ background: 'var(--bg-elevated)', color: 'var(--text-muted)' }}>
                        Skipped
                      </span>
                      <button
                        className="btn btn-primary"
                        onClick={() => handleApplyToggle(rec.id, false)}
                        style={{ fontSize: 12, padding: '5px 12px' }}
                      >
                        <Check size={13} strokeWidth={2} />
                        Approve
                      </button>
                    </>
                  )}
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}

export default RecommendationsPage
