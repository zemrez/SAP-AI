'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import {
  Plus,
  ScanLine,
  Loader2,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  ExternalLink,
} from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogTrigger,
  DialogClose,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { listScanRuns, triggerScan } from '@/lib/api';
import type { ScanStatus, ScanType, ScanRun } from '@/lib/types';

function scanStatusBadge(status: ScanStatus) {
  switch (status) {
    case 'PENDING':
      return (
        <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400">
          PENDING
        </span>
      );
    case 'RUNNING':
      return (
        <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 animate-pulse">
          <Loader2 className="h-3 w-3 animate-spin" />
          RUNNING
        </span>
      );
    case 'COMPLETED':
      return (
        <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
          DONE
        </span>
      );
    case 'FAILED':
      return (
        <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">
          FAILED
        </span>
      );
  }
}

export default function ScansPage() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // New scan form
  const [companyCode, setCompanyCode] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [scanType, setScanType] = useState<ScanType>('FULL');

  // Check if any scan is running to auto-refresh
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['scans'],
    queryFn: () => listScanRuns({ page: 1, page_size: 50 }),
    refetchInterval: (query) => {
      const scans = query.state.data;
      if (scans?.items.some((s: ScanRun) => s.status === 'RUNNING' || s.status === 'PENDING')) {
        return 5000;
      }
      return false;
    },
  });

  const triggerMutation = useMutation({
    mutationFn: () =>
      triggerScan({
        company_code: companyCode,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        scan_type: scanType,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scans'] });
      setDialogOpen(false);
      setCompanyCode('');
      setDateFrom('');
      setDateTo('');
      setScanType('FULL');
    },
  });

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
            Scan Management
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Trigger and monitor anomaly detection scans.
          </p>
        </div>

        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger
            render={
              <Button>
                <Plus className="h-4 w-4 mr-1.5" />
                New Scan
              </Button>
            }
          />
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Trigger New Scan</DialogTitle>
              <DialogDescription>
                Run anomaly detection against SAP financial data.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div className="space-y-1.5">
                <Label htmlFor="company-code">
                  Company Code <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="company-code"
                  placeholder="e.g. 1000"
                  value={companyCode}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                    setCompanyCode(e.target.value)
                  }
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label htmlFor="date-from">Date From</Label>
                  <Input
                    id="date-from"
                    type="date"
                    value={dateFrom}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                      setDateFrom(e.target.value)
                    }
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="date-to">Date To</Label>
                  <Input
                    id="date-to"
                    type="date"
                    value={dateTo}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                      setDateTo(e.target.value)
                    }
                  />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label>Scan Type</Label>
                <Select
                  value={scanType}
                  onValueChange={(val: string | null) => { if (val) setScanType(val as ScanType); }}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="FULL">Full Scan</SelectItem>
                    <SelectItem value="INCREMENTAL">Incremental</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              {triggerMutation.isError && (
                <p className="text-xs text-red-500">
                  {triggerMutation.error instanceof Error
                    ? triggerMutation.error.message
                    : 'Failed to trigger scan'}
                </p>
              )}
            </div>
            <DialogFooter>
              <DialogClose render={<Button variant="outline">Cancel</Button>} />
              <Button
                onClick={() => triggerMutation.mutate()}
                disabled={!companyCode.trim() || triggerMutation.isPending}
              >
                {triggerMutation.isPending ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                    Starting...
                  </>
                ) : (
                  <>
                    <ScanLine className="h-3.5 w-3.5 mr-1.5" />
                    Start Scan
                  </>
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Scans table */}
      <Card className="border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 shadow-none">
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-4 space-y-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="flex items-center gap-4">
                  <Skeleton className="h-4 w-20" />
                  <Skeleton className="h-4 flex-1" />
                  <Skeleton className="h-5 w-16 rounded-full" />
                  <Skeleton className="h-4 w-24" />
                </div>
              ))}
            </div>
          ) : isError ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <AlertTriangle className="h-8 w-8 text-red-400 mb-3" />
              <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
                Failed to load scans
              </p>
              <p className="text-xs text-slate-500 mt-1">
                {error instanceof Error ? error.message : 'Unknown error'}
              </p>
            </div>
          ) : data && data.items.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <div className="flex h-14 w-14 items-center justify-center rounded-full border-2 border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 mb-3">
                <ScanLine className="h-6 w-6 text-slate-400" />
              </div>
              <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
                No scans yet
              </p>
              <p className="text-xs text-slate-500 mt-1">
                Click &quot;New Scan&quot; to start your first anomaly detection run.
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="border-slate-200 dark:border-slate-800">
                  <TableHead className="w-8" />
                  <TableHead>Scan ID</TableHead>
                  <TableHead>Company Code</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Fiscal Year</TableHead>
                  <TableHead>Anomalies</TableHead>
                  <TableHead>Started By</TableHead>
                  <TableHead>Started At</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.items.map((scan) => {
                  const isExpanded = expandedId === scan.id;
                  return (
                    <ScanRow
                      key={scan.id}
                      scan={scan}
                      isExpanded={isExpanded}
                      onToggle={() =>
                        setExpandedId(isExpanded ? null : scan.id)
                      }
                      onViewAnomalies={() =>
                        router.push(
                          `/anomaly-detective?scan_run_id=${scan.id}`
                        )
                      }
                    />
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function ScanRow({
  scan,
  isExpanded,
  onToggle,
  onViewAnomalies,
}: {
  scan: ScanRun;
  isExpanded: boolean;
  onToggle: () => void;
  onViewAnomalies: () => void;
}) {
  return (
    <>
      <TableRow
        className="cursor-pointer border-slate-100 dark:border-slate-800/50 hover:bg-slate-50 dark:hover:bg-slate-900/50"
        onClick={onToggle}
      >
        <TableCell>
          {isExpanded ? (
            <ChevronDown className="h-3.5 w-3.5 text-slate-500" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5 text-slate-500" />
          )}
        </TableCell>
        <TableCell className="font-mono text-xs">
          {scan.id.slice(0, 8)}...
        </TableCell>
        <TableCell className="text-xs font-medium">{scan.company_code}</TableCell>
        <TableCell>
          <Badge variant="outline" className="text-[11px]">
            {scan.fiscal_period ? 'INCREMENTAL' : 'FULL'}
          </Badge>
        </TableCell>
        <TableCell>{scanStatusBadge(scan.status)}</TableCell>
        <TableCell className="text-xs">{scan.fiscal_year}</TableCell>
        <TableCell>
          <span className="text-xs font-medium">
            {scan.anomaly_count}
          </span>
        </TableCell>
        <TableCell className="text-xs text-slate-500">{scan.triggered_by}</TableCell>
        <TableCell className="text-xs text-slate-500">
          {new Date(scan.started_at).toLocaleString()}
        </TableCell>
      </TableRow>

      {isExpanded && (
        <TableRow className="bg-slate-50/50 dark:bg-slate-900/30">
          <TableCell colSpan={9}>
            <div className="py-2 px-4 space-y-2">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                <div>
                  <span className="text-slate-500">Full Scan ID</span>
                  <p className="font-mono text-slate-700 dark:text-slate-300">
                    {scan.id}
                  </p>
                </div>
                <div>
                  <span className="text-slate-500">Completed At</span>
                  <p className="text-slate-700 dark:text-slate-300">
                    {scan.completed_at
                      ? new Date(scan.completed_at).toLocaleString()
                      : '—'}
                  </p>
                </div>
                <div>
                  <span className="text-slate-500">Duration</span>
                  <p className="text-slate-700 dark:text-slate-300">
                    {scan.completed_at && scan.started_at
                      ? formatDuration(
                          new Date(scan.completed_at).getTime() -
                            new Date(scan.started_at).getTime()
                        )
                      : '—'}
                  </p>
                </div>
                <div>
                  <span className="text-slate-500">Anomalies Found</span>
                  <p className="font-medium text-slate-700 dark:text-slate-300">
                    {scan.anomaly_count}
                  </p>
                </div>
              </div>
              {scan.error_message && (
                <div className="rounded-md bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900 p-2 text-xs text-red-700 dark:text-red-400">
                  {scan.error_message}
                </div>
              )}
              {scan.anomaly_count > 0 && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={(e: React.MouseEvent) => {
                    e.stopPropagation();
                    onViewAnomalies();
                  }}
                >
                  <ExternalLink className="h-3 w-3 mr-1.5" />
                  View Anomalies
                </Button>
              )}
            </div>
          </TableCell>
        </TableRow>
      )}
    </>
  );
}

function formatDuration(ms: number): string {
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  if (minutes < 60) return `${minutes}m ${remainingSeconds}s`;
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return `${hours}h ${remainingMinutes}m`;
}
