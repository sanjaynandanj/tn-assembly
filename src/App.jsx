import { useState } from 'react'
import Overview from './components/Overview'
import PartyAnalysis from './components/PartyAnalysis'
import DistrictAnalysis from './components/DistrictAnalysis'
import ConstituencyTable from './components/ConstituencyTable'
import Demographics from './components/Demographics'
import AllianceAnalysis from './components/AllianceAnalysis'

const tabs = [
  { id: 'overview', label: 'Overview' },
  { id: 'party', label: 'Party Analysis' },
  { id: 'district', label: 'District Analysis' },
  { id: 'constituency', label: 'Constituencies' },
  { id: 'demographics', label: 'Demographics' },
  { id: 'alliance', label: 'Alliances' },
]

export default function App() {
  const [activeTab, setActiveTab] = useState('overview')

  return (
    <div className="min-h-screen bg-slate-900">
      {/* Header */}
      <header className="bg-slate-800/80 backdrop-blur-md border-b border-slate-700 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div>
              <h1 className="text-xl sm:text-2xl font-extrabold">
                <span className="text-white">Tamil Nadu</span>{' '}
                <span className="text-blue-400">2021</span>{' '}
                <span className="text-slate-400 font-normal text-lg">Assembly Election</span>
              </h1>
            </div>
            <nav className="flex flex-wrap gap-1">
              {tabs.map(t => (
                <button
                  key={t.id}
                  onClick={() => setActiveTab(t.id)}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                    activeTab === t.id
                      ? 'bg-blue-500 text-white shadow-lg shadow-blue-500/25'
                      : 'text-slate-400 hover:text-white hover:bg-slate-700'
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </nav>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {activeTab === 'overview' && <Overview />}
        {activeTab === 'party' && <PartyAnalysis />}
        {activeTab === 'district' && <DistrictAnalysis />}
        {activeTab === 'constituency' && <ConstituencyTable />}
        {activeTab === 'demographics' && <Demographics />}
        {activeTab === 'alliance' && <AllianceAnalysis />}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800 py-4 text-center text-sm text-slate-500">
        Data source: TCPD Indian Elections Dataset | Tamil Nadu Assembly Election 2021
      </footer>
    </div>
  )
}
