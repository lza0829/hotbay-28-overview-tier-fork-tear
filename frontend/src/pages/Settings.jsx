import { useEffect, useState } from 'react'
import { api } from '../api'

export default function Settings() {
  const [day, setDay] = useState('')
  const [msg, setMsg] = useState('')
  useEffect(() => { api.settings().then(s => setDay(s.营业日 || '')) }, [])
  async function save(e) {
    e.preventDefault()
    try {
      const r = await api.setDay(day)
      setMsg(`营业日已设为 ${r.营业日}`)
    } catch (err) { setMsg(err.message) }
  }
  return (
    <div className="page">
      <h1>营业日</h1>
      <form className="panel form row" onSubmit={save}>
        <label>营业日<input type="date" value={day} onChange={e => setDay(e.target.value)} /></label>
        <button type="submit">保存</button>
      </form>
      {msg && <p className="msg">{msg}</p>}
    </div>
  )
}
