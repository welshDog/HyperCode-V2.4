import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Send, Radio, Terminal } from 'lucide-react';

import { formatTime } from '@/lib/format';
import { hypersyncHandoff, hypersyncRedeem } from '@/lib/api';

// FIX #1: type field must be 'execute' | 'ping' — crew-orchestrator /ws/uplink
// does NOT handle 'command'. Was broken since initial implementation.
interface UplinkMessage {
  id: string;
  timestamp: string;
  type: 'execute' | 'ping';  // ← was 'command', caused "Unknown message type" on every send
  source: string;
  target: string;
  payload: unknown;
  metadata?: unknown;
}

interface MessageUI {
  role: 'user' | 'system' | 'agent';
  content: string;
  timestamp: number;
}

export default function CognitiveUplink() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<MessageUI[]>(() => [
    { role: 'system', content: 'Neural interface ready. Establishing uplink...', timestamp: Date.now() },
  ]);
  const [isConnected, setIsConnected] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [syncStatus, setSyncStatus] = useState<'idle' | 'syncing' | 'complete' | 'error'>('idle');
  const [resumeToken, setResumeToken] = useState<string | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const getClientId = useCallback(() => {
    if (typeof window === 'undefined') return 'server';
    const key = 'hyperstation_client_id';
    const existing = localStorage.getItem(key);
    if (existing) return existing;
    const created = crypto.randomUUID();
    localStorage.setItem(key, created);
    return created;
  }, []);

  const getUserPreferences = useCallback(() => {
    if (typeof window === 'undefined') return {};
    const sensoryProfile = localStorage.getItem('hyperstation_sensory_profile');
    return { sensory_profile: sensoryProfile || 'CALM' };
  }, []);

  const currentSizeChars = useCallback((msgs: MessageUI[]) => {
    return msgs.reduce((acc, m) => acc + (m.content?.length || 0), 0);
  }, []);

  const triggerHyperSync = useCallback(async (reason: string) => {
    if (syncStatus === 'syncing' || syncStatus === 'complete') return;
    setSyncStatus('syncing');
    setSyncError(null);
    try {
      const clientId = getClientId();
      const safeReason = reason.replace(/[^a-zA-Z0-9]/g, '').slice(0, 32) || 'sync';
      const idempotencyKey = `uplink${Date.now()}${safeReason}`;

      const wait = (ms: number) => new Promise<void>(resolve => setTimeout(resolve, ms));
      const maxAttempts = 3;
      let lastError: unknown = null;

      for (let attempt = 1; attempt <= maxAttempts; attempt++) {
        try {
          const response = await hypersyncHandoff({
            client_id: clientId,
            messages: messages.map(m => ({ role: m.role, content: m.content, timestamp: m.timestamp })),
            context_variables: { uplink_reason: reason, attempt },
            file_references: [],
            user_preferences: getUserPreferences(),
            session_meta: { source: 'CognitiveUplink', size_chars: currentSizeChars(messages) }
          }, `${idempotencyKey}${attempt}`);

          setResumeToken(response.resume_token);
          setSyncStatus('complete');
          setMessages(prev => [...prev, {
            role: 'system',
            content: 'Sync complete—continue here.',
            timestamp: Date.now()
          }]);
          return;
        } catch (err) {
          lastError = err;
          if (attempt < maxAttempts) {
            const delayMs = 500 * Math.pow(2, attempt - 1);
            await wait(delayMs);
            continue;
          }
        }
      }

      const msg = lastError instanceof Error ? lastError.message : String(lastError);
      setSyncStatus('error');
      setSyncError(`HyperSync failed after ${maxAttempts} attempts. ${msg ? `Reason: ${msg}` : ''}`);
      setMessages(prev => [...prev, {
        role: 'system',
        content: 'Sync failed. Use Retry, or keep going (context may degrade).',
        timestamp: Date.now()
      }]);
    } catch (e) {
      setSyncStatus('error');
      const msg = e instanceof Error ? e.message : String(e);
      setSyncError(`HyperSync failed. ${msg ? `Reason: ${msg}` : ''}`);
      setMessages(prev => [...prev, {
        role: 'system',
        content: 'Sync failed. Use Retry, or keep going (context may degrade).',
        timestamp: Date.now()
      }]);
    }
  }, [currentSizeChars, getClientId, getUserPreferences, messages, syncStatus]);

  const connect = useCallback(() => {
    if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
      return;
    }

    const hostname = typeof window !== 'undefined' ? window.location.hostname : 'localhost';
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL ?? `ws://${hostname}:8081/ws/uplink`;

    console.log(`[CognitiveUplink] Connecting to ${wsUrl}...`);
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('[CognitiveUplink] Connected');
      setIsConnected(true);
      setMessages(prev => [...prev, {
        role: 'system',
        content: 'SECURE CHANNEL ESTABLISHED. NEURAL NET ONLINE.',
        timestamp: Date.now()
      }]);
    };

    ws.onerror = (error) => {
      console.error('[CognitiveUplink] WebSocket Error:', error);
    };

    ws.onclose = () => {
      console.log('[CognitiveUplink] Disconnected');
      setIsConnected(false);
    };

    ws.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'response' || data.type === 'result') {
          setMessages(prev => [...prev, {
            role: 'agent',
            content: typeof data.payload === 'string' ? data.payload : JSON.stringify(data.payload, null, 2),
            timestamp: Date.now()
          }]);
          setIsTyping(false);
        } else if (data.type === 'error') {
          setMessages(prev => [...prev, {
            role: 'system',
            content: `Error: ${data.data ?? 'Unknown error'}`,
            timestamp: Date.now()
          }]);
          setIsTyping(false);
        }
      } catch (e) {
        console.error('Failed to parse message', e);
      }
    };

    wsRef.current = ws;
  }, []);

  useEffect(() => {
    if (!wsRef.current || wsRef.current.readyState === WebSocket.CLOSED) {
      connect();
    }

    const interval = setInterval(() => {
      if (!wsRef.current || wsRef.current.readyState === WebSocket.CLOSED) {
        console.log('[CognitiveUplink] Reconnecting...');
        connect();
      }
    }, 5000);

    return () => {
      clearInterval(interval);
    };
  }, [connect]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const params = new URLSearchParams(window.location.search);
    const resume = params.get('resume');
    if (!resume) return;
    (async () => {
      try {
        const clientId = getClientId();
        const redeemed = await hypersyncRedeem(resume, clientId);
        const state = redeemed.state as any;
        const restored = Array.isArray(state.messages) ? state.messages : [];
        setMessages([
          { role: 'system', content: 'Resumed from HyperSync handoff.', timestamp: Date.now() },
          ...restored.map((m: any) => ({
            role: (m.role === 'user' || m.role === 'system' || m.role === 'agent') ? m.role : 'system',
            content: String(m.content ?? ''),
            timestamp: Number(m.timestamp ?? Date.now()),
          }))
        ]);
        setSyncStatus('idle');
        setResumeToken(null);
        const url = new URL(window.location.href);
        url.searchParams.delete('resume');
        window.history.replaceState({}, '', url.toString());
      } catch (e) {
        setMessages(prev => [...prev, { role: 'system', content: `Resume failed: ${String(e)}`, timestamp: Date.now() }]);
      }
    })();
  }, [getClientId]);

  useEffect(() => {
    const MAX_CHARS = 12000;
    const size = currentSizeChars(messages);
    if (size >= MAX_CHARS) {
      triggerHyperSync('size_threshold');
    }
  }, [currentSizeChars, messages, triggerHyperSync]);

  const handleSend = () => {
    if (!input.trim() || !isConnected) return;

    const content = input;
    setInput('');

    setMessages(prev => [...prev, { role: 'user', content: content, timestamp: Date.now() }]);
    setIsTyping(true);

    // FIX #1 APPLIED: type is now 'execute' — matches crew-orchestrator WS handler
    const message: UplinkMessage = {
      id: crypto.randomUUID(),
      timestamp: new Date().toISOString(),
      type: 'execute',  // ← THE FIX. Was 'command'. Orchestrator lines 796–866.
      source: 'user',
      target: 'orchestrator',
      payload: { command: content }
    };

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      setMessages(prev => [...prev, { role: 'system', content: 'Error: Uplink offline.', timestamp: Date.now() }]);
      setIsTyping(false);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center h-full w-full p-8 text-cyan-500">
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className="max-w-2xl w-full bg-black/40 border border-cyan-500/30 p-8 rounded-lg backdrop-blur-xl relative overflow-hidden"
      >
        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-cyan-500 to-transparent opacity-50" />

        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded border border-cyan-500/30 transition-colors ${isConnected ? 'bg-cyan-900/20' : 'bg-red-900/20'}`}>
              <Radio className={isConnected ? 'animate-pulse text-cyan-500' : 'text-red-500'} size={24} />
            </div>
            <div>
              <h2 className="text-xl font-bold tracking-[0.2em]">COGNITIVE UPLINK</h2>
              <div className={`text-[10px] font-mono ${isConnected ? 'text-cyan-700' : 'text-red-700'}`}>
                {isConnected ? 'SECURE CHANNEL ESTABLISHED' : 'SEARCHING FOR CARRIER...'}
              </div>
            </div>
          </div>
          <div className="text-right font-mono text-xs">
            <div className={isConnected ? 'text-emerald-500' : 'text-red-500'}>
              SIGNAL: {isConnected ? 'STRONG' : 'LOST'}
            </div>
            <div className="text-cyan-700">LATENCY: {isConnected ? '12ms' : '--'}</div>
          </div>
        </div>
        <div className="space-y-6">
          {syncStatus === 'syncing' && (
            <div className="border border-cyan-500/30 bg-cyan-900/10 text-cyan-300 font-mono text-xs p-3 rounded">
              Syncing session state…
            </div>
          )}
          {syncStatus === 'complete' && resumeToken && (
            <div className="border border-emerald-500/30 bg-emerald-900/10 text-emerald-300 font-mono text-xs p-3 rounded flex items-center justify-between gap-3">
              <div>Sync complete—continue here</div>
              <button
                type="button"
                onClick={() => {
                  const url = new URL(window.location.href);
                  url.searchParams.set('resume', resumeToken);
                  window.open(url.toString(), '_blank', 'noopener,noreferrer');
                }}
                className="px-3 py-1 border border-emerald-500/40 hover:bg-emerald-500 hover:text-black transition-colors"
              >
                Open new chat
              </button>
            </div>
          )}
          {syncStatus === 'error' && syncError && (
            <div className="border border-red-500/30 bg-red-900/10 text-red-300 font-mono text-xs p-3 rounded flex items-center justify-between gap-3">
              <div className="break-words">{syncError}</div>
              <button
                type="button"
                onClick={() => triggerHyperSync('manual_retry')}
                className="px-3 py-1 border border-red-500/40 hover:bg-red-500 hover:text-black transition-colors"
              >
                Retry
              </button>
            </div>
          )}
          <div
            ref={scrollRef}
            className="h-64 border border-cyan-900/30 bg-black/50 rounded p-4 font-mono text-sm text-cyan-300/80 overflow-y-auto scrollbar-thin scrollbar-thumb-cyan-900/50"
          >
            {messages.map((msg, i) => (
              <div key={i} className={`mb-2 ${msg.role === 'user' ? 'text-right' : 'text-left'}`}>
                <span className={`text-[10px] uppercase ${msg.role === 'user' ? 'text-emerald-700' : 'text-cyan-700'} block mb-1`}>
                  [{formatTime(msg.timestamp)}] {msg.role === 'user' ? 'OPERATOR' : msg.role === 'agent' ? 'SWARM' : 'SYSTEM'}
                </span>
                <div className={`${msg.role === 'user' ? 'text-emerald-400' : msg.role === 'system' ? 'text-zinc-500 italic' : 'text-cyan-300'}`}>
                  {msg.role === 'system' && '// '}
                  {msg.content}
                </div>
              </div>
            ))}
            {isTyping && (
              <div className="text-left animate-pulse">
                <span className="text-[10px] text-cyan-700 block mb-1">SWARM</span>
                <div className="flex gap-1 items-center h-4">
                  <div className="w-1 h-1 bg-cyan-500 rounded-full" />
                  <div className="w-1 h-1 bg-cyan-500 rounded-full animation-delay-200" />
                  <div className="w-1 h-1 bg-cyan-500 rounded-full animation-delay-400" />
                </div>
              </div>
            )}
          </div>

          <form
            onSubmit={(e) => { e.preventDefault(); handleSend(); }}
            className="flex gap-2"
          >
            <div className="flex items-center justify-center w-10 bg-zinc-900 border border-zinc-700 text-cyan-500">
              <Terminal size={18} />
            </div>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={isConnected ? "Enter directive (e.g., 'run: build a spaceship UI')..." : 'Connecting...'}
              disabled={!isConnected}
              className="flex-1 bg-transparent border-b border-zinc-700 text-cyan-400 font-mono focus:outline-none focus:border-cyan-500 transition-colors placeholder:text-zinc-700 disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={!isConnected}
              className="px-6 bg-cyan-900/20 border border-cyan-800 text-cyan-400 hover:bg-cyan-500 hover:text-black transition-all font-bold uppercase text-xs tracking-wider flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Execute <Send size={14} />
            </button>
          </form>
        </div>
      </motion.div>
    </div>
  );
}
