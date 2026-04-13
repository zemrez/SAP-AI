import { cn } from '@/lib/utils';

interface RiskScoreBadgeProps {
  score: number; // 0-100
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

function getRiskColor(score: number): {
  text: string;
  stroke: string;
  bg: string;
  label: string;
} {
  if (score <= 25) {
    return {
      text: 'text-blue-700 dark:text-blue-400',
      stroke: 'stroke-blue-500',
      bg: 'bg-blue-50 dark:bg-blue-950',
      label: 'Low',
    };
  }
  if (score <= 50) {
    return {
      text: 'text-yellow-700 dark:text-yellow-400',
      stroke: 'stroke-yellow-500',
      bg: 'bg-yellow-50 dark:bg-yellow-950',
      label: 'Medium',
    };
  }
  if (score <= 75) {
    return {
      text: 'text-orange-700 dark:text-orange-400',
      stroke: 'stroke-orange-500',
      bg: 'bg-orange-50 dark:bg-orange-950',
      label: 'High',
    };
  }
  return {
    text: 'text-red-700 dark:text-red-400',
    stroke: 'stroke-red-500',
    bg: 'bg-red-50 dark:bg-red-950',
    label: 'Critical',
  };
}

const SIZES = {
  sm: { outer: 32, strokeWidth: 3, fontSize: 'text-[9px]' },
  md: { outer: 48, strokeWidth: 4, fontSize: 'text-xs' },
  lg: { outer: 64, strokeWidth: 5, fontSize: 'text-sm' },
};

export function RiskScoreBadge({
  score,
  size = 'md',
  className,
}: RiskScoreBadgeProps) {
  const clamped = Math.max(0, Math.min(100, score));
  const colors = getRiskColor(clamped);
  const { outer, strokeWidth, fontSize } = SIZES[size];

  const radius = (outer - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const dashOffset = circumference * (1 - clamped / 100);
  const center = outer / 2;

  return (
    <div
      className={cn('relative inline-flex items-center justify-center', className)}
      style={{ width: outer, height: outer }}
      title={`Risk Score: ${clamped} (${colors.label})`}
    >
      <svg
        width={outer}
        height={outer}
        viewBox={`0 0 ${outer} ${outer}`}
        className="-rotate-90"
        aria-hidden="true"
      >
        {/* Background track */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          strokeWidth={strokeWidth}
          className="stroke-slate-200 dark:stroke-slate-700"
        />
        {/* Progress arc */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          strokeLinecap="round"
          className={colors.stroke}
          style={{ transition: 'stroke-dashoffset 0.4s ease' }}
        />
      </svg>
      {/* Score text */}
      <span
        className={cn(
          'absolute font-bold tabular-nums',
          fontSize,
          colors.text
        )}
      >
        {clamped}
      </span>
    </div>
  );
}
