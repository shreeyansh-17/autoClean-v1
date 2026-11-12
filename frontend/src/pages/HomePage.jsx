import { Link } from 'react-router-dom'
import styles from './HomePage.module.css'

function HomePage() {
  return (
    <div className={styles.container}>
      <section className={styles.hero}>
        <h1 className={styles.title}>🧹 AutoClean</h1>
        <p className={styles.subtitle}>
          AI-powered CSV data cleaning — detect issues, fix them, and download
          a clean dataset in seconds.
        </p>
        <div className={styles.actions}>
          <Link to="/upload" className={styles.btnPrimary}>
            Get Started
          </Link>
          <a
            href="https://github.com/"
            className={styles.btnSecondary}
            target="_blank"
            rel="noreferrer"
          >
            View on GitHub
          </a>
        </div>
      </section>

      <section className={styles.features}>
        <div className={styles.card}>
          <span className={styles.icon}>📊</span>
          <h3>Smart Profiling</h3>
          <p>Automatically profiles your CSV and detects missing values, type mismatches, and outliers.</p>
        </div>
        <div className={styles.card}>
          <span className={styles.icon}>🤖</span>
          <h3>LLM-Assisted Fixing</h3>
          <p>Uses an LLM engine to intelligently suggest and apply fixes tailored to your data.</p>
        </div>
        <div className={styles.card}>
          <span className={styles.icon}>📝</span>
          <h3>Detailed Reports</h3>
          <p>Generates a markdown report explaining every change made to your dataset.</p>
        </div>
      </section>
    </div>
  )
}

export default HomePage

