import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { demographics } from '../data/processData'

const GENDER_COLORS = ['#3b82f6', '#ec4899']

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 shadow-xl text-sm">
      {payload.map((p, i) => (
        <div key={i}>
          <span className="font-semibold" style={{ color: p.payload?.fill || p.color }}>{p.name}: </span>
          <span>{p.value.toLocaleString()}</span>
        </div>
      ))}
    </div>
  )
}

const GenderPieLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, name, value, percent }) => {
  const RADIAN = Math.PI / 180
  const radius = innerRadius + (outerRadius - innerRadius) * 0.5
  const x = cx + radius * Math.cos(-midAngle * RADIAN)
  const y = cy + radius * Math.sin(-midAngle * RADIAN)
  return (
    <text x={x} y={y} fill="white" textAnchor="middle" dominantBaseline="central" className="text-xs font-bold">
      {name} ({(percent * 100).toFixed(0)}%)
    </text>
  )
}

export default function Demographics() {
  return (
    <div className="space-y-6">
      {/* Gender Split */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-slate-800/60 backdrop-blur rounded-xl p-6 border border-slate-700">
          <h3 className="text-lg font-bold mb-4">Gender - All Candidates</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie data={demographics.genderAll} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={60} outerRadius={120} label={GenderPieLabel} labelLine={false}>
                {demographics.genderAll.map((d, i) => <Cell key={d.name} fill={GENDER_COLORS[i]} />)}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
              <Legend formatter={v => <span className="text-slate-300 text-sm">{v}</span>} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-slate-800/60 backdrop-blur rounded-xl p-6 border border-slate-700">
          <h3 className="text-lg font-bold mb-4">Gender - Winners Only</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie data={demographics.genderWinners} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={60} outerRadius={120} label={GenderPieLabel} labelLine={false}>
                {demographics.genderWinners.map((d, i) => <Cell key={d.name} fill={GENDER_COLORS[i]} />)}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
              <Legend formatter={v => <span className="text-slate-300 text-sm">{v}</span>} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Age Distribution */}
      <div className="bg-slate-800/60 backdrop-blur rounded-xl p-6 border border-slate-700">
        <h3 className="text-lg font-bold mb-4">Age Distribution of Winners</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={demographics.ageDistribution}>
            <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 12 }} />
            <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="value" name="Winners" fill="#8b5cf6" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Education & Profession */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-slate-800/60 backdrop-blur rounded-xl p-6 border border-slate-700">
          <h3 className="text-lg font-bold mb-4">Education Level of Winners</h3>
          <ResponsiveContainer width="100%" height={350}>
            <BarChart data={demographics.education} layout="vertical" margin={{ left: 120 }}>
              <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <YAxis type="category" dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} width={115} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="value" name="Winners" fill="#06b6d4" radius={[0, 6, 6, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-slate-800/60 backdrop-blur rounded-xl p-6 border border-slate-700">
          <h3 className="text-lg font-bold mb-4">Profession of Winners</h3>
          <ResponsiveContainer width="100%" height={350}>
            <BarChart data={demographics.profession} layout="vertical" margin={{ left: 120 }}>
              <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <YAxis type="category" dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} width={115} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="value" name="Winners" fill="#f59e0b" radius={[0, 6, 6, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
