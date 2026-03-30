import { summary, partyStats } from '../data/processData'

const cards = [
  { label: 'Total Constituencies', value: summary.totalSeats, color: 'from-blue-500 to-blue-700' },
  { label: 'Total Candidates', value: summary.totalCandidates.toLocaleString(), color: 'from-purple-500 to-purple-700' },
  { label: 'Total Electors', value: (summary.totalElectors / 1e6).toFixed(1) + 'M', color: 'from-emerald-500 to-emerald-700' },
  { label: 'Votes Polled', value: (summary.totalVotesPolled / 1e6).toFixed(1) + 'M', color: 'from-amber-500 to-amber-700' },
  { label: 'Avg Turnout', value: summary.avgTurnout + '%', color: 'from-rose-500 to-rose-700' },
  { label: 'Districts', value: summary.totalDistricts, color: 'from-cyan-500 to-cyan-700' },
]

const dmk = partyStats.find(p => p.party === 'DMK')
const admk = partyStats.find(p => p.party === 'ADMK')

export default function Overview() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {cards.map(c => (
          <div key={c.label} className={`bg-gradient-to-br ${c.color} rounded-xl p-4 shadow-lg`}>
            <div className="text-2xl md:text-3xl font-extrabold">{c.value}</div>
            <div className="text-sm text-white/80 mt-1">{c.label}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-slate-800/60 backdrop-blur rounded-xl p-6 border border-slate-700">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-slate-400 uppercase tracking-wide">DMK</div>
              <div className="text-5xl font-extrabold text-[#E3001B] mt-1">{dmk?.seats}</div>
              <div className="text-sm text-slate-400 mt-1">seats won</div>
            </div>
            <div className="text-right">
              <div className="text-sm text-slate-400">{dmk?.candidates} candidates</div>
              <div className="text-sm text-slate-400">{(dmk?.totalVotes / 1e6).toFixed(2)}M votes</div>
            </div>
          </div>
          <div className="mt-3 bg-slate-700 rounded-full h-3 overflow-hidden">
            <div className="bg-[#E3001B] h-full rounded-full" style={{ width: `${(dmk?.seats / 234) * 100}%` }} />
          </div>
        </div>

        <div className="bg-slate-800/60 backdrop-blur rounded-xl p-6 border border-slate-700">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-slate-400 uppercase tracking-wide">ADMK</div>
              <div className="text-5xl font-extrabold text-[#00A651] mt-1">{admk?.seats}</div>
              <div className="text-sm text-slate-400 mt-1">seats won</div>
            </div>
            <div className="text-right">
              <div className="text-sm text-slate-400">{admk?.candidates} candidates</div>
              <div className="text-sm text-slate-400">{(admk?.totalVotes / 1e6).toFixed(2)}M votes</div>
            </div>
          </div>
          <div className="mt-3 bg-slate-700 rounded-full h-3 overflow-hidden">
            <div className="bg-[#00A651] h-full rounded-full" style={{ width: `${(admk?.seats / 234) * 100}%` }} />
          </div>
        </div>
      </div>
    </div>
  )
}
