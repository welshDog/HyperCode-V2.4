// 🧠 Sensory Profile Hook — persists CALM/FOCUS/ENERGISE to localStorage

import { useState, useEffect } from 'react';

type SensoryProfile = 'CALM' | 'FOCUS' | 'ENERGISE';

const STORAGE_KEY = 'hyperstation_sensory_profile';

export function useSensoryProfile() {
  const [profile, setProfile] = useState<SensoryProfile>('CALM');

  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY) as SensoryProfile | null;
    if (saved && ['CALM', 'FOCUS', 'ENERGISE'].includes(saved)) {
      setProfile(saved);
    }
  }, []);

  const switchProfile = (newProfile: SensoryProfile) => {
    setProfile(newProfile);
    localStorage.setItem(STORAGE_KEY, newProfile);

    // Optional: sync to backend (non-blocking)
    fetch('/api/user/sensory-profile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ profile: newProfile })
    }).catch(() => {
      // Fail silently — localStorage is source of truth
    });
  };

  return { profile, switchProfile };
}
