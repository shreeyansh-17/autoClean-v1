import { useState } from 'react'
import {
  SlidersHorizontal,
  Sparkles,
  FileText,
  Bell,
  Shield,
  Info,
  Eye,
  EyeOff,
  Copy,
  Check,
  Save,
  CheckCircle2,
} from 'lucide-react'
import PyWebViewTest from '../components/PyWebViewTest/PyWebViewTest'
import styles from './SettingsPage.module.css'

function SettingsPage() {
  const [activeTab, setActiveTab] = useState('general')
  const [showApiKey, setShowApiKey] = useState(false)
  const [apiKey, setApiKey] = useState('sk-proj-98f9a8b7c6d5e4f3a2b1...')
  const [copied, setCopied] = useState(false)
  const [selectedAccent, setSelectedAccent] = useState('purple')

  // General state
  const [maxPreviewRows, setMaxPreviewRows] = useState(100)
  const [autoSave, setAutoSave] = useState(true)
  const [bgProcessing, setBgProcessing] = useState(true)

  // AI settings
  const [selectedModel, setSelectedModel] = useState('gemini-1.5-pro')
  const [temperature, setTemperature] = useState(0.2)
  const [confidence, setConfidence] = useState(0.75)

  // File defaults
  const [encoding, setEncoding] = useState('UTF-8')
  const [delimiter, setDelimiter] = useState('comma')
  const [hasHeader, setHasHeader] = useState(true)
  const [skipEmpty, setSkipEmpty] = useState(true)

  const handleCopy = () => {
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>Settings</h1>
        <p className={styles.subtitle}>
          Configure pipeline defaults, AI inference parameters, file parsers, and UI preferences.
        </p>
      </header>

      <div className={styles.layout}>
        {/* Left Sub-nav */}
        <aside className={styles.sidebarNav}>
          <div className="card" style={{ padding: 6 }}>
            {[
              { key: 'general', label: 'General', icon: SlidersHorizontal },
              { key: 'ai', label: 'AI Configuration', icon: Sparkles },
              { key: 'files', label: 'File Defaults', icon: FileText },
              { key: 'notifications', label: 'Notifications', icon: Bell },
              { key: 'privacy', label: 'Privacy & Data', icon: Shield },
              { key: 'about', label: 'About', icon: Info },
            ].map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                onClick={() => setActiveTab(key)}
                className={[
                  styles.navItem,
                  activeTab === key ? styles.navItemActive : '',
                ].join(' ')}
              >
                <Icon size={15} strokeWidth={1.75} />
                <span>{label}</span>
              </button>
            ))}
          </div>
        </aside>

        {/* Right Settings Content */}
        <div className={styles.mainContent}>
          {/* GENERAL */}
          {activeTab === 'general' && (
            <div className={styles.sectionStack}>
              <div className="card">
                <h3 className={styles.cardHeading}>Interface Appearance</h3>
                <div className={styles.settingRow}>
                  <div>
                    <div className={styles.settingLabel}>Desktop Theme</div>
                    <div className={styles.settingDesc}>Select color mode for desktop interface.</div>
                  </div>
                  <div className={styles.themeToggleGroup}>
                    <button className={[styles.themeBtn, styles.themeBtnActive].join(' ')}>
                      Dark Mode
                    </button>
                    <button className={styles.themeBtn} disabled style={{ opacity: 0.5 }}>
                      Light (Soon)
                    </button>
                  </div>
                </div>

                <div className={styles.settingRow}>
                  <div>
                    <div className={styles.settingLabel}>Accent Color</div>
                    <div className={styles.settingDesc}>Controls focus rings, badges, and primary buttons.</div>
                  </div>
                  <div className={styles.colorSwatches}>
                    {[
                      { key: 'purple', color: '#7c6af7' },
                      { key: 'blue', color: '#5b8af7' },
                      { key: 'green', color: '#34d399' },
                      { key: 'orange', color: '#fb923c' },
                    ].map((c) => (
                      <button
                        key={c.key}
                        onClick={() => setSelectedAccent(c.key)}
                        className={[
                          styles.swatch,
                          selectedAccent === c.key ? styles.swatchActive : '',
                        ].join(' ')}
                        style={{ background: c.color }}
                      />
                    ))}
                  </div>
                </div>
              </div>

              <div className="card">
                <h3 className={styles.cardHeading}>Processing & Display</h3>
                <div className={styles.settingRow}>
                  <div>
                    <div className={styles.settingLabel}>Max Preview Rows</div>
                    <div className={styles.settingDesc}>Number of rows rendered in dataset preview tables.</div>
                  </div>
                  <input
                    type="number"
                    value={maxPreviewRows}
                    onChange={(e) => setMaxPreviewRows(Number(e.target.value))}
                    className={styles.numberInput}
                  />
                </div>

                <div className={styles.settingRow}>
                  <div>
                    <div className={styles.settingLabel}>Auto-Save Cleaned Outputs</div>
                    <div className={styles.settingDesc}>Automatically save cleaned datasets to disk on finish.</div>
                  </div>
                  <button
                    type="button"
                    role="switch"
                    aria-checked={autoSave}
                    onClick={() => setAutoSave(!autoSave)}
                    className={[styles.toggle, autoSave ? styles.toggleOn : ''].join(' ')}
                  >
                    <span className={styles.toggleThumb} />
                  </button>
                </div>

                <div className={styles.settingRow}>
                  <div>
                    <div className={styles.settingLabel}>Background Worker Threading</div>
                    <div className={styles.settingDesc}>Execute heavy pipelines asynchronously in background.</div>
                  </div>
                  <button
                    type="button"
                    role="switch"
                    aria-checked={bgProcessing}
                    onClick={() => setBgProcessing(!bgProcessing)}
                    className={[styles.toggle, bgProcessing ? styles.toggleOn : ''].join(' ')}
                  >
                    <span className={styles.toggleThumb} />
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* AI CONFIG */}
          {activeTab === 'ai' && (
            <div className={styles.sectionStack}>
              <div className="card">
                <h3 className={styles.cardHeading}>Model Provider & Credentials</h3>
                <div className={styles.settingRow}>
                  <div style={{ flex: 1 }}>
                    <div className={styles.settingLabel}>API Secret Key</div>
                    <div className={styles.settingDesc}>
                      Stored strictly in OS keychain or local protected storage. Never transmitted off-device.
                    </div>
                    <div className={styles.keyInputRow}>
                      <input
                        type={showApiKey ? 'text' : 'password'}
                        value={apiKey}
                        onChange={(e) => setApiKey(e.target.value)}
                        className={styles.keyInput}
                      />
                      <button
                        className="btn btn-secondary"
                        onClick={() => setShowApiKey(!showApiKey)}
                      >
                        {showApiKey ? (
                          <EyeOff size={14} strokeWidth={1.75} />
                        ) : (
                          <Eye size={14} strokeWidth={1.75} />
                        )}
                      </button>
                      <button className="btn btn-secondary" onClick={handleCopy}>
                        {copied ? (
                          <Check size={14} strokeWidth={1.75} color="var(--accent-green)" />
                        ) : (
                          <Copy size={14} strokeWidth={1.75} />
                        )}
                      </button>
                    </div>
                  </div>
                </div>

                <div className={styles.settingRow}>
                  <div>
                    <div className={styles.settingLabel}>Active LLM Reasoning Model</div>
                    <div className={styles.settingDesc}>Select the model used for recommendation generation.</div>
                  </div>
                  <select
                    value={selectedModel}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    className={styles.selectInput}
                  >
                    <option value="gemini-1.5-pro">Gemini 1.5 Pro (Recommended)</option>
                    <option value="gemini-1.5-flash">Gemini 1.5 Flash (High Speed)</option>
                    <option value="gpt-4o">OpenAI GPT-4o</option>
                    <option value="claude-3-5-sonnet">Claude 3.5 Sonnet</option>
                  </select>
                </div>
              </div>

              <div className="card">
                <h3 className={styles.cardHeading}>Inference Hyperparameters</h3>
                <div className={styles.settingRow}>
                  <div style={{ flex: 1 }}>
                    <div className={styles.labelWithVal}>
                      <span className={styles.settingLabel}>Temperature</span>
                      <span className="badge badge-purple">{temperature}</span>
                    </div>
                    <div className={styles.settingDesc}>Lower values produce deterministic, conservative fixes.</div>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.05"
                      value={temperature}
                      onChange={(e) => setTemperature(parseFloat(e.target.value))}
                      className={styles.slider}
                    />
                  </div>
                </div>

                <div className={styles.settingRow}>
                  <div style={{ flex: 1 }}>
                    <div className={styles.labelWithVal}>
                      <span className={styles.settingLabel}>Confidence Acceptance Threshold</span>
                      <span className="badge badge-green">{Math.round(confidence * 100)}%</span>
                    </div>
                    <div className={styles.settingDesc}>Only auto-execute fixes exceeding this confidence level.</div>
                    <input
                      type="range"
                      min="0.5"
                      max="0.99"
                      step="0.01"
                      value={confidence}
                      onChange={(e) => setConfidence(parseFloat(e.target.value))}
                      className={styles.slider}
                    />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* FILE DEFAULTS */}
          {activeTab === 'files' && (
            <div className="card">
              <h3 className={styles.cardHeading}>Parser Defaults</h3>
              <div className={styles.settingRow}>
                <div>
                  <div className={styles.settingLabel}>Default Character Encoding</div>
                  <div className={styles.settingDesc}>Fallback charset for plain CSV and text files.</div>
                </div>
                <select
                  value={encoding}
                  onChange={(e) => setEncoding(e.target.value)}
                  className={styles.selectInput}
                >
                  <option value="UTF-8">UTF-8 (Standard)</option>
                  <option value="UTF-16">UTF-16</option>
                  <option value="ISO-8859-1">ISO-8859-1 (Latin-1)</option>
                </select>
              </div>

              <div className={styles.settingRow}>
                <div>
                  <div className={styles.settingLabel}>Default CSV Delimiter</div>
                  <div className={styles.settingDesc}>Column separator when auto-sniff fails.</div>
                </div>
                <select
                  value={delimiter}
                  onChange={(e) => setDelimiter(e.target.value)}
                  className={styles.selectInput}
                >
                  <option value="comma">Comma (,)</option>
                  <option value="semicolon">Semicolon (;)</option>
                  <option value="tab">Tab (\t)</option>
                  <option value="pipe">Pipe (|)</option>
                </select>
              </div>

              <div className={styles.settingRow}>
                <div>
                  <div className={styles.settingLabel}>Treat First Row as Column Headers</div>
                  <div className={styles.settingDesc}>Parse the initial line as schema header names.</div>
                </div>
                <button
                  type="button"
                  role="switch"
                  aria-checked={hasHeader}
                  onClick={() => setHasHeader(!hasHeader)}
                  className={[styles.toggle, hasHeader ? styles.toggleOn : ''].join(' ')}
                >
                  <span className={styles.toggleThumb} />
                </button>
              </div>

              <div className={styles.settingRow}>
                <div>
                  <div className={styles.settingLabel}>Automatically Drop Blank Lines</div>
                  <div className={styles.settingDesc}>Omit empty lines from dataset indexing without error.</div>
                </div>
                <button
                  type="button"
                  role="switch"
                  aria-checked={skipEmpty}
                  onClick={() => setSkipEmpty(!skipEmpty)}
                  className={[styles.toggle, skipEmpty ? styles.toggleOn : ''].join(' ')}
                >
                  <span className={styles.toggleThumb} />
                </button>
              </div>
            </div>
          )}

          {/* NOTIFICATIONS */}
          {activeTab === 'notifications' && (
            <div className="card">
              <h3 className={styles.cardHeading}>Desktop Alerts</h3>
              <div className={styles.settingRow}>
                <div>
                  <div className={styles.settingLabel}>Pipeline Completion Sounds</div>
                  <div className={styles.settingDesc}>Audible notification when asynchronous cleaning finishes.</div>
                </div>
                <button type="button" role="switch" className={[styles.toggle, styles.toggleOn].join(' ')}>
                  <span className={styles.toggleThumb} />
                </button>
              </div>
              <div className={styles.settingRow}>
                <div>
                  <div className={styles.settingLabel}>System Tray Badges</div>
                  <div className={styles.settingDesc}>Show unresolved anomaly counts in desktop system tray.</div>
                </div>
                <button type="button" role="switch" className={[styles.toggle, styles.toggleOn].join(' ')}>
                  <span className={styles.toggleThumb} />
                </button>
              </div>
            </div>
          )}

          {/* PRIVACY */}
          {activeTab === 'privacy' && (
            <div className="card">
              <h3 className={styles.cardHeading}>Data Confidentiality & Privacy</h3>
              <p className={styles.settingDesc} style={{ marginBottom: 16 }}>
                AutoClean operates on a <strong>local-first architecture</strong>. Dataset rows are never
                cached remotely or utilized for LLM weight retraining.
              </p>
              <div className={styles.settingRow}>
                <div>
                  <div className={styles.settingLabel}>Anonymize PII Prior to Profiling</div>
                  <div className={styles.settingDesc}>Mask sensitive emails, phone numbers, and SSNs.</div>
                </div>
                <button type="button" role="switch" className={[styles.toggle, styles.toggleOn].join(' ')}>
                  <span className={styles.toggleThumb} />
                </button>
              </div>
            </div>
          )}

          {/* ABOUT */}
          {activeTab === 'about' && (
            <div className={styles.sectionStack}>
              <div className="card">
                <h3 className={styles.cardHeading}>AutoClean Desktop Engine</h3>
                <p className={styles.settingDesc}>
                  High-performance automated data cleaning, profiling, and AI-assisted data engineering suite.
                </p>
                <hr className="divider" />
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 13 }}>
                  <div><strong>Version:</strong> v0.1.0-alpha</div>
                  <div><strong>Frontend Engine:</strong> React 18 &bull; Vite 5</div>
                  <div><strong>Desktop Bridge:</strong> PyWebView 6.x</div>
                  <div><strong>Iconography:</strong> Lucide React (Clean Outline System)</div>
                  <div><strong>License:</strong> MIT Open Source</div>
                </div>
              </div>

              <div className="card">
                <PyWebViewTest />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default SettingsPage

