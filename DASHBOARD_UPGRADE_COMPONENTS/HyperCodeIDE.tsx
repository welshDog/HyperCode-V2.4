'use client';

import { useEffect, useState, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export function HyperCodeIDE() {
  const [code, setCode] = useState('# Start coding here\nprint("Hello HyperCode!")');
  const [output, setOutput] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const editorRef = useRef<HTMLTextAreaElement>(null);

  const handleRun = async () => {
    setIsRunning(true);
    setError(null);
    setOutput('');

    try {
      const response = await fetch('http://hypercode-core:8000/execution/execute-hc', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': process.env.NEXT_PUBLIC_API_KEY || 'dev',
        },
        body: JSON.stringify({ source: code, timeout: 30 }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();

      if (result.success) {
        setOutput(result.stdout || '(no output)');
      } else {
        setError(result.stderr || 'Execution failed');
      }
    } catch (err) {
      setError(`Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setIsRunning(false);
    }
  };

  const handleClear = () => {
    setCode('');
    setOutput('');
    setError(null);
  };

  const handleExample = () => {
    setCode(`# Example: FizzBuzz
for i in range(1, 21):
    if i % 15 == 0:
        print("FizzBuzz")
    elif i % 3 == 0:
        print("Fizz")
    elif i % 5 == 0:
        print("Buzz")
    else:
        print(i)`);
  };

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Code Editor</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <textarea
            ref={editorRef}
            value={code}
            onChange={(e) => setCode(e.target.value)}
            className="h-96 w-full rounded-lg border border-gray-300 bg-gray-50 p-3 font-mono text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            placeholder="# Enter HyperCode here..."
            spellCheck="false"
          />
          <div className="flex gap-2">
            <Button
              onClick={handleRun}
              disabled={isRunning}
              className="flex-1 bg-green-600 hover:bg-green-700"
            >
              {isRunning ? 'Running...' : '▶ Run Code'}
            </Button>
            <Button
              onClick={handleExample}
              variant="outline"
              className="flex-1"
            >
              📝 Example
            </Button>
            <Button
              onClick={handleClear}
              variant="outline"
              className="flex-1"
            >
              🗑️ Clear
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Output</CardTitle>
        </CardHeader>
        <CardContent>
          {error ? (
            <div className="h-96 rounded-lg border border-red-300 bg-red-50 p-3 font-mono text-sm text-red-800 overflow-auto">
              {error}
            </div>
          ) : (
            <div className="h-96 rounded-lg border border-gray-300 bg-gray-900 p-3 font-mono text-sm text-green-400 overflow-auto whitespace-pre-wrap">
              {output || '(waiting for output...)'}
            </div>
          )}
          <div className="mt-3 text-xs text-gray-500">
            {isRunning && <p>⏳ Executing...</p>}
            {!isRunning && output && <p>✅ Execution complete</p>}
            {!isRunning && error && <p>🔴 Execution failed</p>}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
