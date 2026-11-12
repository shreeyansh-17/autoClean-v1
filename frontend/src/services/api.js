/**
 * api.js — placeholder service layer for AutoClean API calls.
 * Replace BASE_URL and implement functions when the Python backend is ready.
 */

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

/**
 * Upload a CSV file to the backend for cleaning.
 * @param {File} file
 * @returns {Promise<object>} job result
 */
export async function uploadCSV(file) {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${BASE_URL}/upload`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    throw new Error(`Upload failed: ${response.statusText}`)
  }

  return response.json()
}

/**
 * Fetch the cleaning results for a given job ID.
 * @param {string} jobId
 * @returns {Promise<object>} results
 */
export async function fetchResults(jobId) {
  const response = await fetch(`${BASE_URL}/results/${jobId}`)

  if (!response.ok) {
    throw new Error(`Fetch results failed: ${response.statusText}`)
  }

  return response.json()
}

