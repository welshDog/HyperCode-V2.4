'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface Task {
  id: string;
  agent: string;
  description: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  startedAt: number;
  completedAt?: number;
  duration?: number;
}

export function MissionTimeline() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTasks = async () => {
      try {
        const response = await fetch('http://hypercode-core:8000/missions/tasks');
        if (response.ok) {
          const data = await response.json();
          setTasks(data.tasks || []);
        }
      } catch (err) {
        console.error('Failed to fetch tasks:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchTasks();
    const interval = setInterval(fetchTasks, 5000); // Refresh every 5s
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-500';
      case 'running':
        return 'bg-blue-500';
      case 'failed':
        return 'bg-red-500';
      case 'pending':
        return 'bg-gray-400';
      default:
        return 'bg-gray-400';
    }
  };

  const formatDuration = (ms?: number) => {
    if (!ms) return '--';
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-gray-500">Loading timeline...</p>
      </div>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Mission Timeline</CardTitle>
        <p className="text-sm text-gray-500">
          {tasks.length} tasks • {tasks.filter(t => t.status === 'completed').length} completed
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        {tasks.map((task, index) => (
          <div key={task.id} className="flex items-center gap-4">
            <div className="flex-shrink-0 w-16 text-xs font-mono text-gray-600">
              #{index + 1}
            </div>
            <div className={`h-8 rounded flex items-center px-3 text-white text-xs font-semibold ${getStatusColor(task.status)}`}>
              {task.status.toUpperCase()}
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium">{task.description}</p>
              <p className="text-xs text-gray-500">{task.agent}</p>
            </div>
            <div className="text-right">
              <p className="text-sm font-mono font-semibold">
                {formatDuration(task.duration)}
              </p>
              <p className="text-xs text-gray-500">
                {new Date(task.startedAt).toLocaleTimeString()}
              </p>
            </div>
          </div>
        ))}
        {tasks.length === 0 && (
          <div className="flex items-center justify-center py-8">
            <p className="text-gray-500">No tasks yet</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
