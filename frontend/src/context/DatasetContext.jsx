import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import * as api from '../services/pywebview'

const DatasetContext = createContext(null)

export function DatasetProvider({ children }) {
  // 1. File & Preview State
  const [fileInfo, setFileInfo] = useState(null)
  const [previewRows, setPreviewRows] = useState([])
  const [columns, setColumns] = useState([])
  const [isLoadingFile, setIsLoadingFile] = useState(false)
  const [fileError, setFileError] = useState(null)

  // 2. Profiling State
  const [profilingData, setProfilingData] = useState(null)
  const [isProfiling, setIsProfiling] = useState(false)
  const [profileError, setProfileError] = useState(null)

  // 3. AI Recommendations State
  const [recommendations, setRecommendations] = useState([])
  const [planSource, setPlanSource] = useState('llm')
  const [llmError, setLlmError] = useState(null)
  const [isLoadingRecs, setIsLoadingRecs] = useState(false)
  const [recError, setRecError] = useState(null)

  // 4. Execution & Results State
  const [cleaningResults, setCleaningResults] = useState(null)
  const [isCleaning, setIsCleaning] = useState(false)
  const [cleanError, setCleanError] = useState(null)

  // 5. History State
  const [historyRecords, setHistoryRecords] = useState([])

  // Refresh history on mount
  const refreshHistory = useCallback(async () => {
    try {
      const res = await api.getCleaningHistory()
      if (res && res.records) {
        setHistoryRecords(res.records)
      }
    } catch (e) {
      console.warn('Could not load history:', e)
    }
  }, [])

  useEffect(() => {
    refreshHistory()
  }, [refreshHistory])

  // Helper to poll background task
  const pollTask = async (taskId, intervalMs = 800, maxAttempts = 60) => {
    for (let i = 0; i < maxAttempts; i++) {
      await new Promise((r) => setTimeout(r, intervalMs))
      const task = await api.getTaskStatus(taskId)
      if (task.status === 'completed') {
        return task.result
      }
      if (task.status === 'failed') {
        throw new Error(task.error || 'Background task failed.')
      }
    }
    throw new Error('Task timed out.')
  }

  // Load a dataset from disk
  const loadDatasetFile = useCallback(async (filePath) => {
    setIsLoadingFile(true)
    setFileError(null)
    setProfilingData(null)
    setRecommendations([])
    setCleaningResults(null)
    try {
      const res = await api.loadDataset(filePath)
      if (res.status === 'error') {
        throw new Error(res.error || 'Failed to load dataset.')
      }
      setFileInfo({
        name: res.file_name,
        path: res.file_path,
        format: res.file_format?.toUpperCase(),
        size_kb: res.file_size_kb,
        row_count: res.row_count,
        column_count: res.column_count,
      })
      setColumns(res.columns || [])
      setPreviewRows(res.preview || [])
      return res
    } catch (err) {
      setFileError(err.message)
      throw err
    } finally {
      setIsLoadingFile(false)
    }
  }, [])

  // Run profiling
  const runProfiling = useCallback(async () => {
    setIsProfiling(true)
    setProfileError(null)
    try {
      const prof = await api.profileDataset()
      if (prof.status === 'error') {
        throw new Error(prof.error || 'Profiling failed.')
      }
      setProfilingData(prof)
      return prof
    } catch (err) {
      setProfileError(err.message)
      throw err
    } finally {
      setIsProfiling(false)
    }
  }, [])

  // Generate recommendations
  const runGenerateRecommendations = useCallback(async () => {
    setIsLoadingRecs(true)
    setRecError(null)
    try {
      const startRes = await api.generateRecommendations()
      if (startRes.status === 'error') {
        throw new Error(startRes.error || 'Could not start recommendation generation.')
      }
      const taskResult = await pollTask(startRes.task_id)
      setPlanSource(taskResult.plan_source || 'llm')
      setLlmError(taskResult.llm_error || null)
      setRecommendations(taskResult.recommendations || [])
      return taskResult
    } catch (err) {
      setRecError(err.message)
      throw err
    } finally {
      setIsLoadingRecs(false)
    }
  }, [])

  // Toggle individual action approval
  const toggleAction = useCallback(async (actionId, approved) => {
    try {
      await api.updateActionStatus(actionId, approved)
      setRecommendations((prev) =>
        prev.map((rec) => (rec.id === actionId ? { ...rec, approved } : rec))
      )
    } catch (err) {
      console.error('Failed to update action:', err)
    }
  }, [])

  // Approve all
  const approveAllActions = useCallback(async () => {
    try {
      for (const rec of recommendations) {
        await api.updateActionStatus(rec.id, true)
      }
      setRecommendations((prev) => prev.map((r) => ({ ...r, approved: true })))
    } catch (err) {
      console.error('Failed to approve all:', err)
    }
  }, [recommendations])

  // Execute cleaning
  const runCleaning = useCallback(async (selectedIds = null) => {
    setIsCleaning(true)
    setCleanError(null)
    try {
      const startRes = await api.executeCleaning(selectedIds)
      if (startRes.status === 'error') {
        throw new Error(startRes.error || 'Could not start cleaning execution.')
      }
      const finalResult = await pollTask(startRes.task_id, 1000, 90)
      setCleaningResults(finalResult)
      await refreshHistory()
      return finalResult
    } catch (err) {
      setCleanError(err.message)
      throw err
    } finally {
      setIsCleaning(false)
    }
  }, [refreshHistory])

  // Export dataset
  const exportFile = useCallback(async (exportType, targetPath = null) => {
    try {
      const res = await api.exportDataset(exportType, targetPath)
      return res
    } catch (err) {
      console.error('Export error:', err)
      throw err
    }
  }, [])

  return (
    <DatasetContext.Provider
      value={{
        fileInfo,
        previewRows,
        columns,
        isLoadingFile,
        fileError,
        loadDatasetFile,
        profilingData,
        isProfiling,
        profileError,
        runProfiling,
        recommendations,
        planSource,
        llmError,
        isLoadingRecs,
        recError,
        runGenerateRecommendations,
        toggleAction,
        approveAllActions,
        cleaningResults,
        isCleaning,
        cleanError,
        runCleaning,
        exportFile,
        historyRecords,
        refreshHistory,
      }}
    >
      {children}
    </DatasetContext.Provider>
  )
}

export function useDataset() {
  const context = useContext(DatasetContext)
  if (!context) {
    throw new Error('useDataset must be used within a DatasetProvider')
  }
  return context
}

