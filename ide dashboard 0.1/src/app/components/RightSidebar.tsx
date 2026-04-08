import React from 'react';
import { Bot, Send, Activity, Focus, Cpu, CheckCircle2, History } from 'lucide-react';

export function RightSidebar() {
  const metrics = [
    { label: 'Focus Score', value: '94%', icon: <Activity className="w-4 h-4 text-fuchsia-400" /> },
    { label: 'Agents Running', value: '3', icon: <Cpu className="w-4 h-4 text-indigo-400" /> },
    { label: 'Sessions Today', value: '7', icon: <History className="w-4 h-4 text-emerald-400" /> },
    { label: 'Tasks Done', value: '12', icon: <CheckCircle2 className="w-4 h-4 text-cyan-400" /> },
  ];

  const activities = [
    { time: '10:42 AM', text: 'BROski optimized 3 render cycles', type: 'agent' },
    { time: '10:15 AM', text: 'Hyperfocus session completed (45m)', type: 'focus' },
    { time: '09:30 AM', text: 'Auto-resolved merge conflict in app.tsx', type: 'agent' },
    { time: '09:05 AM', text: 'Dev Mode activated by WelshDog', type: 'system' },
  ];

  return (
    <div className="w-80 border-l border-[#1e1e24] bg-[#0A0A0C] flex flex-col shrink-0 overflow-hidden hidden xl:flex">
      <div className="p-4 border-b border-[#1e1e24] bg-[#0D0D0F]">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded bg-[#1A1A24] border border-[#2d2d35] flex items-center justify-center shadow-[0_0_10px_rgba(192,38,211,0.1)]">
              <span className="text-xl">🤖</span>
            </div>
            <span className="font-semibold text-slate-200">BROski AI</span>
          </div>
          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-[#1A1A24] border border-[#2d2d35]">
            <span className="w-2 h-2 rounded-full bg-fuchsia-500 animate-[pulse_2s_ease-in-out_infinite] shadow-[0_0_8px_rgba(192,38,211,0.8)]"></span>
            <span className="text-[10px] font-mono text-fuchsia-400 font-bold">ACTIVE</span>
          </div>
        </div>
        
        <div className="text-xs text-slate-400 mb-4 p-2.5 rounded bg-[#15151A] border border-[#1e1e24]">
          <span className="text-fuchsia-400/80 mb-1 block uppercase text-[10px] tracking-wider font-semibold">Last Action</span>
          <span className="text-slate-300">Reviewed 8 files and suggested 3 neuro-friendly contrast adjustments.</span>
        </div>

        <div className="relative group">
          <input 
            type="text" 
            placeholder="Ask BROski..." 
            className="w-full bg-[#15151A] border border-[#2d2d35] group-hover:border-[#C026D3]/50 focus:border-[#C026D3] rounded-md py-2 pl-3 pr-10 text-sm text-slate-200 placeholder:text-slate-500 outline-none transition-all focus:shadow-[0_0_10px_rgba(192,38,211,0.1)]"
          />
          <button className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-slate-500 hover:text-fuchsia-400 transition-colors">
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="p-4 border-b border-[#1e1e24] bg-[#0D0D0F]">
        <h3 className="text-[11px] font-semibold tracking-wider text-slate-500 uppercase mb-3">Workspace Metrics</h3>
        <div className="grid grid-cols-2 gap-3">
          {metrics.map((m, idx) => (
            <div 
              key={idx} 
              className="bg-[#15151A] border border-[#1e1e24] hover:border-[#C026D3]/40 rounded-lg p-3 transition-all hover:shadow-[0_0_15px_rgba(192,38,211,0.05)] cursor-default group"
            >
              <div className="flex items-center justify-between mb-2">
                {m.icon}
                <span className="text-lg font-bold text-slate-200 group-hover:text-white transition-colors">{m.value}</span>
              </div>
              <div className="text-[11px] text-slate-500 font-medium">{m.label}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-auto p-4 bg-[#0A0A0C]">
        <h3 className="text-[11px] font-semibold tracking-wider text-slate-500 uppercase mb-4 flex items-center gap-2">
          <span className="text-sm">🧠</span> Hyperfocus Activity Feed
        </h3>
        <div className="space-y-4 relative before:absolute before:inset-0 before:ml-2 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-[#C026D3]/20 before:to-transparent ml-2 md:ml-0 md:before:hidden">
          {activities.map((act, idx) => (
            <div key={idx} className="flex gap-3 items-start group relative">
              <div className={`mt-1 w-2 h-2 rounded-full shrink-0 shadow-[0_0_8px_rgba(0,0,0,0.5)] ${
                act.type === 'agent' ? 'bg-fuchsia-500' :
                act.type === 'focus' ? 'bg-indigo-500' : 'bg-slate-500'
              } group-hover:scale-125 transition-transform z-10`} />
              <div className="absolute left-1 top-3 bottom-[-16px] w-px bg-gradient-to-b from-[#2d2d35] to-transparent last:hidden" />
              <div>
                <div className="text-[13px] text-slate-300 font-medium group-hover:text-slate-100 transition-colors leading-tight">{act.text}</div>
                <div className="text-[10px] text-slate-500 font-mono mt-1">{act.time}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
