import { Home, Folder, Bot, BarChart3, Settings } from 'lucide-react';

interface NavigationSidebarProps {
  activeItem?: string;
}

export function NavigationSidebar({ activeItem = 'Stats' }: NavigationSidebarProps) {
  const navItems = [
    { icon: Home, label: 'Home' },
    { icon: Folder, label: 'Projects' },
    { icon: Bot, label: 'Agents' },
    { icon: BarChart3, label: 'Stats' },
    { icon: Settings, label: 'Settings' },
  ];

  return (
    <aside className="w-20 bg-[#0D0D0F] border-r border-white/10 flex flex-col items-center py-6 gap-6">
      {navItems.map((item) => {
        const Icon = item.icon;
        const isActive = item.label === activeItem;
        
        return (
          <button
            key={item.label}
            className={`
              relative w-12 h-12 rounded-xl flex items-center justify-center
              transition-all duration-200
              ${isActive 
                ? 'bg-fuchsia-600/20 shadow-lg shadow-fuchsia-600/30' 
                : 'bg-white/5 hover:bg-white/10'
              }
            `}
            aria-label={item.label}
          >
            {isActive && (
              <div className="absolute -left-1 top-1/2 -translate-y-1/2 w-1 h-8 bg-fuchsia-600 rounded-full shadow-lg shadow-fuchsia-600/50" />
            )}
            <Icon className={`w-5 h-5 ${isActive ? 'text-fuchsia-400' : 'text-white/60'}`} />
          </button>
        );
      })}
    </aside>
  );
}