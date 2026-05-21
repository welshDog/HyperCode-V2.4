// app/dashboard/page.tsx
// Main dashboard hub with all 5 new features

'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

// Import all upgrade components
import { AgentMonitor } from '@/components/dashboard/AgentMonitor';
import { HyperCodeIDE } from '@/components/dashboard/HyperCodeIDE';
import { MissionTimeline } from '@/components/dashboard/MissionTimeline';
import { DockerZone } from '@/components/dashboard/DockerZone';
import { MCPToolBrowser } from '@/components/dashboard/MCPToolBrowser';

const DASHBOARD_SECTIONS = [
  {
    id: 'agents',
    label: '🤖 Agents',
    description: 'Live 25-agent monitoring',
    icon: '🤖',
  },
  {
    id: 'code-ide',
    label: '💻 Code IDE',
    description: 'Execute HyperCode in real-time',
    icon: '💻',
  },
  {
    id: 'timeline',
    label: '📊 Timeline',
    description: 'Mission task visualization',
    icon: '📊',
  },
  {
    id: 'docker',
    label: '🐳 Docker Zone',
    description: 'Container management',
    icon: '🐳',
  },
  {
    id: 'mcp',
    label: '🔌 MCP Tools',
    description: 'Tool browser & tester',
    icon: '🔌',
  },
];

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState('agents');

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50">
      {/* Header */}
      <div className="border-b bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-6 py-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            🚀 HyperCode Dashboard v2.0
          </h1>
          <p className="text-gray-600">
            Real-time monitoring, code execution, and system control
          </p>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-2 md:grid-cols-5 bg-white shadow-sm rounded-lg">
            {DASHBOARD_SECTIONS.map((section) => (
              <TabsTrigger key={section.id} value={section.id} className="text-xs md:text-sm">
                <span className="hidden sm:inline">{section.icon}</span>
                <span className="sm:hidden">{section.label.split(' ')[0]}</span>
              </TabsTrigger>
            ))}
          </TabsList>

          {/* Tab Contents */}
          <div className="mt-8">
            {/* Agents Tab */}
            <TabsContent value="agents" className="space-y-4">
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-2xl font-bold mb-2 flex items-center gap-2">
                  <span>🤖</span> Live Agent Monitor
                </h2>
                <p className="text-gray-600 mb-6">
                  Real-time status of all 25 agents. Updates via WebSocket streaming.
                </p>
                <AgentMonitor />
              </div>
            </TabsContent>

            {/* Code IDE Tab */}
            <TabsContent value="code-ide" className="space-y-4">
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-2xl font-bold mb-2 flex items-center gap-2">
                  <span>💻</span> HyperCode IDE
                </h2>
                <p className="text-gray-600 mb-6">
                  Write and execute HyperCode directly from your dashboard. Real-time output streaming.
                </p>
                <HyperCodeIDE />
              </div>
            </TabsContent>

            {/* Timeline Tab */}
            <TabsContent value="timeline" className="space-y-4">
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-2xl font-bold mb-2 flex items-center gap-2">
                  <span>📊</span> Mission Timeline
                </h2>
                <p className="text-gray-600 mb-6">
                  Visualize all tasks, their status, agents, and execution duration. Updates every 5 seconds.
                </p>
                <MissionTimeline />
              </div>
            </TabsContent>

            {/* Docker Zone Tab */}
            <TabsContent value="docker" className="space-y-4">
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-2xl font-bold mb-2 flex items-center gap-2">
                  <span>🐳</span> Docker Zone
                </h2>
                <p className="text-gray-600 mb-6">
                  Manage all 37 containers from the UI. Stop, restart, and view logs without the CLI.
                </p>
                <DockerZone />
              </div>
            </TabsContent>

            {/* MCP Tools Tab */}
            <TabsContent value="mcp" className="space-y-4">
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-2xl font-bold mb-2 flex items-center gap-2">
                  <span>🔌</span> MCP Tool Browser
                </h2>
                <p className="text-gray-600 mb-6">
                  Browse all available MCP tools, test them, and see call history.
                </p>
                <MCPToolBrowser />
              </div>
            </TabsContent>
          </div>
        </Tabs>

        {/* Feature Cards */}
        <div className="mt-12 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          {DASHBOARD_SECTIONS.map((section) => (
            <Card
              key={section.id}
              className="cursor-pointer hover:shadow-lg transition-shadow"
              onClick={() => setActiveTab(section.id)}
            >
              <CardContent className="pt-6">
                <div className="text-3xl mb-2">{section.icon}</div>
                <h3 className="font-semibold text-sm">{section.label}</h3>
                <p className="text-xs text-gray-600 mt-1">{section.description}</p>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Stats Footer */}
        <div className="mt-12 bg-white rounded-lg shadow p-6">
          <h3 className="font-semibold text-lg mb-4">System Overview</h3>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="pt-6 text-center">
                <div className="text-3xl font-bold text-green-600">25</div>
                <p className="text-sm text-gray-600 mt-2">AI Agents</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6 text-center">
                <div className="text-3xl font-bold text-blue-600">37</div>
                <p className="text-sm text-gray-600 mt-2">Containers</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6 text-center">
                <div className="text-3xl font-bold text-purple-600">8</div>
                <p className="text-sm text-gray-600 mt-2">Infrastructure Services</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6 text-center">
                <div className="text-3xl font-bold text-orange-600">24h</div>
                <p className="text-sm text-gray-600 mt-2">Uptime</p>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
