import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Settings, Server, KeyRound, Bell } from "lucide-react";

const SETTING_GROUPS = [
  {
    title: "API Connection",
    icon: Server,
    description: "Configure the Python sidecar API endpoint.",
    placeholder: true,
  },
  {
    title: "Authentication",
    icon: KeyRound,
    description: "SAP user credentials and session management.",
    placeholder: true,
  },
  {
    title: "Notifications",
    icon: Bell,
    description: "Alert thresholds and notification preferences.",
    placeholder: true,
  },
];

export default function SettingsPage() {
  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
          Settings
        </h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Platform configuration and preferences.
        </p>
      </div>

      <div className="space-y-4">
        {SETTING_GROUPS.map((group, i) => {
          const Icon = group.icon;
          return (
            <Card
              key={group.title}
              className="border-slate-200 dark:border-slate-800 shadow-none"
            >
              <CardHeader className="flex flex-row items-center gap-3 pb-2 pt-4 px-4">
                <div className="flex h-8 w-8 items-center justify-center rounded-md border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900">
                  <Icon className="h-4 w-4 text-slate-500" />
                </div>
                <CardTitle className="text-sm font-medium text-slate-800 dark:text-slate-200">
                  {group.title}
                </CardTitle>
              </CardHeader>
              {i < SETTING_GROUPS.length - 1 && (
                <Separator className="bg-slate-100 dark:bg-slate-800" />
              )}
              <CardContent className="px-4 pb-4 pt-3">
                <p className="text-xs text-slate-400 dark:text-slate-500">
                  {group.description}
                </p>
                {group.placeholder && (
                  <p className="mt-2 text-xs text-slate-300 dark:text-slate-600 italic">
                    Configuration UI coming in a future phase.
                  </p>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      <div className="flex items-center gap-2 text-xs text-slate-400">
        <Settings className="h-3 w-3" />
        <span>SAP Anomaly Detective — v0.1.0</span>
      </div>
    </div>
  );
}
