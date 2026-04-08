import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const data = [
  { day: 'Mon', sessions: 4, focus: 85, id: 'mon' },
  { day: 'Tue', sessions: 6, focus: 92, id: 'tue' },
  { day: 'Wed', sessions: 5, focus: 78, id: 'wed' },
  { day: 'Thu', sessions: 8, focus: 95, id: 'thu' },
  { day: 'Fri', sessions: 7, focus: 88, id: 'fri' },
  { day: 'Sat', sessions: 3, focus: 72, id: 'sat' },
  { day: 'Sun', sessions: 4, focus: 80, id: 'sun' },
];

export function FocusChart() {
  return (
    <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-6 transition-all duration-200 hover:border-fuchsia-600/50 hover:shadow-lg hover:shadow-fuchsia-600/20">
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-white mb-1">Daily Focus Sessions</h2>
        <p className="text-sm text-white/50">Your focus patterns over the week</p>
      </div>
      
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
          <XAxis 
            dataKey="day" 
            stroke="rgba(255,255,255,0.3)"
            style={{ fontSize: '12px' }}
          />
          <YAxis 
            stroke="rgba(255,255,255,0.3)"
            style={{ fontSize: '12px' }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1a1a1f',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '8px',
              color: 'white'
            }}
          />
          <Line 
            type="monotone" 
            dataKey="sessions" 
            stroke="#6366F1" 
            strokeWidth={3}
            dot={(props) => {
              const { cx, cy, index } = props;
              return (
                <circle
                  key={`dot-sessions-${index}`}
                  cx={cx}
                  cy={cy}
                  r={4}
                  fill="#6366F1"
                  strokeWidth={0}
                />
              );
            }}
            activeDot={{ r: 6, fill: '#6366F1' }}
            name="Sessions"
          />
          <Line 
            type="monotone" 
            dataKey="focus" 
            stroke="#C026D3" 
            strokeWidth={3}
            dot={(props) => {
              const { cx, cy, index } = props;
              return (
                <circle
                  key={`dot-focus-${index}`}
                  cx={cx}
                  cy={cy}
                  r={4}
                  fill="#C026D3"
                  strokeWidth={0}
                />
              );
            }}
            activeDot={{ r: 6, fill: '#C026D3' }}
            name="Focus Score"
          />
        </LineChart>
      </ResponsiveContainer>
      
      <div className="flex items-center gap-6 mt-4">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-indigo-600"></div>
          <span className="text-sm text-white/70">Sessions</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-fuchsia-600"></div>
          <span className="text-sm text-white/70">Focus Score</span>
        </div>
      </div>
    </div>
  );
}
