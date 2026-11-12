/**
 * src/components/ConnectionStatus/ConnectionStatus.jsx
 *
 * A compact status pill shown in the sidebar footer that reflects whether
 * the React frontend is connected to the Python AutoCleanAPI via PyWebView.
 *
 * States:
 *   • loading   — probing the bridge on startup
 *   • connected — ping() succeeded
 *   • browser   — running in a plain browser (not PyWebView)
 *   • error     — bridge probe failed
 */

import { Cpu, Wifi, WifiOff, Loader } from 'lucide-react'
import { usePyWebView } from '../../hooks/usePyWebView'
import styles from './ConnectionStatus.module.css'

function ConnectionStatus() {
  const { isNativeWindow, isConnected, loading, error, appInfo } = usePyWebView()

  if (loading) {
    return (
      <div className={[styles.pill, styles.loading].join(' ')}>
        <Loader size={12} strokeWidth={2} className={styles.spin} />
        <span>Connecting…</span>
      </div>
    )
  }

  if (!isNativeWindow) {
    return (
      <div className={[styles.pill, styles.browser].join(' ')}>
        <WifiOff size={12} strokeWidth={2} />
        <span>Browser mode</span>
      </div>
    )
  }

  if (isConnected) {
    return (
      <div className={[styles.pill, styles.connected].join(' ')} title={appInfo?.python_version ? `Python ${appInfo.python_version}` : 'Connected'}>
        <Cpu size={12} strokeWidth={2} />
        <span>Python bridge active</span>
      </div>
    )
  }

  return (
    <div className={[styles.pill, styles.error].join(' ')} title={error || 'Bridge unavailable'}>
      <WifiOff size={12} strokeWidth={2} />
      <span>Bridge error</span>
    </div>
  )
}

export default ConnectionStatus

