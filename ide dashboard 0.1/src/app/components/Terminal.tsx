import React, { useState } from 'react';
import { Terminal as TerminalIcon, X, Maximize2, Minimize2 } from 'lucide-react';

export function Terminal() {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className={`border-t border-[#1e1e24] bg-[#0A0A0C] flex flex-col shrink-0 transition-all duration-300 ${isExpanded ? 'h-96' : 'h-48'}`}>
      <div className="flex items-center justify-between px-4 py-1.5 bg-[#0A0A0C] border-b border-[#1e1e24] shrink-0">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2 text-[11px] uppercase tracking-wider font-semibold text-slate-300 border-b border-fuchsia-500 pb-1 -mb-[7px]">
            <TerminalIcon className="w-3.5 h-3.5" />
            Terminal
          </div>
          <div className="flex items-center gap-2 text-[11px] uppercase tracking-wider font-semibold text-slate-500 hover:text-slate-300 cursor-pointer pb-1 -mb-[7px]">
            Output
          </div>
          <div className="flex items-center gap-2 text-[11px] uppercase tracking-wider font-semibold text-slate-500 hover:text-slate-300 cursor-pointer pb-1 -mb-[7px]">
            Problems <span className="bg-fuchsia-500/20 text-fuchsia-400 text-[10px] px-1.5 rounded-full">0</span>
          </div>
        </div>
        <div className="flex items-center gap-2 text-slate-500">
          <button onClick={() => setIsExpanded(!isExpanded)} className="hover:text-slate-300 p-1 rounded hover:bg-[#1A1A24]">
            {isExpanded ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </button>
          <button className="hover:text-slate-300 p-1 rounded hover:bg-[#1A1A24]">
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>
      
      <div className="flex-1 overflow-auto p-4 font-mono text-[13px] leading-relaxed text-slate-300">
        <div className="text-green-400 mb-1">welshdog@hypercode:~/HyperCode-V2$ docker ps</div>
        <div className="text-slate-400 mb-4 whitespace-pre">
{`CONTAINER ID   IMAGE                 COMMAND                  CREATED          STATUS          PORTS                    NAMES
8f9e7d6c5b4a   hypercode/agent:v2    "python agent.py"        10 minutes ago   Up 10 minutes   0.0.0.0:8000->8000/tcp   broski_core
3a2b1c4d5e6f   redis:alpine          "docker-entrypoint.s…"   2 hours ago      Up 2 hours      6379/tcp                 hyper_cache`}
        </div>
        <div className="text-green-400 mb-1">welshdog@hypercode:~/HyperCode-V2$ npm run dev</div>
        <div className="text-slate-400 mb-2">
          <span className="text-fuchsia-400 font-bold">VITE</span> v6.3.5  ready in 245 ms<br/><br/>
          ➜  <span className="text-slate-300 font-bold">Local:</span>   <span className="text-cyan-400 underline cursor-pointer">http://localhost:5173/</span><br/>
          ➜  <span className="text-slate-300 font-bold">Network:</span> use <span className="text-slate-300">--host</span> to expose<br/>
          ➜  <span className="text-slate-300 font-bold">press h to show help</span>
        </div>
        <div className="flex items-center text-green-400 mt-4">
          welshdog@hypercode:~/HyperCode-V2$ <span className="w-2 h-4 bg-fuchsia-500 ml-2 animate-[pulse_1s_step-end_infinite]"></span>
        </div>
      </div>
    </div>
  );
}
