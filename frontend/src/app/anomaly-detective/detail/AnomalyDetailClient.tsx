'use client';

import { useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  User,
  Clock,
  Loader2,
  Sparkles,
  AlertTriangle,
  FileText,
  Activity,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { RiskScoreBadge } from '@/components/anomaly-detective/RiskScoreBadge';
import {
  getAnomaly,
  patchAnomaly,
  requestAnomalyExplanation,
} from '@/lib/api';
import type { AnomalyStatus } from '@/lib/types';

const STATUS_OPTIONS: Array<{ label: string; value: AnomalyStatus }> = [
  { label: 'Open', value: 'OPEN' },
  { label: 'Investigating', value: 'INVESTIGATING' },
  { label: 'Resolved', value: 'RESOLVED' },
  { label: 'False Positive', value: 'FALSE_POSITIVE' },
];

function severityColor(severity: string) {
  switch (severity) {
    case 'CRITICAL':
      return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400';
    case 'HIGH':
      return 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400';
    case 'MEDIUM':
      return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400';
    case 'LOW':
      return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400';
    default:
      return 'bg-slate-100 text-slate-800 dark:bg-slate-900/30 dark:text-slate-400';
  }
}

function statusColor(status: string) {
  switch (status) {
    case 'OPEN':
      return 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400';
    case 'INVESTIGATING':
      return 'bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400';
    case 'RESOLVED':
      return 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400';
    case 'FALSE_POSITIVE':
      return 'bg-slate-50 text-slate-600 dark:bg-slate-900/20 dark:text-slate-400';
    default:
      return '';
  }
}

export default function AnomalyDetailClient() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const id = searchParams.get('id') ?? '';

  const [assignTo, setAssignTo] = useState('');
  const [resolutionNotes, setResolutionNotes] = useState('');
  const [showResolutionNotes, setShowResolutionNotes] = useState(false);

  const { data: anomaly, isLoading, isError, error } = useQuery({
    queryKey: ['anomaly', id],
    queryFn: () => getAnomaly(id),
    enabled: !!id,
  });

  const statusMutation = useMutation({
    mutationFn: (newStatus: AnomalyStatus) =>
      patchAnomaly(id, {
        status: newStatus,
        resolution_notes:
          (newStatus === 'RESOLVED' || newStatus === 'FALSE_POSITIVE')
            ? resolutionNotes || undefined
            : undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['anomaly', id] });
      queryClient.invalidateQueries({ queryKey: ['anomalies'] });
    },
  });

  const assignMutation = useMutation({
    mutationFn: () => patchAnomaly(id, { assigned_to: assignTo }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['anomaly', id] });
      setAssignTo('');
    },
  });

  const explainMutation = useMutation({
    mutationFn: () => requestAnomalyExplanation(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['anomaly', id] });
    },
  });

  if (!id) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <AlertTriangle className="h-8 w-8 text-red-400 mb-3" />
        <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
          No anomaly ID provided
        </p>
        <Button
          variant="outline"
          size="sm"
          className="mt-4"
          onClick={() => router.push('/anomaly-detective')}
        >
          Back to list
        </Button>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 space-y-4">
            <Skeleton className="h-48" />
            <Skeleton className="h-64" />
          </div>
          <div className="space-y-4">
            <Skeleton className="h-40" />
            <Skeleton className="h-40" />
          </div>
        </div>
      </div>
    );
  }

  if (isError || !anomaly) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <AlertTriangle className="h-8 w-8 text-red-400 mb-3" />
        <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
          Failed to load anomaly
        </p>
        <p className="text-xs text-slate-500 mt-1">
          {error instanceof Error ? error.message : 'Anomaly not found'}
        </p>
        <Button
          variant="outline"
          size="sm"
          className="mt-4"
          onClick={() => router.push('/anomaly-detective')}
        >
          Back to list
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Back + Header */}
      <div className="flex items-start gap-4">
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={() => router.push('/anomaly-detective')}
        >
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            <RiskScoreBadge score={anomaly.risk_score} size="lg" />
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                  {anomaly.document_number ?? 'Anomaly'}
                </h2>
                <span
                  className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ${severityColor(anomaly.severity)}`}
                >
                  {anomaly.severity}
                </span>
                <span
                  className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ${statusColor(anomaly.status)}`}
                >
                  {anomaly.status.replace('_', ' ')}
                </span>
              </div>
              <p className="text-sm text-slate-500 mt-0.5">{anomaly.description}</p>
            </div>
          </div>
        </div>

        {/* Status dropdown */}
        <Select
          value={anomaly.status}
          onValueChange={(val: string | null) => {
            if (!val) return;
            const newStatus = val as AnomalyStatus;
            if (newStatus === 'RESOLVED' || newStatus === 'FALSE_POSITIVE') {
              setShowResolutionNotes(true);
            }
            statusMutation.mutate(newStatus);
          }}
        >
          <SelectTrigger className="w-[170px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {STATUS_OPTIONS.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Left column */}
        <div className="lg:col-span-2 space-y-4">
          {/* Details card */}
          <Card className="border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 shadow-none">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-sm">
                <FileText className="h-4 w-4 text-slate-500" />
                Details
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <DetailItem label="Company Code" value={anomaly.company_code} />
                <DetailItem label="Fiscal Year" value={anomaly.fiscal_year} />
                <DetailItem label="Fiscal Period" value={anomaly.fiscal_period || '—'} />
                <DetailItem
                  label="Posting Date"
                  value={anomaly.posting_date
                    ? new Date(anomaly.posting_date).toLocaleDateString()
                    : anomaly.detected_at
                      ? new Date(anomaly.detected_at).toLocaleDateString()
                      : '—'
                  }
                />
                <DetailItem
                  label="Amount"
                  value={
                    anomaly.amount != null
                      ? `${anomaly.amount.toLocaleString()} ${anomaly.currency ?? ''}`
                      : '—'
                  }
                />
                <DetailItem label="Currency" value={anomaly.currency ?? '—'} />
                <DetailItem label="GL Account" value={anomaly.gl_account ?? '—'} />
                <DetailItem label="Vendor ID" value={anomaly.vendor_id ?? '—'} />
                <DetailItem label="Detector" value={anomaly.rule_name} />
                <DetailItem
                  label="Detected At"
                  value={new Date(anomaly.detected_at).toLocaleString()}
                />
                <DetailItem
                  label="Last Updated"
                  value={new Date(anomaly.updated_at).toLocaleString()}
                />
                <DetailItem label="Scan Run" value={anomaly.scan_run_id.slice(0, 8) + '...'} />
              </div>
            </CardContent>
          </Card>

          {/* AI Explanation card */}
          <Card className="border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 shadow-none">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-sm">
                <Sparkles className="h-4 w-4 text-amber-500" />
                AI Analysis
              </CardTitle>
            </CardHeader>
            <CardContent>
              {anomaly.explanation ? (
                <div className="space-y-4">
                  <div>
                    <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
                      Root Cause
                    </h4>
                    <p className="text-sm text-slate-700 dark:text-slate-300">
                      {anomaly.explanation.root_cause}
                    </p>
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
                      Risk Assessment
                    </h4>
                    <p className="text-sm text-slate-700 dark:text-slate-300">
                      {anomaly.explanation.risk_assessment}
                    </p>
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
                      Recommended Actions
                    </h4>
                    <ul className="list-disc list-inside text-sm text-slate-700 dark:text-slate-300 space-y-1">
                      {anomaly.explanation.recommended_actions.map((action, i) => (
                        <li key={i}>{action}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              ) : anomaly.llm_explanation ? (
                <p className="text-sm text-slate-700 dark:text-slate-300 whitespace-pre-wrap">
                  {anomaly.llm_explanation}
                </p>
              ) : (
                <div className="text-center py-6">
                  <Sparkles className="h-8 w-8 text-slate-300 mx-auto mb-2" />
                  <p className="text-sm text-slate-500 mb-3">
                    AI analysis pending...
                  </p>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => explainMutation.mutate()}
                    disabled={explainMutation.isPending}
                  >
                    {explainMutation.isPending ? (
                      <>
                        <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                        Analyzing...
                      </>
                    ) : (
                      <>
                        <Sparkles className="h-3.5 w-3.5 mr-1.5" />
                        Request AI Analysis
                      </>
                    )}
                  </Button>
                  {explainMutation.isError && (
                    <p className="text-xs text-red-500 mt-2">
                      {explainMutation.error instanceof Error
                        ? explainMutation.error.message
                        : 'Failed to request analysis'}
                    </p>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right column */}
        <div className="space-y-4">
          {/* Assignment card */}
          <Card className="border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 shadow-none">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-sm">
                <User className="h-4 w-4 text-slate-500" />
                Assignment
              </CardTitle>
            </CardHeader>
            <CardContent>
              {anomaly.assigned_to && (
                <div className="mb-3">
                  <span className="text-xs text-slate-500">Currently assigned to</span>
                  <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
                    {anomaly.assigned_to}
                  </p>
                </div>
              )}
              <div className="flex gap-2">
                <Input
                  placeholder="Username..."
                  value={assignTo}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                    setAssignTo(e.target.value)
                  }
                  className="flex-1"
                />
                <Button
                  variant="outline"
                  size="default"
                  onClick={() => assignMutation.mutate()}
                  disabled={!assignTo.trim() || assignMutation.isPending}
                >
                  {assignMutation.isPending ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    'Assign'
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Resolution notes */}
          {(showResolutionNotes ||
            anomaly.status === 'RESOLVED' ||
            anomaly.status === 'FALSE_POSITIVE' ||
            anomaly.resolution_notes) && (
            <Card className="border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 shadow-none">
              <CardHeader>
                <CardTitle className="text-sm">Resolution Notes</CardTitle>
              </CardHeader>
              <CardContent>
                {anomaly.resolution_notes ? (
                  <p className="text-sm text-slate-700 dark:text-slate-300 whitespace-pre-wrap">
                    {anomaly.resolution_notes}
                  </p>
                ) : (
                  <div className="space-y-2">
                    <Textarea
                      placeholder="Add resolution notes..."
                      value={resolutionNotes}
                      onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
                        setResolutionNotes(e.target.value)
                      }
                      rows={4}
                    />
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        patchAnomaly(id, { resolution_notes: resolutionNotes }).then(
                          () => {
                            queryClient.invalidateQueries({ queryKey: ['anomaly', id] });
                          }
                        );
                      }}
                      disabled={!resolutionNotes.trim()}
                    >
                      Save Notes
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Timeline / Activity card */}
          <Card className="border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 shadow-none">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-sm">
                <Activity className="h-4 w-4 text-slate-500" />
                Activity
              </CardTitle>
            </CardHeader>
            <CardContent>
              {anomaly.timeline && anomaly.timeline.length > 0 ? (
                <div className="space-y-3">
                  {anomaly.timeline.map((entry) => (
                    <div key={entry.id} className="flex gap-3">
                      <div className="flex flex-col items-center">
                        <div className="h-2 w-2 rounded-full bg-slate-300 dark:bg-slate-600 mt-1.5" />
                        <div className="flex-1 w-px bg-slate-200 dark:bg-slate-700" />
                      </div>
                      <div className="pb-3">
                        <p className="text-xs font-medium text-slate-700 dark:text-slate-300">
                          {entry.action}
                        </p>
                        <p className="text-[11px] text-slate-500">
                          {entry.performed_by} &middot;{' '}
                          {new Date(entry.timestamp).toLocaleString()}
                        </p>
                        {entry.details && (
                          <p className="text-xs text-slate-500 mt-0.5">
                            {entry.details}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-4">
                  <Clock className="h-6 w-6 text-slate-300 mx-auto mb-1.5" />
                  <p className="text-xs text-slate-500">No activity recorded yet.</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

function DetailItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-[11px] font-medium text-slate-500 uppercase tracking-wide">
        {label}
      </dt>
      <dd className="text-sm text-slate-800 dark:text-slate-200 mt-0.5 font-mono">
        {value}
      </dd>
    </div>
  );
}
