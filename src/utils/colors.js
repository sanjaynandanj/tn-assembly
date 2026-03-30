export const PARTY_COLORS = {
  DMK: '#E3001B',
  ADMK: '#00A651',
  INC: '#19AAED',
  BJP: '#FF6B00',
  PMK: '#FFD700',
  VCK: '#8B0000',
  CPI: '#FF0000',
  CPM: '#CC0000',
  NTK: '#FFCC00',
  DMDK: '#FF69B4',
  MNM: '#00BCD4',
  AMMK: '#7B68EE',
  BSP: '#0000FF',
  NOTA: '#9CA3AF',
  IND: '#6B7280',
  Others: '#94A3B8',
}

export const getPartyColor = (party) => PARTY_COLORS[party] || PARTY_COLORS.Others

export const ALLIANCE_COLORS = {
  'DMK+': '#E3001B',
  'ADMK+': '#00A651',
  'Others': '#94A3B8',
}

export const DMK_ALLIANCE = ['DMK', 'INC', 'VCK', 'CPI', 'CPM', 'CPI(ML)(L)', 'MDMK', 'IUML']
export const ADMK_ALLIANCE = ['ADMK', 'PMK', 'BJP', 'TMC(M)']
