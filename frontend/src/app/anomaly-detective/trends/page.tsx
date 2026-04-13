'use client';

import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  TrendingUp,
  TrendingDown,
  Minus,
  AlertTriangle,
  Loader2,
  BarChart3,
  Activity,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { listAnomalies, getAnomalyStats } from '@/lib/api';
import type { Anomaly, AnomalySeverity } from '@/lib/types';

const SEVERITY_COLORS: Record<AnomalySeverity, string> = {
  CRITICAL: '#ef4444',
  HIGH: '#f97316',
  MEDIUM: '#eab308',
  LOW: '#3b82f6',
  INFO: '#94a3b8',
};

const RISK_BINS = [
  { label: '0–19', min: 0, max: 19 },
  { label: '20–39', min: 20, max: 39 },
  { label: '40–59', min: 40, max: 59 },
  { label: '60–79', min: 60, max: 79 },
  { label: '80–100', min: 80, max: 100 },
];

type Granularity = 'daily' | 'weekly' | 'monthly';

function formatDateKey(date: string, granularity: Granularity): string {
  const d = new Date(date);
  if (granularity === 'monthly') return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
  if (granularity === 'weekly') {
    const startOfWeek = new Date(d);
    startOfWeek.setDate(d.getDate() - d.getDay());
    return startOfWeek.toISOString().slice(0, 10);
  }
  return d.toISOString().slice(0, 10);
}

function TrendIcon({ trend }: { trend: 'UP' | 'DOWN' | 'STABLE' }) {
  if (trend === 'UP') return <TrendingUp className="h-4 w-4 text-red-500" />;
  if (trend === 'DOWN') return <TrendingDown className="h-4 w-4 text-green-500" />;
  return <Minus className="h-4 w-4 text-slate-400" />;
}

