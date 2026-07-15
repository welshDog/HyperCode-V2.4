// Simple UI Card components
export interface CardProps {
  children: React.ReactNode;
  className?: string;
}

export function Card({ children, className }: CardProps) {
  return (
    <div className={`border border-gray-200 rounded-lg shadow-sm ${className || ''}`}>
      {children}
    </div>
  );
}

export function CardHeader({ children, className }: CardProps) {
  return <div className={`border-b border-gray-200 p-4 ${className || ''}`}>{children}</div>;
}

export function CardTitle({ children, className }: CardProps) {
  return <h3 className={`text-lg font-semibold ${className || ''}`}>{children}</h3>;
}

export function CardContent({ children, className }: CardProps) {
  return <div className={`p-4 ${className || ''}`}>{children}</div>;
}
