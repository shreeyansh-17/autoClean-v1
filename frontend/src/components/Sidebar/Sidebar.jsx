import { NavLink } from 'react-router-dom'
import {
  Sparkles,
  LayoutDashboard,
  Upload,
  BarChart2,
  CheckCircle2,
  History,
  FileText,
  Settings,
} from 'lucide-react'
import ConnectionStatus from '../ConnectionStatus/ConnectionStatus'
import styles from './Sidebar.module.css'

const navItems = [
  { icon: LayoutDashboard, label: 'Dashboard',          path: '/'               },
  { icon: Upload,          label: 'New Cleaning',       path: '/upload'         },
  { icon: BarChart2,       label: 'Data Profiling',     path: '/profiling'      },
  { icon: Sparkles,        label: 'AI Recommendations', path: '/recommendations' },
  { icon: CheckCircle2,    label: 'Cleaning Results',   path: '/results'        },
  { icon: History,         label: 'Cleaning History',   path: '/history'        },
  { icon: FileText,        label: 'Reports',            path: '/reports'        },
  { icon: Settings,        label: 'Settings',           path: '/settings'       },
]

function Sidebar() {
  return (
    <aside className={styles.sidebar}>
      {/* Logo */}
      <div className={styles.logo}>
        <Sparkles size={20} color="var(--accent-purple)" />
        <span className={styles.logoText}>AutoClean</span>
      </div>

      {/* Navigation */}
      <nav className={styles.nav}>
        <span className={styles.navLabel}>NAVIGATION</span>
        {navItems.map(({ icon: Icon, label, path }) => (
          <NavLink
            key={path}
            to={path}
            end={path === '/'}
            className={({ isActive }) =>
              [styles.navLink, isActive ? styles.navActive : ''].join(' ')
            }
          >
            <Icon size={16} strokeWidth={1.75} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Bottom area: connection status + user badge */}
      <div className={styles.bottomArea}>
        <div className={styles.statusRow}>
          <ConnectionStatus />
        </div>
        <div className={styles.userArea}>
          <div className={styles.avatar}>AC</div>
          <div className={styles.userInfo}>
            <span className={styles.userName}>AutoClean User</span>
            <span className={styles.userPlan}>Free Plan</span>
          </div>
        </div>
      </div>
    </aside>
  )
}

export default Sidebar
