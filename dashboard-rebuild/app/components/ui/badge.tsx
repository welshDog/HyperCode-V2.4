// Simple UI badge component
export interface BadgeProps {
  children: React.ReactNode;
  className?: string;
}

export function Badge({ children, className }: BadgeProps) {
  return (
    <span className={`inline-block px-3 py-1 text-sm font-semibold rounded-full ${className || 'bg-gray-200 text-gray-800'}`}>
      {children}
    </span>
  );
}
