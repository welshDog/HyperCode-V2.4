import React from 'react';
import { Zap, User } from 'lucide-react';

export function Navbar() {
  return (
    <header className="h-14 border-b border-[#1e1e24] bg-[#0D0D0F] flex items-center justify-between px-4 shrink-0">
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 rounded bg-gradient-to-br from-[#C026D3] to-[#6366F1] flex items-center justify-center shadow-[0_0_15px_rgba(192,38,211,0.3)]">
          <Zap className="w-5 h-5 text-white fill-white" />
        </div>
        <span className="font-bold text-lg tracking-tight text-white">HyperCode</span>
      </div>

      <div className="flex items-center">
        <button className="flex items-center gap-2 bg-[#1A1A24] hover:bg-[#252533] border border-[#2d2d35] hover:border-[#C026D3]/50 transition-all rounded-full px-4 py-1.5 group shadow-[0_0_0_rgba(192,38,211,0)] hover:shadow-[0_0_15px_rgba(192,38,211,0.2)]">
          <span className="text-xl group-hover:animate-[pulse_1.5s_ease-in-out_infinite]">⚡</span>
          <span className="font-semibold text-sm text-fuchsia-400 group-hover:text-fuchsia-300">BROski AI</span>
        </button>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex flex-col items-end">
          <span className="text-sm font-medium text-slate-200">WelshDog</span>
          <span className="text-[10px] text-indigo-400 font-mono tracking-wider flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-[pulse_2s_ease-in-out_infinite]"></span>
            DEV MODE: ON
          </span>
        </div>
        <div className="w-9 h-9 rounded-full bg-[#1A1A24] border border-[#2d2d35] flex items-center justify-center overflow-hidden">
           <User className="w-5 h-5 text-slate-400" />
        </div>
      </div>
    </header>
  );
}
