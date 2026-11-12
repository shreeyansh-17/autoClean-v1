/**
 * src/components/PyWebViewTest/PyWebViewTest.jsx
 *
 * A simple diagnostic panel that:
 *   1. Shows bridge connectivity status (ping result)
 *   2. Lets the user manually trigger a ping or echo round-trip
 *   3. Displays raw JSON responses
 *
 * Embed this in the Settings page (About tab) so the user can verify
 * JS → Python communication works without needing DevTools.
 */

import { useState } from 'react'
import { Cpu, RefreshCw, ArrowRightLeft, CheckCircle2, XCircle, Loader } from 'lucide-react'
import { usePyWebView } from '../../hooks/usePyWebView'
import styles from './PyWebViewTest.module.css'

function PyWebViewTest() {
  const { isNativeWindow, isConnected, loading, appInfo, ping, echo } = usePyWebView()

  const [pingResult, setPingResult] = useState(null)
  const [echoResult, setEchoResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const [lastError, setLastError] = useState(null)

  const handlePing = async () => {
    setBusy(true)
    setLastError(null)
    try {
      const r = await ping()
      setPingResult(r)
    } catch (e) {
      setLastError(e.message)
    } finally {
      setBusy(false)
    }
  }

  const handleEcho = async () => {
    setBusy(true)
    setLastError(null)
    try {
      const r = await echo({ test: 'hello from React', timestamp: Date.now() })
      setEchoResult(r)
    } catch (e) {
      setLastError(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className={styles.panel}>
      {/* Header */}
      <div className={styles.panelHeader}>
        <Cpu size={16} strokeWidth={1.75} color="var(--accent-purple)" />
        <span className={styles.panelTitle}>PyWebView Bridge Diagnostics</span>
        <span className={isConnected ? 'badge badge-green' : loading ? 'badge badge-blue' : 'badge badge-red'}>
          {loading ? 'Probing…' : isConnected ? 'Connected' : 'Disconnected'}
        </span>
      </div>

      {/* Status grid */}
      <div className={styles.infoGrid}>
        <div className={styles.infoRow}>
          <span className={styles.infoLabel}>Runtime environment</span>
          <span className={styles.infoVal}>{isNativeWindow ? 'PyWebView native window' : 'Browser (dev mode)'}</span>
        </div>
        {appInfo && (
          <>
            <div className={styles.infoRow}>
              <span className={styles.infoLabel}>Python version</span>
              <span className={styles.infoVal}>{appInfo.python_version || appInfo.python || '—'}</span>
            </div>
            <div className={styles.infoRow}>
              <span className={styles.infoLabel}>Platform</span>
              <span className={styles.infoVal}>{appInfo.platform} {appInfo.platform_release || ''}</span>
            </div>
            <div className={styles.infoRow}>
              <span className={styles.infoLabel}>App version</span>
              <span className={styles.infoVal}>{appInfo.version || '—'}</span>
            </div>
          </>
        )}
      </div>

      {/* Action buttons */}
      <div className={styles.actions}>
        <button className="btn btn-secondary" onClick={handlePing} disabled={busy}>
          {busy ? <Loader size={14} strokeWidth={1.75} className={styles.spin} /> : <RefreshCw size={14} strokeWidth={1.75} />}
          Ping Python
        </button>
        <button className="btn btn-secondary" onClick={handleEcho} disabled={busy}>
          {busy ? <Loader size={14} strokeWidth={1.75} className={styles.spin} /> : <ArrowRightLeft size={14} strokeWidth={1.75} />}
          Echo Round-trip
        </button>
      </div>

      {/* Error */}
      {lastError && (
        <div className={styles.errorBox}>
          <XCircle size={14} strokeWidth={1.75} />
          <span>{lastError}</span>
        </div>
      )}

      {/* Results */}
      {pingResult && (
        <div className={styles.resultBlock}>
          <div className={styles.resultLabel}>
            <CheckCircle2 size={13} strokeWidth={2} color="var(--accent-green)" />
            Ping response
          </div>
          <pre className={styles.pre}>{JSON.stringify(pingResult, null, 2)}</pre>
        </div>
      )}

      {echoResult && (
        <div className={styles.resultBlock}>
          <div className={styles.resultLabel}>
            <CheckCircle2 size={13} strokeWidth={2} color="var(--accent-green)" />
            Echo response
          </div>
          <pre className={styles.pre}>{JSON.stringify(echoResult, null, 2)}</pre>
        </div>
      )}
    </div>
  )
}

export default PyWebViewTest

