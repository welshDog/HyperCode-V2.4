import React, { useState } from 'react';
import { ChevronRight, ChevronDown, Folder, FileCode2, FileText, FileJson, FileType2 } from 'lucide-react';

const fileStructure = [
  {
    name: 'agents',
    type: 'folder',
    children: [
      { name: 'broski.py', type: 'file', ext: 'py' },
      { name: 'memory.ts', type: 'file', ext: 'ts' }
    ]
  },
  {
    name: 'dashboard',
    type: 'folder',
    isOpen: true,
    children: [
      { name: 'page.tsx', type: 'file', ext: 'tsx', active: true },
      { name: 'layout.tsx', type: 'file', ext: 'tsx' },
      { name: 'styles.css', type: 'file', ext: 'css' }
    ]
  },
  {
    name: 'core',
    type: 'folder',
    children: [
      { name: 'engine.py', type: 'file', ext: 'py' }
    ]
  },
  {
    name: 'plugins',
    type: 'folder',
    children: [
      { name: 'config.yaml', type: 'file', ext: 'yaml' }
    ]
  },
  {
    name: 'docs',
    type: 'folder',
    children: [
      { name: 'readme.md', type: 'file', ext: 'md' }
    ]
  },
  {
    name: 'tests',
    type: 'folder',
    children: [
      { name: 'agent_test.py', type: 'file', ext: 'py' }
    ]
  }
];

const getIcon = (ext: string) => {
  switch(ext) {
    case 'py': return <FileCode2 className="w-4 h-4 text-blue-400" />;
    case 'ts': 
    case 'tsx': return <FileCode2 className="w-4 h-4 text-blue-500" />;
    case 'yaml': return <FileJson className="w-4 h-4 text-orange-400" />;
    case 'md': return <FileText className="w-4 h-4 text-slate-400" />;
    case 'css': return <FileType2 className="w-4 h-4 text-cyan-400" />;
    default: return <FileText className="w-4 h-4 text-slate-400" />;
  }
};

export function LeftSidebar() {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({'dashboard': true});

  const toggleFolder = (name: string) => {
    setExpanded(prev => ({...prev, [name]: !prev[name]}));
  };

  return (
    <div className="w-64 border-r border-[#1e1e24] bg-[#0A0A0C] flex flex-col shrink-0 overflow-y-auto hidden md:flex text-slate-300">
      <div className="p-3 text-[11px] font-semibold tracking-wider text-slate-500 uppercase flex items-center justify-between">
        <span>Explorer</span>
      </div>
      <div className="px-2 pb-4">
        <div className="flex items-center gap-1.5 px-2 py-1.5 hover:bg-[#1A1A24] rounded cursor-pointer group mb-1">
          <ChevronDown className="w-4 h-4 text-slate-400 group-hover:text-slate-200 transition-colors" />
          <span className="text-sm font-semibold text-slate-200">HyperCode-V2</span>
        </div>
        <div className="pl-4 mt-1 space-y-0.5">
          {fileStructure.map((folder, idx) => (
            <div key={idx}>
              <div 
                className="flex items-center gap-1.5 px-2 py-1.5 hover:bg-[#1A1A24] rounded cursor-pointer group transition-colors"
                onClick={() => toggleFolder(folder.name)}
              >
                {expanded[folder.name] ? (
                  <ChevronDown className="w-3.5 h-3.5 text-slate-400 group-hover:text-slate-300" />
                ) : (
                  <ChevronRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-slate-300" />
                )}
                <Folder className="w-4 h-4 text-indigo-400" fill="currentColor" fillOpacity={0.2} />
                <span className="text-sm text-slate-300 group-hover:text-slate-100">{folder.name}</span>
              </div>
              
              {expanded[folder.name] && folder.children && (
                <div className="pl-6 space-y-0.5 mt-0.5 mb-1.5">
                  {folder.children.map((file, fidx) => (
                    <div 
                      key={fidx} 
                      className={`flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer transition-colors ${
                        file.active 
                          ? 'bg-[#C026D3]/10 text-fuchsia-400 border border-[#C026D3]/20 shadow-[0_0_10px_rgba(192,38,211,0.05)]' 
                          : 'hover:bg-[#1A1A24] text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      {getIcon(file.ext)}
                      <span className="text-[13px] font-mono">{file.name}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
