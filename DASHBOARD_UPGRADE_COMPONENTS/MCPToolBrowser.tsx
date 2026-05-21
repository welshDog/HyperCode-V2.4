'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface MCPTool {
  name: string;
  description: string;
  inputSchema: any;
  category: string;
}

interface ToolCall {
  tool: string;
  input: any;
  output: any;
  timestamp: number;
  duration: number;
}

export function MCPToolBrowser() {
  const [tools, setTools] = useState<MCPTool[]>([]);
  const [callHistory, setCallHistory] = useState<ToolCall[]>([]);
  const [selectedTool, setSelectedTool] = useState<MCPTool | null>(null);
  const [testInput, setTestInput] = useState('{}');
  const [loading, setLoading] = useState(true);
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    const fetchTools = async () => {
      try {
        const response = await fetch('http://hypercode-core:8000/mcp/tools');
        if (response.ok) {
          const data = await response.json();
          setTools(data.tools || []);
          if (data.tools && data.tools.length > 0) {
            setSelectedTool(data.tools[0]);
          }
        }
      } catch (err) {
        console.error('Failed to fetch tools:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchTools();
  }, []);

  const handleTestTool = async () => {
    if (!selectedTool) return;
    setTesting(true);

    try {
      const startTime = performance.now();
      const response = await fetch(`http://hypercode-core:8000/mcp/tools/${selectedTool.name}/call`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: testInput,
      });
      const duration = performance.now() - startTime;

      if (response.ok) {
        const output = await response.json();
        setCallHistory([
          {
            tool: selectedTool.name,
            input: JSON.parse(testInput),
            output,
            timestamp: Date.now(),
            duration: Math.round(duration),
          },
          ...callHistory,
        ]);
      }
    } catch (err) {
      console.error('Tool call failed:', err);
    } finally {
      setTesting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-gray-500">Loading MCP tools...</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
      <Card className="lg:col-span-1">
        <CardHeader>
          <CardTitle className="text-base">Available Tools</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {tools.map((tool) => (
            <button
              key={tool.name}
              onClick={() => setSelectedTool(tool)}
              className={`w-full text-left p-2 rounded text-sm transition-colors ${
                selectedTool?.name === tool.name
                  ? 'bg-blue-500 text-white'
                  : 'hover:bg-gray-100'
              }`}
            >
              <p className="font-semibold">{tool.name}</p>
              <p className="text-xs opacity-75 truncate">{tool.description}</p>
            </button>
          ))}
        </CardContent>
      </Card>

      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle className="text-base">Tool Tester</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {selectedTool ? (
            <>
              <div>
                <h3 className="font-semibold text-sm mb-2">{selectedTool.name}</h3>
                <p className="text-sm text-gray-600">{selectedTool.description}</p>
                <Badge className="mt-2">{selectedTool.category}</Badge>
              </div>

              <div>
                <label className="text-sm font-semibold block mb-2">Input (JSON)</label>
                <textarea
                  value={testInput}
                  onChange={(e) => setTestInput(e.target.value)}
                  className="w-full h-32 border rounded p-2 font-mono text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  placeholder="{}"
                />
              </div>

              <Button
                onClick={handleTestTool}
                disabled={testing}
                className="w-full bg-blue-600 hover:bg-blue-700"
              >
                {testing ? 'Testing...' : '🧪 Test Tool'}
              </Button>

              {callHistory.length > 0 && (
                <div className="border-t pt-4">
                  <h4 className="font-semibold text-sm mb-2">Call History</h4>
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {callHistory.map((call, index) => (
                      <div key={index} className="bg-gray-50 p-2 rounded text-xs">
                        <p className="font-mono text-gray-600">
                          {new Date(call.timestamp).toLocaleTimeString()} • {call.duration}ms
                        </p>
                        <p className="text-gray-700 truncate">
                          {JSON.stringify(call.output).slice(0, 100)}...
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : (
            <p className="text-gray-500">Select a tool to test</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
