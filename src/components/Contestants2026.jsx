import contestantsData from '../data/contestants2026.json'

const ALLIANCE_STYLES = {
  SPA: { bg: 'bg-red-900/30', border: 'border-red-500/40', badge: 'bg-red-500', label: 'SPA (DMK+)' },
  'AIADMK+': { bg: 'bg-green-900/30', border: 'border-green-500/40', badge: 'bg-green-500', label: 'AIADMK+' },
  NTK: { bg: 'bg-yellow-900/30', border: 'border-yellow-500/40', badge: 'bg-yellow-500', label: 'NTK' },
  TVK: { bg: 'bg-blue-900/30', border: 'border-blue-500/40', badge: 'bg-blue-500', label: 'TVK' },
}

export default function Contestants2026({ acNo }) {
  const data = contestantsData[String(acNo)]
  if (!data || !data.candidates?.length) return null

  return (
    <div className="mt-3 border-t border-slate-700 pt-3">
      <div className="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wide">
        2026 Election Candidates
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
        {data.candidates.map((c, i) => {
          const style = ALLIANCE_STYLES[c.alliance] || ALLIANCE_STYLES.SPA
          return (
            <div key={i} className={`rounded-lg p-3 border ${style.border} ${style.bg}`}>
              <div className="flex items-center gap-1.5 mb-2">
                <span className={`text-xs font-bold px-1.5 py-0.5 rounded text-white ${style.badge}`}>
                  {style.label}
                </span>
              </div>
              <div className="text-xs text-slate-400 mb-0.5">{c.party}</div>
              <div className="font-semibold text-sm leading-tight">
                {c.candidate === 'TBD' ? <span className="text-slate-500 italic">TBD</span> : c.candidate}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
