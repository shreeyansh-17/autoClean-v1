/**
 * src/hooks/usePyWebView.js
 *
 * React hook that provides connectivity status and typed access to the
 * Python AutoCleanAPI via PyWebView.
 *
 * Usage:
 *   const { isConnected, appInfo, loading, error, ping, echo } = usePyWebView()
 */

import { useState, useEffect, useCallback } from 'react'
import {
  isPyWebView,
  ping as apiPing,
  getAppInfo as apiGetAppInfo,
  echo as apiEcho,
  openFileDialog as apiOpenFileDialog,
  getSettings as apiGetSettings,
} from '../services/pywebview'

/**
 * @typedef {Object} PyWebViewHook
 * @property {boolean} isNativeWindow  - True when running inside PyWebView.
 * @property {boolean} isConnected     - True after a successful ping.
 * @property {boolean} loading         - True while the initial ping is in flight.
 * @property {string|null} error       - Error message from the last failed call.
 * @property {object|null} appInfo     - Data returned by Python get_app_info().
 * @property {function(): Promise<object>} ping         - Re-ping the Python backend.
 * @property {function(payload: *): Promise<object>} echo - Round-trip echo test.
 * @property {function(): Promise<object>} openFileDialog - Native file picker.
 * @property {function(): Promise<object>} getSettings  - Fetch Python settings.
 */

/**
 * @returns {PyWebViewHook}
 */
export function usePyWebView() {
  const [isConnected, setIsConnected] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [appInfo, setAppInfo] = useState(null)

  // On mount: probe the bridge and fetch app info.
  useEffect(() => {
    let cancelled = false

    async function probe() {
      setLoading(true)
      setError(null)
      try {
        const pongResult = await apiPing()
        if (!cancelled) {
          setIsConnected(true)
          console.info('[usePyWebView] Bridge connected:', pongResult)
        }

        const info = await apiGetAppInfo()
        if (!cancelled) {
          setAppInfo(info)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message || 'PyWebView bridge unavailable.')
          setIsConnected(false)
          console.warn('[usePyWebView] Bridge error:', err)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    probe()
    return () => { cancelled = true }
  }, [])

  const ping = useCallback(async () => {
    setError(null)
    try {
      const result = await apiPing()
      setIsConnected(true)
      return result
    } catch (err) {
      setError(err.message)
      setIsConnected(false)
      throw err
    }
  }, [])

  const echo = useCallback(async (payload) => {
    setError(null)
    try {
      return await apiEcho(payload)
    } catch (err) {
      setError(err.message)
      throw err
    }
  }, [])

  const openFileDialog = useCallback(async () => {
    setError(null)
    try {
      return await apiOpenFileDialog()
    } catch (err) {
      setError(err.message)
      throw err
    }
  }, [])

  const getSettings = useCallback(async () => {
    setError(null)
    try {
      return await apiGetSettings()
    } catch (err) {
      setError(err.message)
      throw err
    }
  }, [])

  return {
    isNativeWindow: isPyWebView(),
    isConnected,
    loading,
    error,
    appInfo,
    ping,
    echo,
    openFileDialog,
    getSettings,
  }
}

export default usePyWebView

