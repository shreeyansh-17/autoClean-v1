import { useState, useCallback } from 'react'

/**
 * useFileUpload — manages file selection and upload state.
 * Wire up to the api service when the backend is ready.
 */
function useFileUpload() {
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)

  const selectFile = useCallback((selectedFile) => {
    setFile(selectedFile)
    setError(null)
    setResult(null)
  }, [])

  const reset = useCallback(() => {
    setFile(null)
    setUploading(false)
    setError(null)
    setResult(null)
  }, [])

  return { file, uploading, error, result, selectFile, reset }
}

export default useFileUpload

