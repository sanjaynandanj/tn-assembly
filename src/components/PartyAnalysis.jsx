import { useState } from 'react'
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { topPartySeats, partyStats, allCandidates } from '../data/processData'
import { getPartyColor } from '../utils/colors'

const seatsData = topPartySeats.filter(p => p.seats > 0)
const votesData = partyStats.slice(0, 10).map(p => ({
  party: p.party,
  votes: Math.round(p.totalVotes / 1000),
}))
const fieldedVsWon = partyStats.slice(0, 10).map(p => ({
  party: p.party,
  fielded: p.candidates,
  won: p.seats,
}))

// Build per-party constituency records (excluding NOTA)
const partyConstituencies = (() => {
  const map = {}
  allCandidates.forEach(c => {
    if (c.Party === 'NOTA') return
    if (!map[c.Party]) map[c.Party] = []
    map[c.Party].push(c)
  })
  return map
})()

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 shadow-xl">
      {payload.map((p, i) => (
        <div key={i} className="text-sm">
          <span className="font-semibold" style={{ color: p.color || p.fill }}>{p.name || p.dataKey}: </span>
          <span>{typeof p.value === 'number' ? p.value.toLocaleString() : p.value}</span>
        </div>
      ))}
    </div>
  )
}

const PieLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, party, seats }) => {
  const RADIAN = Math.PI / 180
  const radius = innerRadius + (outerRadius - innerRadius) * 0.5
  const x = cx + radius * Math.cos(-midAngle * RADIAN)
  const y = cy + radius * Math.sin(-midAngle * RADIAN)
  if (seats < 3) return null
  return (
    <text x={x} y={y} fill="white" textAnchor="middle" dominantBaseline="central" className="text-xs font-bold">
      {party} ({seats})
    </text>
  )
}

