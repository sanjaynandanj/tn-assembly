import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { allianceStats } from '../data/processData'
import { ALLIANCE_COLORS } from '../utils/colors'

const seatsData = allianceStats.map(a => ({ name: a.name, value: a.seats }))
const votesData = allianceStats.map(a => ({ name: a.name, votes: Math.round(a.votes / 1e6 * 100) / 100 }))
const allianceColors = ['#E3001B', '#00A651', '#94A3B8']

const PieLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, name, value }) => {
  const RADIAN = Math.PI / 180
  const radius = innerRadius + (outerRadius - innerRadius) * 0.5
  const x = cx + radius * Math.cos(-midAngle * RADIAN)
  const y = cy + radius * Math.sin(-midAngle * RADIAN)
  return (
    <text x={x} y={y} fill="white" textAnchor="middle" dominantBaseline="central" className="text-sm font-bold">
      {value}
    </text>
  )
}

export default function AllianceAnalysis() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Seats Donut */}
        <div className="bg-slate-800/60 backdrop-blur rounded-xl p-6 border border-slate-700">
          <h3 className="text-lg font-bold mb-4">Alliance-wise Seats</h3>
          <ResponsiveContainer width="100%" height={350}>
            <PieChart>
              <Pie data={seatsData} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={70} outerRadius={140} label={PieLabel} labelLine={false}>
                {seatsData.map((d, i) => <Cell key={d.name} fill={allianceColors[i]} />)}
              </Pie>
              <Tooltip content={({ active, payload }) => {
                if (!active || !payload?.length) return null
                return (
                  <div className="bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm">
                    <div className="font-bold">{payload[0].name}</div>
                    <div>{payload[0].value} seats</div>
                  </div>
                )
              }} />
              <Legend formatter={v => <span className="text-slate-300 text-sm">{v}</span>} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Votes Bar */}
        <div className="bg-slate-800/60 backdrop-blur rounded-xl p-6 border border-slate-700">
          <h3 className="text-lg font-bold mb-4">Alliance-wise Votes (in millions)</h3>
          <ResponsiveContainer width="100%" height={350}>
            <BarChart data={votesData}>
              <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 12 }} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} />
              <Tooltip content={({ active, payload }) => {
                if (!active || !payload?.length) return null
                return (
                  <div className="bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm">
                    <div className="font-bold">{payload[0].payload.name}</div>
                    <div>{payload[0].value}M votes</div>
                  </div>
                )
              }} />
              <Bar dataKey="votes" radius={[6, 6, 0, 0]}>
                {votesData.map((d, i) => <Cell key={d.name} fill={allianceColors[i]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Alliance Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {allianceStats.map((a, i) => (
          <div key={a.name} className="bg-slate-800/60 backdrop-blur rounded-xl p-6 border border-slate-700">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-4 h-4 rounded-full" style={{ backgroundColor: allianceColors[i] }} />
              <h3 className="text-lg font-bold">{a.name}</h3>
            </div>
            <div className="grid grid-cols-2 gap-3 mb-4">
              <div className="bg-slate-700/50 rounded-lg p-3 text-center">
                <div className="text-3xl font-extrabold">{a.seats}</div>
                <div className="text-xs text-slate-400">Seats</div>
              </div>
              <div className="bg-slate-700/50 rounded-lg p-3 text-center">
                <div className="text-3xl font-extrabold">{(a.votes / 1e6).toFixed(1)}M</div>
                <div className="text-xs text-slate-400">Votes</div>
              </div>
            </div>
            <div className="space-y-2">
              {Object.entries(a.parties).sort((a, b) => b[1] - a[1]).map(([party, seats]) => (
                <div key={party} className="flex justify-between items-center text-sm">
                  <span>{party}</span>
                  <span className="font-bold">{seats} seats</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
