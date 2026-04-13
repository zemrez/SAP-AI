import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  ShieldAlert,
  AlertTriangle,
  Clock,
  CheckCircle2,
} from "lucide-react";

const STATS = [
  {
    title: "Total Anomalies",
    value: "—",
    description: "Across all company codes",
    icon: ShieldAlert,
    iconClass: "text-slate-500",
  },
  {
    title: "Critical Alerts",
    value: "—",
    description: "Require immediate review",
    icon: AlertTriangle,
    iconClass: "text-red-500",
  },
  {
    title: "Last Scan",
    value: "—",
    description: "No scans run yet",
    icon: Clock,
    iconClass: "text-slate-500",
  },
  {
    title: "System Status",
    value: "Online",
    description: "Backend connected",
    icon: CheckCircle2,
    iconClass: "text-emerald-500",
    badge: { label: "OK", variant: "outline" as const },
  },
];

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
          Overview
        </h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Financial anomaly detection status across your SAP landscape.
        </p>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {STATS.map((stat) => {
          const Icon = stat.icon;
          return (
            <Card
              key={stat.title}
              className="border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 shadow-none"
            >
              <CardHeader className="flex flex-row items-center justify-between pb-2 pt-4 px-4">
                <CardTitle className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                  {stat.title}
                </CardTitle>
                <Icon className={`h-4 w-4 ${stat.iconClass}`} />
              </CardHeader>
              <CardContent className="px-4 pb-4">
                <div className="flex items-end gap-2">
                  <span className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                    {stat.value}
                  </span>
                  {stat.badge && (
                    <Badge variant={stat.badge.variant} className="mb-0.5 text-xs">
                      {stat.badge.label}
                    </Badge>
                  )}
                </div>
                <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
                  {stat.description}
                </p>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Placeholder modules section */}
      <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 p-6">
        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">
          Available Modules
        </h3>
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900">
            <ShieldAlert className="h-4 w-4 text-slate-500" />
          </div>
          <div>
            <p className="text-sm font-medium text-slate-800 dark:text-slate-200">
              Anomaly Detective
            </p>
            <p className="text-xs text-slate-400 dark:text-slate-500">
              Detects financial anomalies in SAP ERP transactions
            </p>
          </div>
          <Badge variant="outline" className="ml-auto text-xs text-slate-400">
            Phase 3
          </Badge>
        </div>
      </div>
    </div>
  );
}
