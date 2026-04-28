'use client';

// 📈 SparkLine — tiny inline SVG latency chart
// Renders last N latency_ms readings as a mini sparkline
// Used in SystemHealth panel beside each service

interface SparkLineProps {
  data: number[];        // array of latency_ms values (newest last)
  width?: number;
  height?: number;
  colour?: string;
  className?: string;
}

export function SparkLine({
  data,
  width = 60,
  height = 20,
  colour = '#22c55e',
  className = '',
}: SparkLineProps) {
  if (!data || data.length < 2) {
    return <span className={`inline-block ${className}`} style={{ width, height }} />;
  }

  const max = Math.max(...data, 1);
  const min = Math.min(...data, 0);
  const range = max - min || 1;
  const step = width / (data.length - 1);

  const points = data
    .map((v, i) => {
      const x = i * step;
      const y = height - ((v - min) / range) * (height - 2) - 1;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');

  const lastVal = data[data.length - 1];
  const isHigh = lastVal > max * 0.8;
  const lineColour = isHigh ? '#f59e0b' : colour;

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className={`inline-block shrink-0 ${className}`}
      aria-hidden
    >
      <polyline
        fill="none"
        stroke={lineColour}
        strokeWidth="1.5"
        strokeLinejoin="round"
        strokeLinecap="round"
        points={points}
      />
    </svg>
  );
}
