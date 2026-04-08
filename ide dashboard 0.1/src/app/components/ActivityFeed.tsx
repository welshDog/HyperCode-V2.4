import { Bot, CheckCircle2, Code, Zap } from 'lucide-react';

interface Activity {
  id: string;
  type: 'agent' | 'task' | 'session' | 'code';
  title: string;
  time: string;
  description?: string;
}

const activities: Activity[] = [
  {
    id: '1',
    type: 'session',
    title: 'Deep Focus Session Completed',
    time: '2 min ago',
    description: '45 minutes • 98% focus score'
  },
  {
    id: '2',
    type: 'agent',
    title: 'Code Review Agent Finished',
    time: '12 min ago',
    description: 'Reviewed 8 files, 3 suggestions'
  },
  {
    id: '3',
    type: 'task',
    title: 'API Integration Task Done',
    time: '1 hour ago',
    description: 'User authentication flow'
  },
  {
    id: '4',
    type: 'code',
    title: 'Refactoring Sprint Complete',
    time: '2 hours ago',
    description: 'Cleaned up 1,234 lines of code'
  },
  {
    id: '5',
    type: 'agent',
    title: 'Testing Agent Running',
    time: '3 hours ago',
    description: 'Running 47 unit tests'
  },
];

const iconMap = {
  agent: Bot,
  task: CheckCircle2,
  session: Zap,
  code: Code,
};

const colorMap = {
  agent: 'text-fuchsia-400 bg-fuchsia-600/10',
  task: 'text-emerald-400 bg-emerald-600/10',
  session: 'text-indigo-400 bg-indigo-600/10',
  code: 'text-purple-400 bg-purple-600/10',
};

export function ActivityFeed() {
  return (
    <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-6 transition-all duration-200 hover:border-fuchsia-600/50 hover:shadow-lg hover:shadow-fuchsia-600/20">
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-white mb-1">🧠 Hyperfocus Activity Feed</h2>
        <p className="text-sm text-white/50">What's been happening</p>
      </div>
      
      <div className="space-y-4">
        {activities.map((activity) => {
          const Icon = iconMap[activity.type];
          const colorClass = colorMap[activity.type];
          
          return (
            <div key={activity.id} className="flex gap-3">
              <div className={`w-10 h-10 rounded-lg ${colorClass} flex items-center justify-center flex-shrink-0`}>
                <Icon className="w-5 h-5" />
              </div>
              
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="text-sm font-medium text-white">{activity.title}</h3>
                  <span className="text-xs text-white/40 whitespace-nowrap">{activity.time}</span>
                </div>
                {activity.description && (
                  <p className="text-sm text-white/50 mt-0.5">{activity.description}</p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}