/**
 * src/services/pywebview.js
 *
 * Bridge between the React frontend and the Python AutoCleanAPI exposed
 * by PyWebView as window.pywebview.api.*
 */

export function isPyWebView() {
  return (
    typeof window !== 'undefined' &&
    typeof window.pywebview !== 'undefined' &&
    typeof window.pywebview.api !== 'undefined'
  )
}

const READY_TIMEOUT_MS = 8000

function callPython(method, ...args) {
  return new Promise((resolve, reject) => {
    if (isPyWebView()) {
      return resolve(window.pywebview.api[method](...args))
    }

    let timer = null
    const onReady = () => {
      clearTimeout(timer)
      if (typeof window.pywebview?.api?.[method] !== 'function') {
        return reject(new Error(`PyWebView API method "${method}" not found.`))
      }
      resolve(window.pywebview.api[method](...args))
    }

    window.addEventListener('pywebviewready', onReady, { once: true })

    timer = setTimeout(() => {
      window.removeEventListener('pywebviewready', onReady)
      reject(
        new Error(
          `PyWebView not available after ${READY_TIMEOUT_MS} ms. Running in browser?`
        )
      )
    }, READY_TIMEOUT_MS)
  })
}

function browserStub(method, stubData = {}) {
  console.warn(`[pywebview] "${method}" called outside PyWebView — returning mock stub.`)
  return Promise.resolve({
    __stub: true,
    __method: method,
    status: 'browser_stub',
    ...stubData,
  })
}

// ---------------------------------------------------------------------------
// System & Diagnostics
// ---------------------------------------------------------------------------

export function ping() {
  if (!isPyWebView()) {
    return browserStub('ping', {
      message: 'pong (browser mode)',
      app: 'AutoClean Desktop',
      version: '0.1.0',
      python: '3.11 (simulated)',
      platform: navigator.platform,
    })
  }
  return callPython('ping')
}

export function getAppInfo() {
  if (!isPyWebView()) {
    return browserStub('get_app_info', {
      name: 'AutoClean Desktop',
      version: '0.1.0',
      python_version: '3.11.9',
      platform: 'Windows (browser dev)',
    })
  }
  return callPython('get_app_info')
}

export function echo(payload) {
  if (!isPyWebView()) {
    return browserStub('echo', { payload, echoed_at: new Date().toISOString() })
  }
  return callPython('echo', payload)
}

export function getSettings() {
  if (!isPyWebView()) {
    return browserStub('get_settings', {
      status: 'ok',
      groq_model: 'openai/gpt-oss-20b',
      has_groq_api_key: true,
      masked_api_key: 'sk-proj...demo',
    })
  }
  return callPython('get_settings')
}

export function saveSettings(settings) {
  if (!isPyWebView()) {
    return browserStub('save_settings', {
      status: 'success',
      message: 'Settings saved (browser stub)',
      settings,
    })
  }
  return callPython('save_settings', settings)
}

// ---------------------------------------------------------------------------
// File Dialogs
// ---------------------------------------------------------------------------

export function openFileDialog() {
  if (!isPyWebView()) {
    return browserStub('open_file_dialog', {
      path: 'laptopData.csv',
      name: 'laptopData.csv',
      suffix: 'csv',
      size_kb: 142.5,
    })
  }
  return callPython('open_file_dialog')
}

export function saveFileDialog(defaultName = 'cleaned_dataset.csv', fileType = 'csv') {
  if (!isPyWebView()) {
    return browserStub('save_file_dialog', null)
  }
  return callPython('save_file_dialog', defaultName, fileType)
}

// ---------------------------------------------------------------------------
// Dataset Operations
// ---------------------------------------------------------------------------

export function loadDataset(filePath) {
  if (!isPyWebView()) {
    return browserStub('load_dataset', {
      status: 'success',
      file_name: 'laptopData.csv',
      file_path: filePath,
      file_format: 'csv',
      file_size_kb: 142.5,
      row_count: 1303,
      column_count: 12,
      columns: ['Company', 'Product', 'TypeName', 'Inches', 'ScreenResolution', 'Cpu', 'Ram', 'Memory', 'Gpu', 'OpSys', 'Weight', 'Price'],
      preview: [],
    })
  }
  return callPython('load_dataset', filePath)
}

export function getDatasetPreview(offset = 0, limit = 50, which = 'original') {
  if (!isPyWebView()) {
    return browserStub('get_dataset_preview', {
      columns: ['Company', 'Product', 'TypeName', 'Inches', 'Ram', 'Weight', 'Price'],
      rows: [
        { _row_id: '0', Company: 'Apple', Product: 'MacBook Pro', TypeName: 'Ultrabook', Inches: '13.3', Ram: '8GB', Weight: '1.37kg', Price: '1339.69' },
        { _row_id: '1', Company: 'Apple', Product: 'Macbook Air', TypeName: 'Ultrabook', Inches: '13.3', Ram: '8GB', Weight: '1.34kg', Price: '898.94' },
      ],
      total_rows: 1303,
      offset,
      limit,
    })
  }
  return callPython('get_dataset_preview', offset, limit, which)
}

export function profileDataset() {
  if (!isPyWebView()) {
    return browserStub('profile_dataset', {
      status: 'success',
      file_name: 'laptopData.csv',
      total_rows: 1303,
      total_columns: 12,
      total_missing_cells: 363,
      missing_cells_pct: 2.32,
      exact_duplicate_rows: 29,
      near_duplicate_rows: 29,
      columns: [],
    })
  }
  return callPython('profile_dataset')
}

// ---------------------------------------------------------------------------
// Recommendations & Asynchronous Background Tasks
// ---------------------------------------------------------------------------

export function generateRecommendations() {
  if (!isPyWebView()) {
    return browserStub('generate_recommendations', {
      task_id: 'simulated_task',
      status: 'started',
    })
  }
  return callPython('generate_recommendations')
}

export function getTaskStatus(taskId) {
  if (!isPyWebView()) {
    return browserStub('get_task_status', {
      status: 'completed',
      result: {
        plan_source: 'fallback',
        recommendations: [],
      },
    })
  }
  return callPython('get_task_status', taskId)
}

export function updateActionStatus(actionId, approved) {
  if (!isPyWebView()) {
    return browserStub('update_action_status', { status: 'success', id: actionId, approved })
  }
  return callPython('update_action_status', actionId, approved)
}

// ---------------------------------------------------------------------------
// Execution, Results & Export
// ---------------------------------------------------------------------------

export function executeCleaning(selectedActionIds = null) {
  if (!isPyWebView()) {
    return browserStub('execute_cleaning', {
      task_id: 'simulated_exec',
      status: 'started',
    })
  }
  return callPython('execute_cleaning', selectedActionIds)
}

export function getCleaningResults() {
  if (!isPyWebView()) {
    return browserStub('get_cleaning_results', {
      status: 'success',
      original_rows: 1303,
      cleaned_rows: 1244,
      rows_removed: 59,
      issues_resolved: 10,
      execution_log: [],
      before_rows: [],
      after_rows: [],
      columns: [],
    })
  }
  return callPython('get_cleaning_results')
}

export function exportDataset(exportType = 'cleaned', targetPath = null) {
  if (!isPyWebView()) {
    return browserStub('export_dataset', { status: 'success', saved_path: 'dataset_cleaned.csv' })
  }
  return callPython('export_dataset', exportType, targetPath)
}

export function getCleaningHistory() {
  if (!isPyWebView()) {
    return browserStub('get_cleaning_history', { status: 'success', records: [] })
  }
  return callPython('get_cleaning_history')
}