function PartyDetailPanel({ party, onClose }) {
  const color = getPartyColor(party)
  const candidates = partyConstituencies[party] || []
  const stats = partyStats.find(p => p.party === party)
  const [sortBy, setSortBy] = useState('position')
  const [sortDir, setSortDir] = useState('asc')

  const sorted = [...candidates].sort((a, b) => {
    let va, vb
    if (sortBy === 'position') { va = a.Position; vb = b.Position }
    else if (sortBy === 'constituency') { va = a.Constituency_Name; vb = b.Constituency_Name }
    else if (sortBy === 'votes') { va = a.Votes; vb = b.Votes }
    else if (sortBy === 'votePct') { va = a.Vote_Share_Percentage; vb = b.Vote_Share_Percentage }
    else { va = a.District_Name; vb = b.District_Name }
    if (va < vb) return sortDir === 'asc' ? -1 : 1
    if (va > vb) return sortDir === 'asc' ? 1 : -1
    return 0
  })

  const handleSort = (col) => {
    if (sortBy === col) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortBy(col); setSortDir('asc') }
  }

  const SortIcon = ({ col }) => (
    <span className="text-xs ml-1 opacity-60">{sortBy === col ? (sortDir === 'asc' ? '▲' : '▼') : '↕'}</span>
  )

  const won = candidates.filter(c => c.Position === 1).length
  const lost = candidates.filter(c => c.Position !== 1).length
  const depositsLost = candidates.filter(c => c.Deposit_Lost === 'yes').length
  const totalVotes = candidates.reduce((s, c) => s + c.Votes, 0)
  const avgVoteShare = candidates.length > 0
    ? (candidates.reduce((s, c) => s + c.Vote_Share_Percentage, 0) / candidates.length).toFixed(1)
    : 0

  return (
    <div className="bg-slate-800/60 backdrop-blur rounded-xl border border-slate-600 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700" style={{ borderLeftWidth: 4, borderLeftColor: color }}>
        <div className="flex items-center gap-3">
          <span className="w-4 h-4 rounded-full" style={{ backgroundColor: color }} />
          <h3 className="text-xl font-extrabold">{party}</h3>
          <span className="text-slate-400 text-sm">— full constituency breakdown</span>
        </div>
        <button onClick={onClose} className="text-slate-400 hover:text-white text-xl leading-none">✕</button>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 p-6 border-b border-slate-700">
        {[
          { label: 'Contested', value: candidates.length },
          { label: 'Won', value: won, highlight: 'text-emerald-400' },
          { label: 'Lost', value: lost, highlight: 'text-rose-400' },
          { label: 'Total Votes', value: totalVotes.toLocaleString() },
          { label: 'Avg Vote Share', value: avgVoteShare + '%' },
        ].map(s => (
          <div key={s.label} className="bg-slate-700/50 rounded-lg p-3 text-center">
            <div className={`text-2xl font-extrabold ${s.highlight || ''}`}>{s.value}</div>
            <div className="text-xs text-slate-400 mt-1">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Constituency table */}
      <div className="p-6 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-700 text-slate-400">
              <th className="text-left py-2 px-3 cursor-pointer" onClick={() => handleSort('constituency')}>
                Constituency <SortIcon col="constituency" />
              </th>
              <th className="text-left py-2 px-3 cursor-pointer" onClick={() => handleSort('district')}>
                District <SortIcon col="district" />
              </th>
              <th className="text-left py-2 px-3">Type</th>
              <th className="text-left py-2 px-3">Candidate</th>
              <th className="text-center py-2 px-3 cursor-pointer" onClick={() => handleSort('position')}>
                Position <SortIcon col="position" />
              </th>
              <th className="text-left py-2 px-3">Result</th>
              <th className="text-right py-2 px-3 cursor-pointer" onClick={() => handleSort('votes')}>
                Votes <SortIcon col="votes" />
              </th>
              <th className="text-right py-2 px-3 cursor-pointer" onClick={() => handleSort('votePct')}>
                Vote % <SortIcon col="votePct" />
              </th>
              <th className="text-right py-2 px-3">Margin</th>
              <th className="text-left py-2 px-3">Deposit</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((c, i) => {
              const won = c.Position === 1
              return (
                <tr key={i} className={`border-b border-slate-700/50 hover:bg-slate-700/20 ${won ? 'bg-emerald-900/10' : ''}`}>
                  <td className="py-2 px-3 font-medium">{c.Constituency_Name}</td>
                  <td className="py-2 px-3 text-slate-400">{c.District_Name}</td>
                  <td className="py-2 px-3">
                    <span className={`px-2 py-0.5 rounded text-xs ${c.Constituency_Type === 'SC' ? 'bg-amber-900/50 text-amber-300' : 'bg-slate-700 text-slate-300'}`}>
                      {c.Constituency_Type}
                    </span>
                  </td>
                  <td className="py-2 px-3">{c.Candidate}</td>
                  <td className="text-center py-2 px-3">
                    <span className={`font-bold ${won ? 'text-emerald-400' : 'text-slate-400'}`}>#{c.Position}</span>
                  </td>
                  <td className="py-2 px-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${won ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'}`}>
                      {won ? 'WON' : 'LOST'}
                    </span>
                  </td>
                  <td className="text-right py-2 px-3 font-mono">{c.Votes.toLocaleString()}</td>
                  <td className="text-right py-2 px-3">
                    <div className="flex items-center justify-end gap-2">
                      <div className="w-16 bg-slate-700 rounded-full h-1.5 overflow-hidden">
                        <div className="h-full rounded-full" style={{ width: `${Math.min(c.Vote_Share_Percentage, 100)}%`, backgroundColor: color }} />
                      </div>
                      <span className="font-mono text-xs w-10 text-right">{c.Vote_Share_Percentage}%</span>
                    </div>
                  </td>
                  <td className="text-right py-2 px-3 font-mono text-slate-400">
                    {won ? c.Margin.toLocaleString() : '—'}
                  </td>
                  <td className="py-2 px-3">
                    {c.Deposit_Lost === 'yes'
                      ? <span className="text-xs text-rose-400">Lost</span>
                      : <span className="text-xs text-slate-500">—</span>}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default function PartyAnalysis() {
  const [selectedParty, setSelectedParty] = useState(null)

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Donut - Seats Won */}
        <div className="bg-slate-800/60 backdrop-blur rounded-xl p-6 border border-slate-700">
          <h3 className="text-lg font-bold mb-4">Seats Won by Party</h3>
          <ResponsiveContainer width="100%" height={350}>
            <PieChart>
              <Pie
                data={seatsData}
                dataKey="seats"
                nameKey="party"
                cx="50%"
                cy="50%"
                innerRadius={70}
                outerRadius={140}
                label={PieLabel}
                labelLine={false}
                onClick={d => setSelectedParty(d.party)}
                style={{ cursor: 'pointer' }}
              >
                {seatsData.map(d => (
                  <Cell key={d.party} fill={getPartyColor(d.party)} stroke={selectedParty === d.party ? '#fff' : 'transparent'} strokeWidth={2} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
              <Legend formatter={(v) => <span className="text-slate-300 text-sm cursor-pointer hover:text-white" onClick={() => setSelectedParty(v)}>{v}</span>} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Bar - Total Votes (in thousands) */}
        <div className="bg-slate-800/60 backdrop-blur rounded-xl p-6 border border-slate-700">
          <h3 className="text-lg font-bold mb-4">Total Votes by Party (in thousands)</h3>
          <ResponsiveContainer width="100%" height={350}>
            <BarChart data={votesData} layout="vertical" margin={{ left: 60 }}>
              <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 12 }} />
              <YAxis type="category" dataKey="party" tick={{ fill: '#94a3b8', fontSize: 12, cursor: 'pointer' }} width={55} onClick={e => setSelectedParty(e?.value)} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="votes" radius={[0, 6, 6, 0]} onClick={d => setSelectedParty(d.party)} style={{ cursor: 'pointer' }}>
                {votesData.map(d => (
                  <Cell key={d.party} fill={getPartyColor(d.party)} opacity={selectedParty && selectedParty !== d.party ? 0.4 : 1} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Bar - Candidates Fielded vs Won */}
        <div className="bg-slate-800/60 backdrop-blur rounded-xl p-6 border border-slate-700 lg:col-span-2">
          <h3 className="text-lg font-bold mb-4">Candidates Fielded vs Seats Won (Top 10 Parties)</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={fieldedVsWon} margin={{ left: 10 }}>
              <XAxis dataKey="party" tick={{ fill: '#94a3b8', fontSize: 12, cursor: 'pointer' }} onClick={e => setSelectedParty(e?.value)} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} />
              <Tooltip content={<CustomTooltip />} />
              <Legend formatter={(v) => <span className="text-slate-300 text-sm">{v === 'fielded' ? 'Candidates Fielded' : 'Seats Won'}</span>} />
              <Bar dataKey="fielded" fill="#64748b" radius={[4, 4, 0, 0]} />
              <Bar dataKey="won" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Party Detail Panel */}
      {selectedParty && (
        <PartyDetailPanel party={selectedParty} onClose={() => setSelectedParty(null)} />
      )}

      {/* Party Performance Table */}
      <div className="bg-slate-800/60 backdrop-blur rounded-xl p-6 border border-slate-700">
        <h3 className="text-lg font-bold mb-4">Party Performance Summary <span className="text-sm font-normal text-slate-400 ml-2">— click a party name to see details</span></h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700 text-slate-400">
                <th className="text-left py-2 px-3">Party</th>
                <th className="text-right py-2 px-3">Seats</th>
                <th className="text-right py-2 px-3">Candidates</th>
                <th className="text-right py-2 px-3">Win %</th>
                <th className="text-right py-2 px-3">Total Votes</th>
                <th className="text-right py-2 px-3">Deposits Lost</th>
              </tr>
            </thead>
            <tbody>
              {partyStats.slice(0, 20).map(p => (
                <tr
                  key={p.party}
                  className={`border-b border-slate-700/50 cursor-pointer transition-colors ${selectedParty === p.party ? 'bg-slate-700/50' : 'hover:bg-slate-700/30'}`}
                  onClick={() => setSelectedParty(selectedParty === p.party ? null : p.party)}
                >
                  <td className="py-2 px-3 font-medium">
                    <span className="inline-block w-3 h-3 rounded-full mr-2" style={{ backgroundColor: getPartyColor(p.party) }} />
                    <span className="hover:underline">{p.party}</span>
                  </td>
                  <td className="text-right py-2 px-3 font-bold">{p.seats}</td>
                  <td className="text-right py-2 px-3">{p.candidates}</td>
                  <td className="text-right py-2 px-3">{p.candidates > 0 ? ((p.seats / p.candidates) * 100).toFixed(1) : 0}%</td>
                  <td className="text-right py-2 px-3">{p.totalVotes.toLocaleString()}</td>
                  <td className="text-right py-2 px-3">{p.depositsLost}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
