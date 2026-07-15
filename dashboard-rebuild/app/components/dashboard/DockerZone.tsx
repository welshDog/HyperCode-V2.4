'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface Container {
  id: string;
  name: string;
  status: 'running' | 'stopped' | 'unhealthy';
  memory: string;
  cpu: string;
  ports: string;
  uptime: string;
}

export function DockerZone() {
  const [containers, setContainers] = useState<Container[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchContainers = async () => {
      try {
        const response = await fetch('http://hypercode-core:8000/docker/containers');
        if (response.ok) {
          const data = await response.json();
          setContainers(data.containers || []);
        }
      } catch (err) {
        console.error('Failed to fetch containers:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchContainers();
    const interval = setInterval(fetchContainers, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, []);

  const handleStop = async (containerId: string) => {
    try {
      await fetch(`http://hypercode-core:8000/docker/containers/${containerId}/stop`, {
        method: 'POST',
      });
      // Refresh list
      const response = await fetch('http://hypercode-core:8000/docker/containers');
      if (response.ok) {
        const data = await response.json();
        setContainers(data.containers || []);
      }
    } catch (err) {
      console.error('Failed to stop container:', err);
    }
  };

  const handleRestart = async (containerId: string) => {
    try {
      await fetch(`http://hypercode-core:8000/docker/containers/${containerId}/restart`, {
        method: 'POST',
      });
      // Refresh list
      const response = await fetch('http://hypercode-core:8000/docker/containers');
      if (response.ok) {
        const data = await response.json();
        setContainers(data.containers || []);
      }
    } catch (err) {
      console.error('Failed to restart container:', err);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'bg-green-100 text-green-800';
      case 'stopped':
        return 'bg-gray-100 text-gray-800';
      case 'unhealthy':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-gray-500">Loading containers...</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-4">
        {containers.map((container) => (
          <Card key={container.id}>
            <CardContent className="pt-6">
              <div className="grid grid-cols-1 gap-4 md:grid-cols-6 md:items-center">
                <div className="md:col-span-2">
                  <p className="font-semibold text-sm">{container.name}</p>
                  <p className="text-xs text-gray-500 font-mono">{container.id.slice(0, 12)}</p>
                </div>
                <Badge className={getStatusColor(container.status)}>
                  {container.status}
                </Badge>
                <div className="text-sm">
                  <p className="text-gray-600">Memory: <span className="font-mono font-semibold">{container.memory}</span></p>
                  <p className="text-gray-600">CPU: <span className="font-mono font-semibold">{container.cpu}</span></p>
                </div>
                <div className="text-sm">
                  <p className="text-gray-600 break-all">{container.ports}</p>
                </div>
                <div className="flex gap-2">
                  {container.status === 'running' && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleStop(container.id)}
                    >
                      Stop
                    </Button>
                  )}
                  {container.status !== 'running' && (
                    <Button
                      size="sm"
                      onClick={() => handleRestart(container.id)}
                    >
                      Start
                    </Button>
                  )}
                  <Button size="sm" variant="outline">
                    Logs
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
      {containers.length === 0 && (
        <div className="flex items-center justify-center py-12">
          <p className="text-gray-500">No containers found</p>
        </div>
      )}
      <div className="rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800">
        <p>🐳 {containers.filter(c => c.status === 'running').length}/{containers.length} containers running</p>
      </div>
    </div>
  );
}
