import { useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, Cell } from 'recharts'
import { districtStats } from '../data/processData'
import { getPartyColor, PARTY_COLORS } from '../utils/colors'
import VoterDemographics from './VoterDemographics'
import Contestants2026 from './Contestants2026'

function Top4Cards({ c }) {
  return (
    <tr>
      <td colSpan={6} className="bg-slate-900/60 px-4 py-4">
        <div className="text-xs text-slate-400 mb-3">
          {c.name} — {c.nCand} candidates, {c.validVotes.toLocaleString()} valid votes
        </div>

        {/* Electors Before/After SIR */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-3">
          <div className="bg-slate-700/50 rounded-lg p-2.5">
            <div className="text-base font-bold">{(c.electors / 1e5).toFixed(2)}L</div>
            <div className="text-xs text-slate-400">Electors (2021)</div>
            <div className="text-xs text-slate-500">Before SIR</div>
          </div>
          <div className="bg-slate-700/50 rounded-lg p-2.5">
            <div className="text-base font-bold">{(c.electorsTotal2026 / 1e5).toFixed(2)}L</div>
            <div className="text-xs text-slate-400">Electors (2026)</div>
            <div className="text-xs text-slate-500">After SIR</div>
            {(() => {
              const diff = c.electorsTotal2026 - c.electors
              const pct = ((diff / c.electors) * 100).toFixed(1)
              return diff !== 0 ? (
                <div className={`text-xs mt-1 font-medium ${diff > 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {diff > 0 ? '+' : ''}{(diff / 1e3).toFixed(1)}K ({diff > 0 ? '+' : ''}{pct}%)
                </div>
              ) : null
            })()}
          </div>
          <div className="bg-slate-700/50 rounded-lg p-2.5">
            <div className="text-base font-bold">{c.turnout}%</div>
            <div className="text-xs text-slate-400">Turnout (2021)</div>
          </div>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-3">
          {c.candidates.slice(0, 4).map((cand, i) => (
            <div
              key={i}
              className={`rounded-lg p-3 border ${i === 0 ? 'border-emerald-500/50 bg-emerald-900/20' : 'border-slate-700 bg-slate-800/50'}`}
            >
              <div className="flex items-center gap-1.5 mb-2">
                <span className={`text-xs font-bold px-1.5 py-0.5 rounded ${i === 0 ? 'bg-emerald-500 text-white' : 'bg-slate-700 text-slate-300'}`}>
                  #{cand.Position}
                </span>
                <span className="inline-block w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: getPartyColor(cand.Party) }} />
                <span className="text-xs text-slate-400 truncate">{cand.Party}</span>
              </div>
              <div className="font-semibold text-sm leading-tight mb-2">{cand.Candidate}</div>
              <div className="text-xl font-extrabold">{cand.Votes.toLocaleString()}</div>
              <div className="text-xs text-slate-400 mb-2">votes</div>
              <div className="bg-slate-700 rounded-full h-1.5 overflow-hidden">
                <div
                  className="h-full rounded-full"
                  style={{ width: `${cand.Vote_Share_Percentage}%`, backgroundColor: getPartyColor(cand.Party) }}
                />
              </div>
              <div className="text-xs text-slate-400 mt-1">{cand.Vote_Share_Percentage}% vote share</div>
            </div>
          ))}
        </div>
        {/* Voter Demographics */}
        <VoterDemographics c={c} />

        {/* 2026 Candidates */}
        <Contestants2026 acNo={c.no} />

        {c.candidates.length > 4 && (
          <details className="text-xs">
            <summary className="text-slate-400 cursor-pointer hover:text-slate-200">
              Show remaining {c.candidates.length - 4} candidates
            </summary>
            <table className="w-full mt-2">
              <thead>
                <tr className="text-slate-400 border-b border-slate-700">
                  <th className="text-left py-1 px-2">Pos</th>
                  <th className="text-left py-1 px-2">Candidate</th>
                  <th className="text-left py-1 px-2">Party</th>
                  <th className="text-right py-1 px-2">Votes</th>
                  <th className="text-right py-1 px-2">Vote %</th>
                  <th className="text-left py-1 px-2">Deposit</th>
                </tr>
              </thead>
              <tbody>
                {c.candidates.slice(4).map((cand, i) => (
                  <tr key={i} className="border-b border-slate-800">
                    <td className="py-1 px-2">{cand.Position}</td>
                    <td className="py-1 px-2">{cand.Candidate}</td>
                    <td className="py-1 px-2">
                      <span className="inline-block w-2 h-2 rounded-full mr-1" style={{ backgroundColor: getPartyColor(cand.Party) }} />
                      {cand.Party}
                    </td>
                    <td className="text-right py-1 px-2">{cand.Votes.toLocaleString()}</td>
                    <td className="text-right py-1 px-2">{cand.Vote_Share_Percentage}%</td>
                    <td className="py-1 px-2 text-slate-500">{cand.Deposit_Lost === 'yes' ? 'Lost' : '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </details>
        )}
      </td>
    </tr>
  )
}

const mainParties = ['DMK', 'ADMK', 'INC', 'BJP', 'PMK', 'VCK', 'CPI', 'CPM']

const stackedData = districtStats.map(d => {
  const row = { district: d.district.replace(/_/g, ' ') }
  mainParties.forEach(p => { row[p] = d.seats[p] || 0 })
  const otherSeats = Object.entries(d.seats)
    .filter(([p]) => !mainParties.includes(p))
    .reduce((s, [, v]) => s + v, 0)
  row.Others = otherSeats
  return row
})

const turnoutData = districtStats
  .map(d => ({ district: d.district.replace(/_/g, ' '), turnout: parseFloat(d.avgTurnout) }))
  .sort((a, b) => b.turnout - a.turnout)

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 shadow-xl">
      <div className="text-sm font-bold mb-1">{label}</div>
      {payload.filter(p => p.value > 0).map((p, i) => (
        <div key={i} className="text-sm">
          <span className="inline-block w-2 h-2 rounded-full mr-1" style={{ backgroundColor: p.fill }} />
          <span>{p.dataKey}: {p.value}</span>
        </div>
      ))}
    </div>
  )
}

export default function DistrictAnalysis() {
  const [selected, setSelected] = useState(null)
  const [expandedConst, setExpandedConst] = useState(null)
  const selectedDistrict = districtStats.find(d => d.district === selected)

  return (
    <div className="space-y-6">
      {/* Stacked Bar - Seats by District */}
      <div className="bg-slate-800/60 backdrop-blur rounded-xl p-6 border border-slate-700">
        <h3 className="text-lg font-bold mb-4">Seats Won by Party per District</h3>
        <ResponsiveContainer width="100%" height={Math.max(500, stackedData.length * 28)}>
          <BarChart data={stackedData} layout="vertical" margin={{ left: 120 }}>
            <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 11 }} />
            <YAxis
              type="category"
              dataKey="district"
              tick={{ fill: '#94a3b8', fontSize: 11, cursor: 'pointer' }}
              width={115}
              interval={0}
              onClick={(e) => {
                const d = districtStats.find(ds => ds.district.replace(/_/g, ' ') === e?.value)
                if (d) setSelected(d.district)
              }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend formatter={(v) => <span className="text-slate-300 text-xs">{v}</span>} />
            {[...mainParties, 'Others'].map(p => (
              <Bar key={p} dataKey={p} stackId="seats" fill={getPartyColor(p)} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Turnout by District */}
      <div className="bg-slate-800/60 backdrop-blur rounded-xl p-6 border border-slate-700">
        <h3 className="text-lg font-bold mb-4">Average Turnout % by District</h3>
        <ResponsiveContainer width="100%" height={Math.max(500, turnoutData.length * 28)}>
          <BarChart data={turnoutData} layout="vertical" margin={{ left: 120 }}>
            <XAxis type="number" domain={[60, 85]} tick={{ fill: '#94a3b8', fontSize: 11 }} />
            <YAxis type="category" dataKey="district" tick={{ fill: '#94a3b8', fontSize: 11 }} width={115} interval={0} />
            <Tooltip content={({ active, payload, label }) => {
              if (!active || !payload?.length) return null
              return (
                <div className="bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 shadow-xl text-sm">
                  <div className="font-bold">{label}</div>
                  <div>Turnout: {payload[0].value}%</div>
                </div>
              )
            }} />
            <Bar dataKey="turnout" radius={[0, 6, 6, 0]}>
              {turnoutData.map((d, i) => (
                <Cell key={i} fill={d.turnout > 78 ? '#10b981' : d.turnout > 73 ? '#3b82f6' : '#f59e0b'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* District Selector + Detail */}
      <div className="bg-slate-800/60 backdrop-blur rounded-xl p-6 border border-slate-700">
        <h3 className="text-lg font-bold mb-4">District Detail View</h3>
        <div className="flex flex-wrap gap-2 mb-4">
          {districtStats.map(d => (
            <button
              key={d.district}
              onClick={() => setSelected(d.district === selected ? null : d.district)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-all ${
                selected === d.district
                  ? 'bg-blue-500 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              {d.district}
            </button>
          ))}
        </div>
        {selectedDistrict && (
          <div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
              <div className="bg-slate-700/50 rounded-lg p-3">
                <div className="text-2xl font-bold">{selectedDistrict.constituencies.length}</div>
                <div className="text-xs text-slate-400">Constituencies</div>
              </div>
              <div className="bg-slate-700/50 rounded-lg p-3">
                <div className="text-2xl font-bold">{(selectedDistrict.totalElectors / 1e5).toFixed(1)}L</div>
                <div className="text-xs text-slate-400">Electors (2021)</div>
                <div className="text-xs text-slate-500 mt-0.5">Before SIR</div>
              </div>
              <div className="bg-slate-700/50 rounded-lg p-3">
                <div className="text-2xl font-bold">{(selectedDistrict.totalElectors2026 / 1e5).toFixed(1)}L</div>
                <div className="text-xs text-slate-400">Electors (2026)</div>
                <div className="text-xs text-slate-500 mt-0.5">After SIR</div>
                {(() => {
                  const diff = selectedDistrict.totalElectors2026 - selectedDistrict.totalElectors
                  const pct = ((diff / selectedDistrict.totalElectors) * 100).toFixed(1)
                  return diff !== 0 ? (
                    <div className={`text-xs mt-1 font-medium ${diff > 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {diff > 0 ? '+' : ''}{(diff / 1e3).toFixed(1)}K ({diff > 0 ? '+' : ''}{pct}%)
                    </div>
                  ) : null
                })()}
              </div>
              <div className="bg-slate-700/50 rounded-lg p-3">
                <div className="text-2xl font-bold">{selectedDistrict.avgTurnout}%</div>
                <div className="text-xs text-slate-400">Avg Turnout (2021)</div>
              </div>
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700 text-slate-400">
                  <th className="text-left py-2 px-2">Constituency</th>
                  <th className="text-left py-2 px-2">Type</th>
                  <th className="text-left py-2 px-2">Winner</th>
                  <th className="text-left py-2 px-2">Party</th>
                  <th className="text-right py-2 px-2">Margin</th>
                  <th className="text-right py-2 px-2">Turnout</th>
                </tr>
              </thead>
              <tbody>
                {selectedDistrict.constituencies.map(c => (
                  <>
                    <tr
                      key={c.name}
                      className="border-b border-slate-700/50 hover:bg-slate-700/30 cursor-pointer"
                      onClick={() => setExpandedConst(expandedConst === c.name ? null : c.name)}
                    >
                      <td className="py-2 px-2">{c.name}</td>
                      <td className="py-2 px-2">
                        <span className={`px-2 py-0.5 rounded text-xs ${c.type === 'SC' ? 'bg-amber-900/50 text-amber-300' : 'bg-slate-700 text-slate-300'}`}>
                          {c.type}
                        </span>
                      </td>
                      <td className="py-2 px-2">{c.winner?.Candidate}</td>
                      <td className="py-2 px-2">
                        <span className="inline-block w-2 h-2 rounded-full mr-1" style={{ backgroundColor: getPartyColor(c.winner?.Party) }} />
                        {c.winner?.Party}
                      </td>
                      <td className="text-right py-2 px-2">{c.margin.toLocaleString()}</td>
                      <td className="text-right py-2 px-2">{c.turnout}%</td>
                    </tr>
                    {expandedConst === c.name && <Top4Cards key={c.name + '-detail'} c={c} />}
                  </>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {!selectedDistrict && (
          <div className="text-slate-500 text-center py-8">Select a district to see detailed constituency breakdown</div>
        )}
      </div>
    </div>
  )
}
