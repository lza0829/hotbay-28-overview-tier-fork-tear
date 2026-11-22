import { useEffect, useState } from 'react'
import { api } from '../api'

export default function Migrates() {
  const [parts, setParts] = useState([])
  const [jobs, setJobs] = useState([])
  const [pid, setPid] = useState('')
  const [to, setTo] = useState('冷档')
  const [msg, setMsg] = useState('')
  const reload = () => { api.partitions().then(setParts); api.migrates().then(setJobs) }
  useEffect(() => { reload() }, [])
  async function start() {
    setMsg('')
    try {
      const r = await api.startMigrate({ partition_id: Number(pid), to_tier: to })
      setMsg(`迁移单 ${r.job_id} ${r.status}`)
      reload()
    } catch (e) { setMsg(e.message) }
  }
  async function finish(id, ok) {
    try {
      const r = await api.finishMigrate(id, ok)
      setMsg(`迁移单 ${r.job_id} → ${r.status}`)
      reload()
    } catch (e) { setMsg(e.message) }
  }
  return (
    <div className="page">
      <h1>冷热迁移</h1>
      <div className="panel form row">
        <label>分区<select value={pid} onChange={e => setPid(e.target.value)}>
          <option value="">选择</option>
          {parts.filter(p => p.status === '在册').map(p => <option key={p.id} value={p.id}>{p.part_key}（{p.tier}）</option>)}
        </select></label>
        <label>目标温层<select value={to} onChange={e => setTo(e.target.value)}>
          <option>热档</option><option>温档</option><option>冷档</option>
        </select></label>
        <button type="button" onClick={start}>发起迁移</button>
      </div>
      {msg && <p className="msg">{msg}</p>}
      <div className="table-wrap">
        <table>
          <thead><tr><th>单号</th><th>分区</th><th>从</th><th>到</th><th>状态</th><th>操作</th></tr></thead>
          <tbody>
            {jobs.map(j => (
              <tr key={j.id}>
                <td>{j.id}</td><td>{j.part_key}</td><td>{j.from_tier}</td><td>{j.to_tier}</td><td>{j.status}</td>
                <td>{j.status === '执行中' && (
                  <>
                    <button type="button" onClick={() => finish(j.id, true)}>完成</button>
                    <button type="button" className="ghost" onClick={() => finish(j.id, false)}>失败回滚</button>
                  </>
                )}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
