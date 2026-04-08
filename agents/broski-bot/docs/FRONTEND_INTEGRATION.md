# Frontend Integration Guide: Economy Dashboard

This guide explains how to integrate the BROski Bot Economy Dashboard into the HyperCode-V2.0 frontend.

## 1. Environment Configuration

Add the BROski Bot API URL to your `.env.local` file in `agents/dashboard`:

```bash
NEXT_PUBLIC_BROSKI_API_URL=http://localhost:8000
```

## 2. API Client Update

Update `lib/api.ts` to include the economy fetcher:

```typescript
// ... existing code ...

// --- BROski ECONOMY ---
export const BROSKI_API_URL = process.env.NEXT_PUBLIC_BROSKI_API_URL || "http://localhost:8000";

export interface EconomyBalance {
  user_id: number;
  balance: number;
}

export async function fetchEconomyBalance(userId: number): Promise<EconomyBalance | null> {
  try {
    const res = await fetch(`${BROSKI_API_URL}/economy/balance/${userId}`);
    if (!res.ok) throw new Error("Failed to fetch balance");
    return await res.json();
  } catch (error) {
    console.error("Economy API Error:", error);
    return null;
  }
}
```

## 3. Create Economy Panel Component

Create a new file `components/panels/EconomyPanel.tsx`:

```tsx
"use client";

import { useEffect, useState } from "react";
import { fetchEconomyBalance, EconomyBalance } from "@/lib/api";

export function EconomyPanel({ userId }: { userId: number }) {
  const [data, setData] = useState<EconomyBalance | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const balance = await fetchEconomyBalance(userId);
      setData(balance);
      setLoading(false);
    }
    load();
    // Poll every 30 seconds
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, [userId]);

  if (loading) return <div className="p-4 animate-pulse">Loading Economy...</div>;
  if (!data) return <div className="p-4 text-red-500">Failed to load economy data.</div>;

  return (
    <div className="bg-gray-800 rounded-lg p-6 shadow-lg border border-gray-700">
      <h2 className="text-xl font-bold text-white mb-4 flex items-center">
        <span className="text-2xl mr-2">💰</span> Wallet Balance
      </h2>
      <div className="flex items-end">
        <span className="text-4xl font-mono text-green-400 font-bold">
          {data.balance.toLocaleString()}
        </span>
        <span className="text-gray-400 ml-2 mb-1">BROski$</span>
      </div>
      <div className="mt-4 text-sm text-gray-500">
        User ID: {data.user_id}
      </div>
    </div>
  );
}
```

## 4. Add to Dashboard

Import and use the panel in your main page (e.g., `app/page.tsx`):

```tsx
import { EconomyPanel } from "@/components/panels/EconomyPanel";

export default function Dashboard() {
  // Replace with actual user ID from auth context
  const USER_ID = 1; 

  return (
    <main className="min-h-screen bg-black text-white p-8">
      <h1 className="text-3xl font-bold mb-8">HyperCode Dashboard</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Existing Panels */}
        
        {/* New Economy Panel */}
        <EconomyPanel userId={USER_ID} />
      </div>
    </main>
  );
}
```
