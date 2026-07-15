// Simple UI tabs component
export interface TabsProps {
  value: string;
  onValueChange: (value: string) => void;
  children: React.ReactNode;
  className?: string;
}

export function Tabs({ value, onValueChange, children, className }: TabsProps) {
  return <div className={className}>{children}</div>;
}

export interface TabsListProps {
  children: React.ReactNode;
  className?: string;
}

export function TabsList({ children, className }: TabsListProps) {
  return (
    <div className={`flex border-b border-gray-200 ${className || ''}`}>
      {children}
    </div>
  );
}

export interface TabsTriggerProps {
  value: string;
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
}

export function TabsTrigger({ value, children, className, onClick }: TabsTriggerProps) {
  return (
    <button onClick={onClick} className={`px-4 py-2 border-b-2 border-transparent hover:border-blue-500 ${className || ''}`}>
      {children}
    </button>
  );
}

export interface TabsContentProps {
  value: string;
  children: React.ReactNode;
  className?: string;
}

export function TabsContent({ value, children, className }: TabsContentProps) {
  return <div className={className}>{children}</div>;
}
