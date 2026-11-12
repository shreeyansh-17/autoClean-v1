import styles from './Footer.module.css'

function Footer() {
  return (
    <footer className={styles.footer}>
      <p>© {new Date().getFullYear()} AutoClean — AI-powered CSV data cleaning</p>
    </footer>
  )
}

export default Footer

