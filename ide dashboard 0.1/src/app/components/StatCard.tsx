import { LucideIcon } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string | number;
  change?: string;
  icon: LucideIcon;
  accentColor: 'fuchsia' | 'indigo';
}

export function StatCard({ title, value, change, icon: Icon, accentColor }: StatCardProps) {
  const gradientClass = accentColor === 'fuchsia' 
    ? 'from-fuchsia-600/20 to-fuchsia-600/5' 
    : 'from-indigo-600/20 to-indigo-600/5';
  
  const iconGradientClass = accentColor === 'fuchsia'
    ? 'bg-gradient-to-br from-fuchsia-600 to-fuchsia-400'
    : 'bg-gradient-to-br from-indigo-600 to-indigo-400';

  return (
    <div className={`bg-gradient-to-br ${gradientClass} backdrop-blur-sm border border-white/10 rounded-2xl p-6 transition-all duration-200 hover:border-fuchsia-600/50 hover:shadow-lg hover:shadow-fuchsia-600/20`}>
      <div className="flex items-start justify-between mb-4">
        <div className={`w-12 h-12 rounded-xl ${iconGradientClass} flex items-center justify-center shadow-lg`}>
          <Icon className="w-6 h-6 text-white" />
        </div>
        {change && (
          <span className="text-sm font-medium text-emerald-400">{change}</span>
        )}
      </div>
      
      <div className="text-3xl font-bold text-white mb-1">{value}</div>
      <div className="text-sm text-white/60">{title}</div>
    </div>
  );
}