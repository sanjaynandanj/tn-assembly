import React, { useState, useMemo } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { constituencies } from '../data/processData'
import { getPartyColor } from '../utils/colors'
import VoterDemographics from './VoterDemographics'
import Contestants2026 from './Contestants2026'

export default function ConstituencyTable() {
  const [search, setSearch] = useState('')
  const [expanded, setExpanded] = useState(null)
  const [sortBy, setSortBy] = useState('no')
  const [sortDir, setSortDir] = useState('asc')

  const filtered = useMemo(() => {
    let list = constituencies.filter(c =>
      c.name.toLowerCase().includes(search.toLowerCase()) ||
      c.district.toLowerCase().includes(search.toLowerCase()) ||
      c.winner?.Party?.toLowerCase().includes(search.toLowerCase()) ||
      c.winner?.Candidate?.toLowerCase().includes(search.toLowerCase())
    )
    list.sort((a, b) => {
      let va, vb
      if (sortBy === 'no') { va = Number(a.no); vb = Number(b.no) }
      else if (sortBy === 'name') { va = a.name; vb = b.name }
      else if (sortBy === 'margin') { va = a.margin; vb = b.margin }
      else if (sortBy === 'turnout') { va = a.turnout; vb = b.turnout }
      else { va = a[sortBy]; vb = b[sortBy] }
      if (va < vb) return sortDir === 'asc' ? -1 : 1
      if (va > vb) return sortDir === 'asc' ? 1 : -1
      return 0
    })
    return list
  }, [search, sortBy, sortDir])

  const closestMargins = useMemo(() =>
    [...constituencies].sort((a, b) => a.margin - b.margin).slice(0, 10).map(c => ({
      name: c.name,
      margin: c.margin,
      party: c.winner?.Party,
    })), [])

  const highestMargins = useMemo(() =>
    [...constituencies].sort((a, b) => b.margin - a.margin).slice(0, 10).map(c => ({
      name: c.name,
      margin: c.margin,
      party: c.winner?.Party,
    })), [])

  const handleSort = (col) => {
    if (sortBy === col) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortBy(col); setSortDir('asc') }
  }

  const SortIcon = ({ col }) => (
    <span className="text-xs ml-1">{sortBy === col ? (sortDir === 'asc' ? '▲' : '▼') : '↕'}</span>
  )

  return (
    <div className="space-y-6">
      {/* Margin Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-slate-800/60 backdrop-blur rounded-xl p-6 border border-slate-700">
          <h3 className="text-lg font-bold mb-4">Top 10 Closest Fights</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={closestMargins} layout="vertical" margin={{ left: 100 }}>
              <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <YAxis type="category" dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} width={95} />
              <Tooltip content={({ active, payload, label }) => {
                if (!active || !payload?.length) return null
                return (
                  <div className="bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm">
                    <div className="font-bold">{label}</div>
                    <div>Margin: {payload[0].value.toLocaleString()} votes</div>
                  </div>
                )
              }} />
              <Bar dataKey="margin" radius={[0, 6, 6, 0]}>
                {closestMargins.map((d, i) => (
                  <Cell key={i} fill={getPartyColor(d.party)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-slate-800/60 backdrop-blur rounded-xl p-6 border border-slate-700">
          <h3 className="text-lg font-bold mb-4">Top 10 Highest Margins</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={highestMargins} layout="vertical" margin={{ left: 100 }}>
              <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <YAxis type="category" dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} width={95} />
              <Tooltip content={({ active, payload, label }) => {
                if (!active || !payload?.length) return null
                return (
                  <div className="bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm">
                    <div className="font-bold">{label}</div>
                    <div>Margin: {payload[0].value.toLocaleString()} votes</div>
                  </div>
                )
              }} />
              <Bar dataKey="margin" radius={[0, 6, 6, 0]}>
                {highestMargins.map((d, i) => (
                  <Cell key={i} fill={getPartyColor(d.party)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Searchable Table */}
      <div className="bg-slate-800/60 backdrop-blur rounded-xl p-6 border border-slate-700">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 mb-4">
          <h3 className="text-lg font-bold">All Constituencies ({filtered.length})</h3>
          <input
            type="text"
            placeholder="Search constituency, district, party, candidate..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 text-sm w-full sm:w-80 outline-none focus:border-blue-500"
          />
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700 text-slate-400">
                <th className="text-left py-2 px-2 cursor-pointer" onClick={() => handleSort('no')}>#<SortIcon col="no" /></th>
                <th className="text-left py-2 px-2 cursor-pointer" onClick={() => handleSort('name')}>Constituency<SortIcon col="name" /></th>
                <th className="text-left py-2 px-2">District</th>
                <th className="text-left py-2 px-2">Type</th>
                <th className="text-left py-2 px-2">Winner</th>
                <th className="text-left py-2 px-2">Party</th>
                <th className="text-left py-2 px-2">Runner-up</th>
                <th className="text-right py-2 px-2 cursor-pointer" onClick={() => handleSort('margin')}>Margin<SortIcon col="margin" /></th>
                <th className="text-right py-2 px-2 cursor-pointer" onClick={() => handleSort('turnout')}>Turnout<SortIcon col="turnout" /></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(c => (
                <React.Fragment key={c.name}>
                  <tr
                    className="border-b border-slate-700/50 hover:bg-slate-700/30 cursor-pointer"
                    onClick={() => setExpanded(expanded === c.name ? null : c.name)}
                  >
                    <td className="py-2 px-2 text-slate-500">{c.no}</td>
                    <td className="py-2 px-2 font-medium">{c.name}</td>
                    <td className="py-2 px-2 text-slate-400">{c.district}</td>
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
                    <td className="py-2 px-2 text-slate-400">{c.runnerUp?.Candidate} ({c.runnerUp?.Party})</td>
                    <td className="text-right py-2 px-2">{c.margin.toLocaleString()}</td>
                    <td className="text-right py-2 px-2">{c.turnout}%</td>
                  </tr>
                  {expanded === c.name && (
                    <tr key={c.name + '-detail'}>
                      <td colSpan={9} className="bg-slate-900/50 p-4">
                        <div className="text-sm font-semibold mb-3">
                          {c.name} — {c.nCand} candidates, {c.validVotes.toLocaleString()} valid votes
                        </div>

                        {/* Electors Before/After SIR */}
                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-4">
                          <div className="bg-slate-700/50 rounded-lg p-3">
                            <div className="text-lg font-bold">{(c.electors / 1e5).toFixed(2)}L</div>
                            <div className="text-xs text-slate-400">Electors (2021)</div>
                            <div className="text-xs text-slate-500">Before SIR</div>
                          </div>
                          <div className="bg-slate-700/50 rounded-lg p-3">
                            <div className="text-lg font-bold">{(c.electorsTotal2026 / 1e5).toFixed(2)}L</div>
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
                          <div className="bg-slate-700/50 rounded-lg p-3">
                            <div className="text-lg font-bold">{c.turnout}%</div>
                            <div className="text-xs text-slate-400">Turnout (2021)</div>
                          </div>
                        </div>

                        {/* Top 4 cards */}
                        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
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
                                  style={{
                                    width: `${cand.Vote_Share_Percentage}%`,
                                    backgroundColor: getPartyColor(cand.Party)
                                  }}
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

                        {/* Rest of candidates */}
                        {c.candidates.length > 4 && (
                          <details className="text-xs">
                            <summary className="text-slate-400 cursor-pointer hover:text-slate-200 mb-2">
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
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
