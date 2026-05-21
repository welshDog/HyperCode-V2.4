'use client';

import { useEffect, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface Agent {
  id: string;
  name: string;
  status: 'healthy' | 'busy' | 'error' | 'offline';
  latency: number;
  taskCount: number;
  memory: number;
  cpu: number;
  port: number;
  uptime: number;
}

export function AgentMonitor() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const eventSource = new EventSource('http://hypercode-core:8000/agents/stream');
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setAgents(data.agents || []);
        setLoading(false);
      } catch (err) {
        console.error('Failed to parse agent data:', err);
      }
    };

    eventSource.onerror = (error) => {
      setError('Failed to connect to agent stream');
      console.error('EventSource error:', error);
    };

    return () => eventSource.close();
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'bg-green-100 text-green-800';
      case 'busy':
        return 'bg-yellow-100 text-yellow-800';
      case 'error':
        return 'bg-red-100 text-red-800';
      case 'offline':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-gray-500">Loading agent data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4">
        <p className="text-red-800">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {agents.map((agent) => (
          <Card key={agent.id} className="hover:shadow-lg transition-shadow">
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between">
                <CardTitle className="text-base">{agent.name}</CardTitle>
                <Badge className={getStatusColor(agent.status)}>
                  {agent.status}
                </Badge>
              </div>
              <p className="text-xs text-gray-500">Port {agent.port}</p>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Latency:</span>
                <span className="font-mono font-semibold">{agent.latency}ms</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Tasks:</span>
                <span className="font-mono font-semibold">{agent.taskCount}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Memory:</span>
                <span className="font-mono font-semibold">{agent.memory}MB</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">CPU:</span>
                <span className="font-mono font-semibold">{agent.cpu}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Uptime:</span>
                <span className="font-mono font-semibold text-green-600">
                  {Math.floor(agent.uptime / 3600)}h
                </span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
      {agents.length === 0 && (
        <div className="flex items-center justify-center py-12">
          <p className="text-gray-500">No agents online</p>
        </div>
      )}
      <div className="rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800">
        <p>🟢 {agents.filter(a => a.status === 'healthy').length} healthy • 🟡 {agents.filter(a => a.status === 'busy').length} busy • 🔴 {agents.filter(a => a.status === 'error').length} errors</p>
      </div>
    </div>
  );
}
