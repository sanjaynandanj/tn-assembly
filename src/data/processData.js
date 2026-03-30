import rawData from '../../tn-2021.json'
import { DMK_ALLIANCE, ADMK_ALLIANCE } from '../utils/colors'

const fields = rawData.fields.map(f => f.id)

export const allCandidates = rawData.records.map(r => {
  const obj = {}
  fields.forEach((f, i) => { obj[f] = r[i] })
  obj.Votes = Number(obj.Votes) || 0
  obj.Age = Number(obj.Age) || 0
  obj.Valid_Votes = Number(obj.Valid_Votes) || 0
  obj.Electors = Number(obj.Electors) || 0
  obj.Turnout_Percentage = parseFloat(obj.Turnout_Percentage) || 0
  obj.Vote_Share_Percentage = parseFloat(obj.Vote_Share_Percentage) || 0
  obj.Margin = Number(obj.Margin) || 0
  obj.Margin_Percentage = parseFloat(obj.Margin_Percentage) || 0
  obj.N_Cand = Number(obj.N_Cand) || 0
  obj.Position = Number(obj.Position) || 0
  obj.Electors_Male = Number(obj.Electors_Male) || 0
  obj.Electors_Female = Number(obj.Electors_Female) || 0
  obj.Electors_ThirdGender = Number(obj.Electors_ThirdGender) || 0
  obj.Electors_Total_2026 = Number(obj.Electors_Total_2026) || 0
  return obj
})

export const winners = allCandidates.filter(c => c.Position === 1)
export const runnersUp = allCandidates.filter(c => c.Position === 2)

// Party-wise aggregates
export const partyStats = (() => {
  const map = {}
  allCandidates.forEach(c => {
    if (c.Party === 'NOTA') return
    if (!map[c.Party]) {
      map[c.Party] = { party: c.Party, seats: 0, candidates: 0, totalVotes: 0, depositsLost: 0 }
    }
    map[c.Party].candidates++
    map[c.Party].totalVotes += c.Votes
    if (c.Position === 1) map[c.Party].seats++
    if (c.Deposit_Lost === 'yes') map[c.Party].depositsLost++
  })
  return Object.values(map).sort((a, b) => b.seats - a.seats || b.totalVotes - a.totalVotes)
})()

// Top parties for charts (top 8 + Others)
export const topPartySeats = (() => {
  const top = partyStats.filter(p => p.seats > 0)
  const others = partyStats.filter(p => p.seats === 0)
  const othersTotal = others.reduce((s, p) => s + p.totalVotes, 0)
  return [
    ...top,
    { party: 'Others', seats: 0, candidates: others.reduce((s, p) => s + p.candidates, 0), totalVotes: othersTotal, depositsLost: others.reduce((s, p) => s + p.depositsLost, 0) }
  ]
})()

// District-wise aggregates
export const districtStats = (() => {
  const map = {}
  winners.forEach(w => {
    const d = w.District_Name
    if (!map[d]) map[d] = { district: d, seats: {}, totalElectors: 0, constituencies: [], avgTurnout: 0 }
    map[d].seats[w.Party] = (map[d].seats[w.Party] || 0) + 1
  })
  // Add constituency details
  const constMap = {}
  allCandidates.forEach(c => {
    const key = c.Constituency_Name
    if (!constMap[key]) {
      constMap[key] = {
        name: key,
        no: c.Constituency_No,
        district: c.District_Name,
        type: c.Constituency_Type,
        subRegion: c.Sub_Region,
        electors: c.Electors,
        validVotes: c.Valid_Votes,
        turnout: c.Turnout_Percentage,
        nCand: c.N_Cand,
        electorsMale: c.Electors_Male,
        electorsFemale: c.Electors_Female,
        electorsThirdGender: c.Electors_ThirdGender,
        electorsTotal2026: c.Electors_Total_2026,
        candidates: []
      }
    }
    constMap[key].candidates.push(c)
  })
  // Sort candidates by position within each constituency
  Object.values(constMap).forEach(co => {
    co.candidates.sort((a, b) => a.Position - b.Position)
    co.winner = co.candidates[0]
    co.runnerUp = co.candidates[1]
    co.margin = co.winner?.Margin || 0
    co.marginPct = co.winner?.Margin_Percentage || 0
  })

  Object.values(map).forEach(d => {
    d.constituencies = Object.values(constMap).filter(c => c.district === d.district)
    d.totalElectors = d.constituencies.reduce((s, c) => s + c.electors, 0)
    d.totalElectors2026 = d.constituencies.reduce((s, c) => s + (c.electorsTotal2026 || 0), 0)
    d.avgTurnout = d.constituencies.length > 0
      ? (d.constituencies.reduce((s, c) => s + c.turnout, 0) / d.constituencies.length).toFixed(1)
      : 0
  })

  return Object.values(map).sort((a, b) => a.district.localeCompare(b.district))
})()

