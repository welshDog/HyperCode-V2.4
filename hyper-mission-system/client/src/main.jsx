import React, { useState, useEffect } from 'react';
import { createRoot } from 'react-dom/client';
import { CheckCircle, AlertCircle, Clock, BarChart2 } from 'lucide-react';
import './index.css';

const API_URL = import.meta.env.VITE_API_URL || '/api';
const TOKEN_KEY = 'hyper_mission_token';

const App = () => {
  const [tasks, setTasks] = useState([]);
  const [dashboard, setDashboard] = useState(null);
  const [selectedTask, setSelectedTask] = useState(null);
  const [evidence, setEvidence] = useState('');
  const [peerReviewed, setPeerReviewed] = useState(false);
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY) || '');
  const [loginUsername, setLoginUsername] = useState('admin@hypercode.ai');
  const [loginPassword, setLoginPassword] = useState('adminpassword');
  const [loginError, setLoginError] = useState('');

  useEffect(() => {
    if (!token) return;
    fetchTasks();
    fetchDashboard();
  }, [token]);

  const apiFetch = async (path, options = {}) => {
    const headers = new Headers(options.headers || {});
    if (token) headers.set('Authorization', `Bearer ${token}`);
    const res = await fetch(`${API_URL}${path}`, { ...options, headers });
    if (res.status === 401 || res.status === 403) {
      localStorage.removeItem(TOKEN_KEY);
      setToken('');
      throw new Error('Unauthorized');
    }
    return res;
  };

  const fetchTasks = async () => {
    const res = await apiFetch('/tasks');
    const data = await res.json();
    setTasks(data);
  };

  const fetchDashboard = async () => {
    const res = await apiFetch('/dashboard');
    const data = await res.json();
    setDashboard(data);
  };

  const handleMarkDone = async () => {
    if (!selectedTask) return;
    try {
      const res = await apiFetch(`/tasks/${selectedTask.id}/done`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ evidence_link: evidence, peer_review_checked: peerReviewed })
      });
      if (res.ok) {
        setSelectedTask(null);
        fetchTasks();
        fetchDashboard();
        alert('Task completed!');
      } else {
        const err = await res.json();
        alert(err.error);
      }
    } catch (e) {
      alert('Error marking done');
    }
  };

  const handleLogin = async () => {
    setLoginError('');
    try {
      const res = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: loginUsername, password: loginPassword })
      });
      const data = await res.json();
      if (!res.ok) {
        setLoginError(data?.error || 'Login failed');
        return;
      }
      localStorage.setItem(TOKEN_KEY, data.token);
      setToken(data.token);
    } catch (e) {
      setLoginError('Login failed');
    }
  };

  if (!token) {
    return (
      <div className="min-h-screen bg-gray-900 text-white p-8 font-mono flex items-center justify-center">
        <div className="w-full max-w-md bg-gray-800 p-6 rounded-lg border border-gray-700">
          <h1 className="text-2xl font-bold text-green-400 mb-6">HYPER-MISSION CONTROL</h1>
          <label className="block text-sm mb-1">Email</label>
          <input
            className="w-full bg-gray-900 border border-gray-600 rounded p-2 mb-4"
            value={loginUsername}
            onChange={e => setLoginUsername(e.target.value)}
            placeholder="admin@hypercode.ai"
          />
          <label className="block text-sm mb-1">Password</label>
          <input
            type="password"
            className="w-full bg-gray-900 border border-gray-600 rounded p-2 mb-4"
            value={loginPassword}
            onChange={e => setLoginPassword(e.target.value)}
            placeholder="adminpassword"
          />
          {loginError && <div className="text-red-300 text-sm mb-3">{loginError}</div>}
          <button
            onClick={handleLogin}
            className="w-full py-2 bg-green-600 hover:bg-green-700 rounded font-bold"
          >
            SIGN IN
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8 font-mono">
      <header className="mb-8 flex justify-between items-center border-b border-green-500 pb-4">
        <h1 className="text-3xl font-bold text-green-400">HYPER-MISSION CONTROL</h1>
        {dashboard && (
          <div className="flex gap-4 text-sm">
            <span className="flex items-center gap-2"><BarChart2 size={16}/> {dashboard.percent_complete.toFixed(0)}% Complete</span>
            <span className="flex items-center gap-2"><Clock size={16}/> Velocity: {dashboard.velocity_trend}</span>
          </div>
        )}
      </header>

      <main className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {/* Task List */}
        <div className="md:col-span-2 space-y-4">
          <h2 className="text-xl text-blue-400 mb-4">Mission Matrix (Sorted by Impact/Effort)</h2>
          {tasks.map(task => (
            <div key={task.id} className={`p-4 border rounded-lg flex justify-between items-center ${task.status === 'completed' ? 'border-gray-700 opacity-50' : 'border-green-800 bg-gray-800'}`}>
              <div>
                <h3 className="font-bold text-lg">{task.title}</h3>
                <p className="text-gray-400 text-sm">{task.description}</p>
                <div className="flex gap-2 mt-2 text-xs">
                  <span className={`px-2 py-1 rounded ${task.urgency === 'critical' ? 'bg-red-900 text-red-200' : 'bg-blue-900'}`}>{task.urgency.toUpperCase()}</span>
                  <span className="px-2 py-1 bg-gray-700 rounded">Impact: {task.impact}</span>
                  <span className="px-2 py-1 bg-gray-700 rounded">Effort: {task.effort}</span>
                </div>
              </div>
              {task.status !== 'completed' && (
                <button 
                  onClick={() => setSelectedTask(task)}
                  className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded text-sm font-bold"
                >
                  COMPLETE
                </button>
              )}
            </div>
          ))}
        </div>

        {/* Sidebar / Validator */}
        <div className="bg-gray-800 p-6 rounded-lg border border-gray-700 h-fit">
          <h2 className="text-xl text-yellow-400 mb-4">Done Validator</h2>
          {selectedTask ? (
            <div className="space-y-4">
              <div className="p-4 bg-gray-900 rounded border border-gray-600">
                <h3 className="font-bold mb-2">{selectedTask.title}</h3>
                <p className="text-sm text-gray-400 mb-4">Verify completion criteria:</p>
                
                <label className="block text-sm mb-1">Evidence Link (PR/Doc)</label>
                <input 
                  className="w-full bg-gray-800 border border-gray-600 rounded p-2 mb-4"
                  value={evidence}
                  onChange={e => setEvidence(e.target.value)}
                  placeholder="https://github.com/..."
                />
                
                <label className="flex items-center gap-2 mb-4 cursor-pointer">
                  <input 
                    type="checkbox" 
                    checked={peerReviewed}
                    onChange={e => setPeerReviewed(e.target.checked)}
                    className="w-4 h-4"
                  />
                  <span className="text-sm">Peer Review & Acceptance Criteria Met</span>
                </label>

                <button 
                  onClick={handleMarkDone}
                  disabled={!evidence || !peerReviewed}
                  className="w-full py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded font-bold"
                >
                  CONFIRM DONE
                </button>
              </div>
            </div>
          ) : (
            <p className="text-gray-500 italic">Select a task to validate completion.</p>
          )}

          <div className="mt-8 border-t border-gray-700 pt-4">
            <h3 className="text-lg text-purple-400 mb-2">Daily Standup</h3>
            <button 
              onClick={async () => {
                const res = await apiFetch('/standup');
                const data = await res.json();
                alert(JSON.stringify(data, null, 2));
              }}
              className="w-full py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm"
            >
              Generate Report
            </button>
          </div>
        </div>
      </main>
    </div>
  );
};

const root = createRoot(document.getElementById('root'));
root.render(<App />);
