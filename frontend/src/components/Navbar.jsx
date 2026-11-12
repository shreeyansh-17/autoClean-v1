import { Link, NavLink } from 'react-router-dom'
import styles from './Navbar.module.css'

function Navbar() {
  return (
    <header className={styles.header}>
      <nav className={styles.nav}>
        <Link to="/" className={styles.brand}>
          🧹 AutoClean
        </Link>
        <ul className={styles.links}>
          <li>
            <NavLink to="/" end className={({ isActive }) => isActive ? styles.active : ''}>
              Home
            </NavLink>
          </li>
          <li>
            <NavLink to="/upload" className={({ isActive }) => isActive ? styles.active : ''}>
              Upload
            </NavLink>
          </li>
          <li>
            <NavLink to="/results" className={({ isActive }) => isActive ? styles.active : ''}>
              Results
            </NavLink>
          </li>
        </ul>
      </nav>
    </header>
  )
}

export default Navbar

