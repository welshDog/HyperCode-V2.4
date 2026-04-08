// 💰 BROski$ Wallet Hook — polls /api/wallet/broski/{userId} every 10s

import { useEffect, useState } from 'react';

interface Achievement {
  name: string;
  date: string;
  icon: string;
}

interface Wallet {
  balance: number;
  level: number;
  xp: number;
  achievements: Achievement[];
}

export function useWallet(userId: string) {
  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchWallet = async () => {
      try {
        const res = await fetch(`/api/wallet/broski/${userId}`);
        if (!res.ok) throw new Error(`Wallet fetch failed: ${res.status}`);
        const data = await res.json();
        setWallet(data);
        setError(null);
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    };

    fetchWallet();
    const interval = setInterval(fetchWallet, 10000);
    return () => clearInterval(interval);
  }, [userId]);

  return { wallet, loading, error };
}
