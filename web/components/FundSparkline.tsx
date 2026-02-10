
'use client';

import React from 'react';

interface Props {
  data: number[];
  width?: number;
  height?: number;
  className?: string;
  isPositive?: boolean;
}

export function FundSparkline({ data, width = 80, height = 30, className = '', isPositive = true }: Props) {
  if (!data || data.length < 2) return <div style={{ width, height }} className="opacity-0" />;

  // Map normalized data (0-1) to SVG coordinates
  const points = data.map((val, i) => {
    const x = (i / (data.length - 1)) * width;
    const y = height - (val * height);
    return `${x},${y}`;
  }).join(' ');

  const color = isPositive ? '#ef4444' : '#10b981'; // Rose-500 : Emerald-500

  return (
    <div className={`relative ${className}`} style={{ width, height }}>
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="overflow-visible">
        {/* Fill Area */}
        <path
          d={`M 0,${height} L ${points} L ${width},${height} Z`}
          fill={`url(#gradient-${isPositive ? 'up' : 'down'})`}
          className="opacity-20"
        />
        {/* The Line */}
        <polyline
          fill="none"
          stroke={color}
          strokeWidth="1.5"
          strokeLinejoin="round"
          strokeLinecap="round"
          points={points}
        />
        {/* End Point Dot */}
        <circle
          cx={width}
          cy={height - (data[data.length - 1] * height)}
          r="2"
          fill={color}
          className="animate-pulse"
        />
        
        {/* Gradients */}
        <defs>
          <linearGradient id="gradient-up" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#ef4444" stopOpacity="0.4" />
            <stop offset="100%" stopColor="#ef4444" stopOpacity="0" />
          </linearGradient>
          <linearGradient id="gradient-down" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#10b981" stopOpacity="0.4" />
            <stop offset="100%" stopColor="#10b981" stopOpacity="0" />
          </linearGradient>
        </defs>
      </svg>
    </div>
  );
}
