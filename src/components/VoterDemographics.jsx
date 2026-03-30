import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'

const COLORS = { male: '#3b82f6', female: '#ec4899', third: '#a855f7' }

export default function VoterDemographics({ c }) {
  if (!c.electorsMale && !c.electorsFemale) return null

  const total = c.electorsMale + c.electorsFemale + c.electorsThirdGender
  const malePct = ((c.electorsMale / total) * 100).toFixed(1)
  const femalePct = ((c.electorsFemale / total) * 100).toFixed(1)
  const thirdPct = ((c.electorsThirdGender / total) * 100).toFixed(2)

  const pieData = [
    { name: 'Male', value: c.electorsMale },
    { name: 'Female', value: c.electorsFemale },
    ...(c.electorsThirdGender > 0 ? [{ name: 'Third Gender', value: c.electorsThirdGender }] : []),
  ]
  const pieColors = [COLORS.male, COLORS.female, COLORS.third]

  return (
    <div className="mt-3 border-t border-slate-700 pt-3">
      <div className="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wide">Voter Demographics (2026 Rolls)</div>
      <div className="flex items-center gap-4">
        {/* Mini donut */}
        <div className="w-20 h-20 flex-shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={pieData} dataKey="value" cx="50%" cy="50%" innerRadius={20} outerRadius={38} strokeWidth={0}>
                {pieData.map((d, i) => <Cell key={d.name} fill={pieColors[i]} />)}
              </Pie>
              <Tooltip content={({ active, payload }) => {
                if (!active || !payload?.length) return null
                return (
                  <div className="bg-slate-800 border border-slate-600 rounded px-2 py-1 text-xs">
                    {payload[0].name}: {payload[0].value.toLocaleString()}
                  </div>
                )
              }} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Stats */}
        <div className="flex-1 grid grid-cols-3 gap-3">
          <div>
            <div className="flex items-center gap-1.5 mb-1">
              <span className="w-2.5 h-2.5 rounded-full" style={{ background: COLORS.male }} />
              <span className="text-xs text-slate-400">Male</span>
            </div>
            <div className="text-sm font-bold">{c.electorsMale.toLocaleString()}</div>
            <div className="text-xs text-slate-500">{malePct}%</div>
          </div>
          <div>
            <div className="flex items-center gap-1.5 mb-1">
              <span className="w-2.5 h-2.5 rounded-full" style={{ background: COLORS.female }} />
              <span className="text-xs text-slate-400">Female</span>
            </div>
            <div className="text-sm font-bold">{c.electorsFemale.toLocaleString()}</div>
            <div className="text-xs text-slate-500">{femalePct}%</div>
          </div>
          <div>
            <div className="flex items-center gap-1.5 mb-1">
              <span className="w-2.5 h-2.5 rounded-full" style={{ background: COLORS.third }} />
              <span className="text-xs text-slate-400">Third Gender</span>
            </div>
            <div className="text-sm font-bold">{c.electorsThirdGender.toLocaleString()}</div>
            <div className="text-xs text-slate-500">{thirdPct}%</div>
          </div>
        </div>

        {/* Gender ratio bar */}
        <div className="flex-1">
          <div className="text-xs text-slate-400 mb-1">Gender Ratio</div>
          <div className="h-4 rounded-full overflow-hidden flex">
            <div style={{ width: `${malePct}%`, background: COLORS.male }} />
            <div style={{ width: `${femalePct}%`, background: COLORS.female }} />
            <div style={{ width: `${thirdPct}%`, background: COLORS.third }} />
          </div>
          <div className="flex justify-between text-xs text-slate-500 mt-1">
            <span>M {malePct}%</span>
            <span>F {femalePct}%</span>
          </div>
        </div>
      </div>
    </div>
  )
}
