import React from 'react';
import { Navbar } from './components/Navbar';
import { LeftSidebar } from './components/LeftSidebar';
import { CodeEditor } from './components/CodeEditor';
import { Terminal } from './components/Terminal';
import { RightSidebar } from './components/RightSidebar';

export default function App() {
  return (
    <div className="flex flex-col h-screen bg-[#0D0D0F] text-slate-300 font-sans overflow-hidden selection:bg-fuchsia-500/30">
      <Navbar />
      <div className="flex flex-1 overflow-hidden">
        <LeftSidebar />
        <div className="flex flex-1 flex-col overflow-hidden">
          <CodeEditor />
          <Terminal />
        </div>
        <RightSidebar />
      </div>
    </div>
  );
}
