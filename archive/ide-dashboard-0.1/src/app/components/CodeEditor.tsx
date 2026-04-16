import React from 'react';
import { X, FileCode2, FileJson, FileType2 } from 'lucide-react';

export function CodeEditor() {
  const tabs = [
    { name: 'broski.py', active: false, icon: <FileType2 className="w-3.5 h-3.5 text-blue-400" /> },
    { name: 'page.tsx', active: true, icon: <FileCode2 className="w-3.5 h-3.5 text-blue-500" /> },
    { name: 'config.yaml', active: false, icon: <FileJson className="w-3.5 h-3.5 text-orange-400" /> },
  ];

  const codeLines = [
    `import React from 'react';`,
    `import { AgentContext } from '@hypercode/core';`,
    `import { useBroski } from '../agents/broski';`,
    ``,
    `export default function Dashboard() {`,
    `  const { status, analyzeCode } = useBroski();`,
    `  `,
    `  // BROski AI automatically optimizes performance`,
    `  React.useEffect(() => {`,
    `    if (status === 'ACTIVE') {`,
    `      analyzeCode({ deepScan: true, autoFix: true });`,
    `    }`,
    `  }, [status, analyzeCode]);`,
    ``,
    `  return (`,
    `    <main className="dashboard-container">`,
    `      <Header variant="neurodivergent-friendly" />`,
    `      <WorkspaceMetrics theme="dark-fuchsia" />`,
    `      <AgentActivityFeed />`,
    `    </main>`,
    `  );`,
    `}`,
  ];

  return (
    <div className="flex-1 flex flex-col bg-[#0D0D0F] min-h-0 text-slate-300">
      <div className="flex bg-[#0A0A0C] border-b border-[#1e1e24] shrink-0 overflow-x-auto">
        {tabs.map((tab, idx) => (
          <div 
            key={idx} 
            className={`flex items-center gap-2.5 px-4 py-2 text-sm cursor-pointer border-r border-[#1e1e24] group relative ${
              tab.active 
                ? 'bg-[#0D0D0F] text-fuchsia-400 border-t-2 border-t-[#C026D3]' 
                : 'text-slate-400 hover:bg-[#15151A] hover:text-slate-200 border-t-2 border-t-transparent'
            }`}
          >
            {tab.active && (
              <div className="absolute top-0 left-0 w-full h-4 bg-gradient-to-b from-[#C026D3]/10 to-transparent pointer-events-none" />
            )}
            {tab.icon}
            <span className="font-mono">{tab.name}</span>
            <X className={`w-3.5 h-3.5 rounded-sm p-0.5 ml-2 ${tab.active ? 'text-fuchsia-400 hover:bg-[#C026D3]/20' : 'text-slate-500 hover:bg-slate-700/50 hover:text-slate-200'} transition-colors`} />
          </div>
        ))}
        <div className="flex-1 bg-[#0A0A0C]"></div>
      </div>
      
      <div className="flex-1 overflow-auto p-4 font-mono text-[14px] leading-relaxed flex">
        <div className="flex flex-col text-slate-600 text-right pr-4 select-none border-r border-[#1e1e24] mr-4">
          {codeLines.map((_, idx) => (
            <span key={idx} className="h-6">{idx + 1}</span>
          ))}
        </div>
        <div className="flex flex-col text-slate-300 whitespace-pre">
          {codeLines.map((line, idx) => {
            let highlighted = line
              .replace(/(import|from|export|default|function|const|if|return)/g, '<span class="text-indigo-400">$1</span>')
              .replace(/('@hypercode\/core'|'react'|'\.\.\/agents\/broski'|'ACTIVE'|"dashboard-container"|"neurodivergent-friendly"|"dark-fuchsia")/g, '<span class="text-green-400">$1</span>')
              .replace(/(\/\/.*)/g, '<span class="text-slate-500 italic">$1</span>')
              .replace(/(React\.useEffect|analyzeCode)/g, '<span class="text-fuchsia-300">$1</span>')
              .replace(/(<[A-Za-z]+|<\/[A-Za-z]+>|\/>)/g, '<span class="text-cyan-400">$1</span>');
              
            return (
              <div key={idx} dangerouslySetInnerHTML={{ __html: highlighted || ' ' }} className="h-6" />
            );
          })}
        </div>
      </div>
    </div>
  );
}
