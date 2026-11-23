import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'
import DistributionBar from '../components/DistributionBar'

export default function Home() {
  const [o, setO] = useState(null)
  const [err, setErr] = useState('')
  // 每次打开/手动刷新都向后端要一次即时重算结果，前端不缓存、不本地改数。
  const reload = useCallback(() => {
    api.overview().then(setO).catch(e => setErr(e.message))
  }, [])
  useEffect(() => { reload() }, [reload])
  if (err) return <p className="err">{err}</p>
  if (!o) return <p className="muted">加载总览…</p>
  const cards = [
    ['迁移执行中', o.迁移执行中], ['待销毁候选', o.待销毁候选],
    ['已销毁', o.已销毁], ['目录对象', o.目录对象],
  ]
  return (
    <div className="page">
      <header className="hero">
        <p className="eyebrow">影院素材温层</p>
        <h1>热档片间</h1>
        <p className="lede">分区在册，冷热可迁，片龄到期可销毁，目录与元数据互证。三色分布每次打开按分区册温层列即时重算。</p>
        <button type="button" className="ghost" onClick={reload}>按分区册重新重算</button>
      </header>

      <DistributionBar overview={o} />

      <div className="stat-grid">
        {cards.map(([k, v]) => (
          <div className="stat" key={k}><span>{k}</span><strong>{v}</strong></div>
        ))}
      </div>
      <section className="panel">
        <h2>片库间</h2>
        <ul className="plain">
          {o.片库间.map(v => (
            <li key={v.id}>{v.name} · 额定 {v.capacity} · {v.active ? '启用' : '停用'}</li>
          ))}
        </ul>
        {o.最近互证 && (
          <p className="muted">最近互证：{o.最近互证.status} · 漂移 {o.最近互证.drift_count} · {o.最近互证.created_at}</p>
        )}
      </section>
    </div>
  )
}
