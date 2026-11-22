import { NavLink, Route, Routes } from 'react-router-dom'
import Home from './pages/Home'
import Vaults from './pages/Vaults'
import Partitions from './pages/Partitions'
import Migrates from './pages/Migrates'
import Retention from './pages/Retention'
import Verify from './pages/Verify'
import Settings from './pages/Settings'

const links = [
  ['/', '总览'],
  ['/片库间', '片库间'],
  ['/分区册', '分区册'],
  ['/迁移', '冷热迁移'],
  ['/保留', '片龄保留'],
  ['/互证', '目录互证'],
  ['/营业日', '营业日'],
]

export default function App() {
  return (
    <div className="shell">
      <div className="sprocket" aria-hidden="true" />
      <main className="main">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/片库间" element={<Vaults />} />
          <Route path="/分区册" element={<Partitions />} />
          <Route path="/迁移" element={<Migrates />} />
          <Route path="/保留" element={<Retention />} />
          <Route path="/互证" element={<Verify />} />
          <Route path="/营业日" element={<Settings />} />
        </Routes>
      </main>
      <nav className="filmstrip">
        {links.map(([to, label]) => (
          <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => isActive ? 'bead on' : 'bead'}>
            {label}
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
