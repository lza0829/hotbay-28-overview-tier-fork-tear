// 三色分布条：唯一数据来源是后端按分区册温层列即时重算的结果。
// 深底 #140a0e 上经 CVD 全配对校验的类别色：热橙 / 温青绿 / 冷蓝。
const TIER_COLORS = {
  热档: '#d95926',
  温档: '#199e70',
  冷档: '#3987e5',
}
const TIER_ORDER = ['热档', '温档', '冷档']

export default function DistributionBar({ overview }) {
  const tri = TIER_ORDER.map(t => ({ tier: t, value: overview[t] ?? 0 }))
  const total = tri.reduce((s, x) => s + x.value, 0)
  const shareOf = v => (total > 0 ? (v / total) * 100 : 0)

  return (
    <section className="panel dist-panel">
      <div className="dist-head">
        <h2>在册分区三色分布</h2>
        <span className="dist-caliber" title={overview.分布口径}>
          口径：{overview.分布口径}
        </span>
      </div>

      {/* 高型分段条：28px，段间 2px 底色间隙，零值不绘制；可键盘聚焦，名称/数量/占比进可访问名 */}
      <div
        className="dist-bar"
        role="img"
        aria-label={tri.map(x => `${x.tier}${x.value}个`).join('，')}
      >
        {total === 0 && <div className="dist-empty">暂无在册分区</div>}
        {tri.map(x => {
          if (x.value === 0) return null
          const share = shareOf(x.value)
          return (
            <div
              key={x.tier}
              className="dist-seg"
              style={{ width: `${share}%`, background: TIER_COLORS[x.tier] }}
              tabIndex={0}
              title={`${x.tier}：${x.value} 个 · 占比 ${share.toFixed(1)}%`}
              aria-label={`${x.tier}：${x.value} 个，占比 ${share.toFixed(1)}%`}
            >
              {/* 仅在足够宽（≥12%）时印内联标签，窄段交给图例/表格，绝不裁切 */}
              {share >= 12 && <span className="dist-seg-label">{x.value}</span>}
            </div>
          )
        })}
      </div>

      {/* 图例：固定块顺序，文字用文本色，颜色只由旁边色块承载 */}
      <ul className="dist-legend">
        {tri.map(x => (
          <li key={x.tier}>
            <span className="dist-swatch" style={{ background: TIER_COLORS[x.tier] }} aria-hidden="true" />
            <span className="dist-legend-name">{x.tier}</span>
            <span className="dist-legend-val">{x.value}</span>
            <span className="dist-legend-share">
              {total > 0 ? `${shareOf(x.value).toFixed(1)}%` : '—'}
            </span>
          </li>
        ))}
      </ul>

      {/* 表格视图：保证任何窄段/零值的数都可查，颜色不单独承载信息 */}
      <details className="dist-table-wrap">
        <summary>查看分布表</summary>
        <table>
          <thead><tr><th>温层</th><th>在册分区数</th><th>占比</th></tr></thead>
          <tbody>
            {tri.map(x => (
              <tr key={x.tier}>
                <td>
                  <span className="dist-swatch" style={{ background: TIER_COLORS[x.tier] }} aria-hidden="true" />
                  {x.tier}
                </td>
                <td>{x.value}</td>
                <td>{total > 0 ? `${shareOf(x.value).toFixed(1)}%` : '—'}</td>
              </tr>
            ))}
            <tr className="dist-sum-row"><td>在册总数</td><td>{overview.在册总数 ?? total}</td><td>100%</td></tr>
          </tbody>
        </table>
      </details>

      {/* 诊断对账随总览：对不上即明确拒因，不假装绿 */}
      {overview.分布对账 && (
        <p className={overview.分布对账.一致 ? 'dist-ok' : 'dist-bad'}>
          {overview.分布对账.一致
            ? `分布对账一致 · 三色之和 ${overview.分布对账.三色之和} = 在册 ${overview.分布对账.在册总数_独立计数}`
            : `分布对账异常：${overview.分布对账.拒因}`}
        </p>
      )}
    </section>
  )
}
