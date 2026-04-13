'use client';

import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import {
  ShieldAlert,
  Search,
  ChevronUp,
  ChevronDown,
  ChevronsUpDown,
  ChevronLeft,
  ChevronRight,
  Loader2,
  AlertTriangle,
  Eye,
  CheckCircle2,
  XCircle,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from '@/components/ui/dropdown-menu';
import { RiskScoreBadge } from '@/components/anomaly-detective/RiskScoreBadge';
import { listAnomalies, patchAnomaliesBulk } from '@/lib/api';
import type {
  AnomalySeverity,
  AnomalyStatus,
  SortDirection,
} from '@/lib/types';

const SEVERITY_OPTIONS: Array<{ label: string; value: AnomalySeverity | '' }> = [
  { label: 'All Severities', value: '' },
  { label: 'Critical', value: 'CRITICAL' },
  { label: 'High', value: 'HIGH' },
  { label: 'Medium', value: 'MEDIUM' },
  { label: 'Low', value: 'LOW' },
];

const STATUS_OPTIONS: Array<{ label: string; value: AnomalyStatus | '' }> = [
  { label: 'All Statuses', value: '' },
  { label: 'Open', value: 'OPEN' },
  { label: 'Investigating', value: 'INVESTIGATING' },
  { label: 'Resolved', value: 'RESOLVED' },
  { label: 'False Positive', value: 'FALSE_POSITIVE' },
];

const PAGE_SIZES = [10, 25, 50];

function severityVariant(severity: AnomalySeverity) {
  switch (severity) {
    case 'CRITICAL':
      return 'destructive' as const;
    case 'HIGH':
      return 'destructive' as const;
    case 'MEDIUM':
      return 'secondary' as const;
    case 'LOW':
      return 'outline' as const;
    default:
      return 'outline' as const;
  }
}

function severityColor(severity: AnomalySeverity) {
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

function statusColor(status: AnomalyStatus) {
  switch (status) {
    case 'OPEN':
      return 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400';
    case 'INVESTIGATING':
      return 'bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400';
    case 'RESOLVED':
      return 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400';
    case 'FALSE_POSITIVE':
      return 'bg-slate-50 text-slate-600 dark:bg-slate-900/20 dark:text-slate-400';
  }
}

type SortField = 'risk_score' | 'amount' | 'detected_at';

export default function AnomalyDetectivePage() {
  const router = useRouter();
  const queryClient = useQueryClient();

  // Filter state
  const [severity, setSeverity] = useState<AnomalySeverity | ''>('');
  const [status, setStatus] = useState<AnomalyStatus | ''>('');
  const [search, setSearch] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  // Sort state
  const [sortField, setSortField] = useState<SortField>('detected_at');
  const [sortDir, setSortDir] = useState<SortDirection>('desc');

  // Pagination
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);

  // Selection
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const queryParams = {
    page,
    page_size: pageSize,
    severity: severity || undefined,
    status: status || undefined,
    search: search || undefined,
    sort_by: sortField,
    sort_dir: sortDir,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
  };

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['anomalies', queryParams],
    queryFn: () => listAnomalies(queryParams),
  });

  const bulkMutation = useMutation({
    mutationFn: (params: { ids: string[]; status: AnomalyStatus }) =>
      patchAnomaliesBulk(params.ids, { status: params.status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['anomalies'] });
      setSelectedIds(new Set());
    },
  });

  const handleSort = useCallback(
    (field: SortField) => {
      if (sortField === field) {
        setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
      } else {
        setSortField(field);
        setSortDir('desc');
      }
      setPage(1);
    },
    [sortField]
  );

  const toggleSelectAll = useCallback(() => {
    if (!data) return;
    const allIds = data.items.map((a) => a.id);
    const allSelected = allIds.every((id) => selectedIds.has(id));
    if (allSelected) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(allIds));
    }
  }, [data, selectedIds]);

  const toggleSelect = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const handleBulkAction = useCallback(
    (newStatus: AnomalyStatus) => {
      if (selectedIds.size === 0) return;
      bulkMutation.mutate({ ids: Array.from(selectedIds), status: newStatus });
    },
    [selectedIds, bulkMutation]
  );

  function SortIcon({ field }: { field: SortField }) {
    if (sortField !== field) return <ChevronsUpDown className="h-3 w-3 text-slate-400" />;
    return sortDir === 'asc' ? (
      <ChevronUp className="h-3 w-3" />
    ) : (
      <ChevronDown className="h-3 w-3" />
    );
  }

  const totalPages = data?.pages ?? 0;
  const allOnPageSelected =
    data && data.items.length > 0 && data.items.every((a) => selectedIds.has(a.id));

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
            Anomaly Detective
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Detected financial anomalies across your SAP landscape.
          </p>
        </div>
        {data && (
          <Badge variant="outline" className="text-xs">
            {data.total} anomalies
          </Badge>
        )}
      </div>

      {/* Filters */}
      <Card className="border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 shadow-none">
        <CardContent className="pt-4">
          <div className="flex flex-wrap items-end gap-3">
            {/* Search */}
            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
                <Input
                  placeholder="Search document number, description..."
                  value={search}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                    setSearch(e.target.value);
                    setPage(1);
                  }}
                  className="pl-8"
                />
              </div>
            </div>

            {/* Severity */}
            <Select
              value={severity}
              onValueChange={(val: string | null) => {
                setSeverity((val ?? '') as AnomalySeverity | '');
                setPage(1);
              }}
            >
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="All Severities" />
              </SelectTrigger>
              <SelectContent>
                {SEVERITY_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {/* Status */}
            <Select
              value={status}
              onValueChange={(val: string | null) => {
                setStatus((val ?? '') as AnomalyStatus | '');
                setPage(1);
              }}
            >
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="All Statuses" />
              </SelectTrigger>
              <SelectContent>
                {STATUS_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {/* Date From */}
            <Input
              type="date"
              value={dateFrom}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                setDateFrom(e.target.value);
                setPage(1);
              }}
              className="w-[150px]"
              placeholder="Date from"
            />

            {/* Date To */}
            <Input
              type="date"
              value={dateTo}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                setDateTo(e.target.value);
                setPage(1);
              }}
              className="w-[150px]"
              placeholder="Date to"
            />
          </div>
        </CardContent>
      </Card>

      {/* Bulk actions bar */}
      {selectedIds.size > 0 && (
        <div className="flex items-center gap-3 rounded-lg border border-blue-200 bg-blue-50 dark:border-blue-900 dark:bg-blue-950/30 px-4 py-2">
          <span className="text-sm font-medium text-blue-700 dark:text-blue-400">
            {selectedIds.size} selected
          </span>
          <div className="flex gap-2 ml-auto">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleBulkAction('INVESTIGATING')}
              disabled={bulkMutation.isPending}
            >
              <Eye className="h-3.5 w-3.5 mr-1" />
              Mark Investigating
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleBulkAction('RESOLVED')}
              disabled={bulkMutation.isPending}
            >
              <CheckCircle2 className="h-3.5 w-3.5 mr-1" />
              Mark Resolved
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleBulkAction('FALSE_POSITIVE')}
              disabled={bulkMutation.isPending}
            >
              <XCircle className="h-3.5 w-3.5 mr-1" />
              False Positive
            </Button>
          </div>
        </div>
      )}

      {/* Table */}
      <Card className="border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 shadow-none">
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-4 space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="flex items-center gap-4">
                  <Skeleton className="h-8 w-8 rounded-full" />
                  <Skeleton className="h-4 flex-1" />
                  <Skeleton className="h-4 w-20" />
                  <Skeleton className="h-4 w-24" />
                </div>
              ))}
            </div>
          ) : isError ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <AlertTriangle className="h-8 w-8 text-red-400 mb-3" />
              <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
                Failed to load anomalies
              </p>
              <p className="text-xs text-slate-500 mt-1">
                {error instanceof Error ? error.message : 'Unknown error'}
              </p>
            </div>
          ) : data && data.items.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <div className="flex h-14 w-14 items-center justify-center rounded-full border-2 border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 mb-3">
                <ShieldAlert className="h-6 w-6 text-slate-400" />
              </div>
              <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
                No anomalies found
              </p>
              <p className="text-xs text-slate-500 mt-1">
                Try adjusting your filters or run a new scan.
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="border-slate-200 dark:border-slate-800">
                  <TableHead className="w-10">
                    <Checkbox
                      checked={allOnPageSelected ?? false}
                      onCheckedChange={toggleSelectAll}
                    />
                  </TableHead>
                  <TableHead className="w-16">
                    <button
                      onClick={() => handleSort('risk_score')}
                      className="flex items-center gap-1 text-xs font-medium"
                    >
                      Risk <SortIcon field="risk_score" />
                    </button>
                  </TableHead>
                  <TableHead>Severity</TableHead>
                  <TableHead>Document No.</TableHead>
                  <TableHead>Company Code</TableHead>
                  <TableHead>
                    <button
                      onClick={() => handleSort('amount')}
                      className="flex items-center gap-1 text-xs font-medium"
                    >
                      Amount <SortIcon field="amount" />
                    </button>
                  </TableHead>
                  <TableHead>Detector</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>
                    <button
                      onClick={() => handleSort('detected_at')}
                      className="flex items-center gap-1 text-xs font-medium"
                    >
                      Date <SortIcon field="detected_at" />
                    </button>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.items.map((anomaly) => (
                  <TableRow
                    key={anomaly.id}
                    className="cursor-pointer border-slate-100 dark:border-slate-800/50 hover:bg-slate-50 dark:hover:bg-slate-900/50"
                    onClick={() => router.push(`/anomaly-detective/detail?id=${anomaly.id}`)}
                  >
                    <TableCell onClick={(e: React.MouseEvent) => e.stopPropagation()}>
                      <Checkbox
                        checked={selectedIds.has(anomaly.id)}
                        onCheckedChange={() => toggleSelect(anomaly.id)}
                      />
                    </TableCell>
                    <TableCell>
                      <RiskScoreBadge score={anomaly.risk_score} size="sm" />
                    </TableCell>
                    <TableCell>
                      <span
                        className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ${severityColor(anomaly.severity)}`}
                      >
                        {anomaly.severity}
                      </span>
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {anomaly.document_number ?? '—'}
                    </TableCell>
                    <TableCell className="text-xs">{anomaly.company_code}</TableCell>
                    <TableCell className="font-mono text-xs">
                      {anomaly.amount != null
                        ? `${anomaly.amount.toLocaleString()} ${anomaly.currency ?? ''}`
                        : '—'}
                    </TableCell>
                    <TableCell className="text-xs">{anomaly.rule_name}</TableCell>
                    <TableCell>
                      <span
                        className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ${statusColor(anomaly.status)}`}
                      >
                        {anomaly.status.replace('_', ' ')}
                      </span>
                    </TableCell>
                    <TableCell className="text-xs text-slate-500">
                      {new Date(anomaly.detected_at).toLocaleDateString()}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Pagination */}
      {data && data.total > 0 && (
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500">Rows per page</span>
            <Select
              value={String(pageSize)}
              onValueChange={(val: string | null) => {
                if (!val) return;
                setPageSize(Number(val));
                setPage(1);
              }}
            >
              <SelectTrigger size="sm" className="w-[70px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PAGE_SIZES.map((size) => (
                  <SelectItem key={size} value={String(size)}>
                    {size}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500">
              Page {data.page} of {totalPages}
            </span>
            <Button
              variant="outline"
              size="icon-sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              <ChevronLeft className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="outline"
              size="icon-sm"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              <ChevronRight className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
