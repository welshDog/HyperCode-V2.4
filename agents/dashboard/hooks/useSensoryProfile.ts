'use client'

import { useState } from 'react'

type SensoryProfile = 'CALM' | 'FOCUS' | 'ENERGISE'

const STORAGE_KEY = 'hyperstation_sensory_profile'

export function useSensoryProfile() {
  const [profile, setProfile] = useState<SensoryProfile>(() => {
    if (typeof window === 'undefined') return 'CALM'
    const saved = localStorage.getItem(STORAGE_KEY) as SensoryProfile | null
    return saved && ['CALM', 'FOCUS', 'ENERGISE'].includes(saved) ? saved : 'CALM'
  })

  const switchProfile = (newProfile: SensoryProfile) => {
    setProfile(newProfile)
    localStorage.setItem(STORAGE_KEY, newProfile)
    fetch('/api/user/sensory-profile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ profile: newProfile })
    }).catch(() => {})
  }

  return { profile, switchProfile }
}