export default function TrendsPage() {
  const [granularity, setGranularity] = useState<Granularity>('daily');

  const { data: anomaliesData, isLoading: loadingAnomalies, error: anomaliesError } = useQuery({
    queryKey: ['anomalies-trends'],
    queryFn: () => listAnomalies({ page_size: 500 }),
  });

  const { data: stats, isLoading: loadingStats } = useQuery({
    queryKey: ['anomaly-stats'],
    queryFn: getAnomalyStats,
  });

  const anomalies = anomaliesData?.items ?? [];
  const isLoading = loadingAnomalies || loadingStats;

  // Time series data: anomaly count over time
  const timeSeriesData = useMemo(() => {
    if (!anomalies.length) return [];
    const groups: Record<string, number> = {};
    anomalies.forEach((a) => {
      const key = formatDateKey(a.detected_at, granularity);
      groups[key] = (groups[key] ?? 0) + 1;
    });
    return Object.entries(groups)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, count]) => ({ date, count }));
  }, [anomalies, granularity]);

  // Severity over time (stacked)
  const severityTimeData = useMemo(() => {
    if (!anomalies.length) return [];
    const groups: Record<string, Record<string, number>> = {};
    anomalies.forEach((a) => {
      const key = formatDateKey(a.detected_at, granularity);
      if (!groups[key]) groups[key] = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0, INFO: 0 };
      groups[key][a.severity] = (groups[key][a.severity] ?? 0) + 1;
    });
    return Object.entries(groups)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, sevs]) => ({ date, ...sevs }));
  }, [anomalies, granularity]);

  // Risk score histogram
  const riskHistogram = useMemo(() => {
    return RISK_BINS.map((bin) => ({
      label: bin.label,
      count: anomalies.filter((a) => a.risk_score >= bin.min && a.risk_score <= bin.max).length,
    }));
  }, [anomalies]);

  // Severity pie
  const severityPie = useMemo(() => {
    if (!stats) return [];
    return (['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'] as AnomalySeverity[])
      .map((sev) => ({ name: sev, value: stats.by_severity[sev] ?? 0 }))
      .filter((s) => s.value > 0);
  }, [stats]);

  // Top detectors
  const topDetectors = useMemo(() => {
    const counts: Record<string, number> = {};
    anomalies.forEach((a) => {
      counts[a.rule_name] = (counts[a.rule_name] ?? 0) + 1;
    });
    return Object.entries(counts)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 8)
      .map(([name, count]) => ({ name, count }));
  }, [anomalies]);

  // Avg risk score
  const avgRisk = useMemo(() => {
    if (!anomalies.length) return 0;
    return Math.round(anomalies.reduce((sum, a) => sum + a.risk_score, 0) / anomalies.length);
  }, [anomalies]);

  if (anomaliesError) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[40vh] gap-3">
        <AlertTriangle className="h-10 w-10 text-amber-500" />
        <p className="text-sm text-slate-500">Failed to load trend data</p>
        <p className="text-xs text-slate-400">{String(anomaliesError)}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-200">Trend Analysis</h1>
          <p className="text-sm text-slate-500 mt-1">Historical anomaly patterns and detection statistics</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">Granularity:</span>
          {(['daily', 'weekly', 'monthly'] as Granularity[]).map((g) => (
            <button
              key={g}
              onClick={() => setGranularity(g)}
              className={`px-3 py-1.5 text-xs rounded-md border transition-colors ${
                granularity === g
                  ? 'bg-slate-900 text-white border-slate-900 dark:bg-white dark:text-slate-900'
                  : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700'
              }`}
            >
              {g.charAt(0).toUpperCase() + g.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Summary Cards */}
      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i}><CardContent className="pt-6"><Skeleton className="h-8 w-20" /><Skeleton className="h-4 w-32 mt-2" /></CardContent></Card>
          ))}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Anomalies</CardTitle>
              {stats && <TrendIcon trend={stats.recent_trend} />}
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats?.total ?? 0}</div>
              <p className="text-xs text-slate-500 mt-1">
                {stats?.recent_trend === 'UP' ? 'Increasing' : stats?.recent_trend === 'DOWN' ? 'Decreasing' : 'Stable'} trend
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Open Critical</CardTitle>
              <AlertTriangle className="h-4 w-4 text-red-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">{stats?.open_critical ?? 0}</div>
              <p className="text-xs text-slate-500 mt-1">Requires immediate attention</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Open High</CardTitle>
              <AlertTriangle className="h-4 w-4 text-orange-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-orange-600">{stats?.open_high ?? 0}</div>
              <p className="text-xs text-slate-500 mt-1">Under monitoring</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Avg Risk Score</CardTitle>
              <Activity className="h-4 w-4 text-slate-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{avgRisk}</div>
              <p className="text-xs text-slate-500 mt-1">Across all anomalies</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Charts Row 1: Timeline + Severity Over Time */}
      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2">
          <Card><CardContent className="pt-6"><Skeleton className="h-[300px] w-full" /></CardContent></Card>
          <Card><CardContent className="pt-6"><Skeleton className="h-[300px] w-full" /></CardContent></Card>
        </div>
      ) : anomalies.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16">
            <BarChart3 className="h-12 w-12 text-slate-300 mb-3" />
            <p className="text-sm text-slate-500">No anomaly data available yet</p>
            <p className="text-xs text-slate-400 mt-1">Run a scan to see trend analysis</p>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2">
            {/* Anomaly Count Over Time */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium">Anomaly Count Over Time</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={timeSeriesData}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-slate-200 dark:stroke-slate-700" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Line type="monotone" dataKey="count" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3 }} name="Anomalies" />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Severity Distribution Over Time */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium">Severity Distribution Over Time</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={severityTimeData}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-slate-200 dark:stroke-slate-700" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Legend />
                    {(['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'] as AnomalySeverity[]).map((sev) => (
                      <Area
                        key={sev}
                        type="monotone"
                        dataKey={sev}
                        stackId="severity"
                        fill={SEVERITY_COLORS[sev]}
                        stroke={SEVERITY_COLORS[sev]}
                        fillOpacity={0.6}
                      />
                    ))}
                  </AreaChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>

          {/* Charts Row 2: Risk Histogram + Severity Pie */}
          <div className="grid gap-4 md:grid-cols-2">
            {/* Risk Score Histogram */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium">Risk Score Distribution</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={riskHistogram}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-slate-200 dark:stroke-slate-700" />
                    <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Bar dataKey="count" name="Anomalies" radius={[4, 4, 0, 0]}>
                      {riskHistogram.map((entry, i) => (
                        <Cell key={i} fill={['#3b82f6', '#eab308', '#f97316', '#ef4444', '#dc2626'][i]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Severity Breakdown Pie */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium">Severity Breakdown</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={severityPie}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      paddingAngle={2}
                      dataKey="value"
                      nameKey="name"
                      label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
                    >
                      {severityPie.map((entry) => (
                        <Cell key={entry.name} fill={SEVERITY_COLORS[entry.name as AnomalySeverity]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>

          {/* Top Detectors */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">Top Detection Rules</CardTitle>
            </CardHeader>
            <CardContent>
              {topDetectors.length === 0 ? (
                <p className="text-sm text-slate-400 text-center py-8">No detection data available</p>
              ) : (
                <div className="space-y-3">
                  {topDetectors.map((d) => {
                    const maxCount = topDetectors[0]?.count ?? 1;
                    const pct = Math.round((d.count / maxCount) * 100);
                    return (
                      <div key={d.name} className="flex items-center gap-3">
                        <span className="text-sm text-slate-600 dark:text-slate-300 w-48 truncate">{d.name}</span>
                        <div className="flex-1 bg-slate-100 dark:bg-slate-800 rounded-full h-5 overflow-hidden">
                          <div
                            className="bg-blue-500 h-full rounded-full transition-all"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        <span className="text-sm font-medium text-slate-700 dark:text-slate-300 w-10 text-right">{d.count}</span>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
