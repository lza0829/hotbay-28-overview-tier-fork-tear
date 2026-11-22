import { useEffect, useState } from 'react'
import { api } from '../api'

export default function Verify() {
  const [inv, setInv] = useState([])
  const [runs, setRuns] = useState([])
  const [last, setLast] = useState(null)
  const [msg, setMsg] = useState('')
  const [check, setCheck] = useState(null)
  const [checkMsg, setCheckMsg] = useState('')
  const reload = () => {
    api.inventory().then(setInv)
    api.verifyRuns().then(setRuns)
    api.distributionCheck().then(setCheck).catch(e => setCheckMsg(e.message))
  }
  useEffect(() => { reload() }, [])
  async function run() {
    setMsg('')
    try {
      const r = await api.runVerify()
      setLast(r)
      setMsg(`互证${r.status} · 漂移 ${r.drift_count}`)
      reload()
    } catch (e) { setMsg(e.message) }
  }
  // 诊断侧尝试改三色分布：架构上没有可改的分布账，后端整笔 403，回执与分布都不变。
  async function tryTamper() {
    setCheckMsg('')
    try {
      await api.tamperDistribution()
      setCheckMsg('异常：改数竟被接受（违反架构）')
    } catch (e) {
      setCheckMsg(`已拒绝诊断改数：${e.message}`)
    }
    api.distributionCheck().then(setCheck)
  }
  return (
    <div className="page">
      <h1>目录互证</h1>
      <p className="lede">对照湖目录对象清单与分区素材元数据，不是网盘文件浏览器。诊断只读、只对账，不产生登记/迁移/销毁回执。</p>
      <button type="button" onClick={run}>跑一次互证</button>
      {msg && <p className="msg">{msg}</p>}
      {last && last.drifts?.length > 0 && (
        <ul className="plain">{last.drifts.map((d, i) => <li key={i}>{d.对象键} · {d.问题}</li>)}</ul>
      )}

      <section className="panel">
        <h2>三色分布对账（只读，按总览同一口径重算）</h2>
        {check ? (
          <>
            <p className={check.一致 ? 'dist-ok' : 'dist-bad'}>
              {check.一致
                ? `对账一致 · 三色之和 ${check.三色之和} = 在册 ${check.在册总数_独立计数}`
                : `对账异常：${check.拒因}`}
            </p>
            <ul className="plain">
              <li>热档 {check.三色重算.热档} · 温档 {check.三色重算.温档} · 冷档 {check.三色重算.冷档}</li>
              <li className="muted">口径：{check.口径}（架构：{check.架构}）</li>
            </ul>
          </>
        ) : <p className="muted">{checkMsg || '加载对账…'}</p>}
        <button type="button" className="ghost" onClick={tryTamper}>诊断页尝试改三色分布（应被拒绝）</button>
        {checkMsg && <p className="dist-bad">{checkMsg}</p>}
      </section>

      <h2>目录清单</h2>
      <div className="table-wrap">
        <table>
          <thead><tr><th>对象键</th><th>字节</th><th>片库间</th><th>扫描时刻</th></tr></thead>
          <tbody>{inv.map(x => <tr key={x.id}><td>{x.object_key}</td><td>{x.bytes}</td><td>{x.vault_name}</td><td>{x.scanned_at}</td></tr>)}</tbody>
        </table>
      </div>
      <h2>互证流水</h2>
      <div className="table-wrap">
        <table>
          <thead><tr><th>编号</th><th>状态</th><th>漂移数</th><th>时间</th></tr></thead>
          <tbody>{runs.map(r => <tr key={r.id}><td>{r.id}</td><td>{r.status}</td><td>{r.drift_count}</td><td>{r.created_at}</td></tr>)}</tbody>
        </table>
      </div>
    </div>
  )
}