export const constituencies = (() => {
  const map = {}
  allCandidates.forEach(c => {
    const key = c.Constituency_Name
    if (!map[key]) {
      map[key] = {
        name: key,
        no: c.Constituency_No,
        district: c.District_Name,
        type: c.Constituency_Type,
        subRegion: c.Sub_Region,
        electors: c.Electors,
        validVotes: c.Valid_Votes,
        turnout: c.Turnout_Percentage,
        nCand: c.N_Cand,
        electorsMale: c.Electors_Male,
        electorsFemale: c.Electors_Female,
        electorsThirdGender: c.Electors_ThirdGender,
        electorsTotal2026: c.Electors_Total_2026,
        candidates: []
      }
    }
    map[key].candidates.push(c)
  })
  Object.values(map).forEach(co => {
    co.candidates.sort((a, b) => a.Position - b.Position)
    co.winner = co.candidates[0]
    co.runnerUp = co.candidates[1]
    co.margin = co.winner?.Margin || 0
    co.marginPct = co.winner?.Margin_Percentage || 0
  })
  return Object.values(map).sort((a, b) => Number(a.no) - Number(b.no))
})()

// Summary stats
export const summary = {
  totalSeats: winners.length,
  totalCandidates: allCandidates.filter(c => c.Party !== 'NOTA').length,
  totalElectors: winners.reduce((s, w) => s + w.Electors, 0),
  totalVotesPolled: winners.reduce((s, w) => s + w.Valid_Votes, 0),
  avgTurnout: (winners.reduce((s, w) => s + w.Turnout_Percentage, 0) / winners.length).toFixed(1),
  totalDistricts: districtStats.length,
  totalParties: new Set(allCandidates.filter(c => c.Party !== 'NOTA' && c.Party !== 'IND').map(c => c.Party)).size,
}

// Alliance stats
export const allianceStats = (() => {
  const dmkPlus = { name: 'DMK+ Alliance', seats: 0, votes: 0, parties: {} }
  const admkPlus = { name: 'ADMK+ Alliance', seats: 0, votes: 0, parties: {} }
  const others = { name: 'Others', seats: 0, votes: 0, parties: {} }

  winners.forEach(w => {
    if (DMK_ALLIANCE.includes(w.Party)) {
      dmkPlus.seats++
      dmkPlus.parties[w.Party] = (dmkPlus.parties[w.Party] || 0) + 1
    } else if (ADMK_ALLIANCE.includes(w.Party)) {
      admkPlus.seats++
      admkPlus.parties[w.Party] = (admkPlus.parties[w.Party] || 0) + 1
    } else {
      others.seats++
      others.parties[w.Party] = (others.parties[w.Party] || 0) + 1
    }
  })

  allCandidates.forEach(c => {
    if (c.Party === 'NOTA') return
    if (DMK_ALLIANCE.includes(c.Party)) dmkPlus.votes += c.Votes
    else if (ADMK_ALLIANCE.includes(c.Party)) admkPlus.votes += c.Votes
    else others.votes += c.Votes
  })

  return [dmkPlus, admkPlus, others]
})()

// Demographics
export const demographics = {
  genderAll: (() => {
    const counts = { M: 0, F: 0 }
    allCandidates.forEach(c => { if (c.Sex === 'M' || c.Sex === 'F') counts[c.Sex]++ })
    return [{ name: 'Male', value: counts.M }, { name: 'Female', value: counts.F }]
  })(),
  genderWinners: (() => {
    const counts = { M: 0, F: 0 }
    winners.forEach(w => { if (w.Sex === 'M' || w.Sex === 'F') counts[w.Sex]++ })
    return [{ name: 'Male', value: counts.M }, { name: 'Female', value: counts.F }]
  })(),
  ageDistribution: (() => {
    const bins = { '25-35': 0, '36-45': 0, '46-55': 0, '56-65': 0, '66-75': 0, '76+': 0 }
    winners.forEach(w => {
      if (w.Age <= 35) bins['25-35']++
      else if (w.Age <= 45) bins['36-45']++
      else if (w.Age <= 55) bins['46-55']++
      else if (w.Age <= 65) bins['56-65']++
      else if (w.Age <= 75) bins['66-75']++
      else bins['76+']++
    })
    return Object.entries(bins).map(([name, value]) => ({ name, value }))
  })(),
  education: (() => {
    const map = {}
    winners.forEach(w => {
      const edu = w.MyNeta_education || 'Unknown'
      map[edu] = (map[edu] || 0) + 1
    })
    return Object.entries(map).sort((a, b) => b[1] - a[1]).map(([name, value]) => ({ name, value }))
  })(),
  profession: (() => {
    const map = {}
    winners.forEach(w => {
      const prof = w.TCPD_Prof_Main || 'Unknown'
      map[prof] = (map[prof] || 0) + 1
    })
    return Object.entries(map).sort((a, b) => b[1] - a[1]).map(([name, value]) => ({ name, value }))
  })(),
}
