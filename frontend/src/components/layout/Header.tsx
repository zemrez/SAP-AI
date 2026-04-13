'use client';

import { usePathname } from 'next/navigation';
import { Bell, ChevronRight, User } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

function buildBreadcrumbs(pathname: string): { label: string; href: string }[] {
  const parts = pathname.split('/').filter(Boolean);
  const crumbs = [{ label: 'Home', href: '/' }];

  const labels: Record<string, string> = {
    'anomaly-detective': 'Anomaly Detective',
    scans: 'Scans',
    trends: 'Trends',
    settings: 'Settings',
  };

  let path = '';
  for (const part of parts) {
    path += `/${part}`;
    crumbs.push({ label: labels[part] ?? part, href: path });
  }

  return crumbs;
}

function buildPageTitle(pathname: string): string {
  const segments = pathname.split('/').filter(Boolean);
  if (segments.length === 0) return 'Dashboard';

  const labels: Record<string, string> = {
    'anomaly-detective': 'Anomaly Detective',
    scans: 'Scans',
    trends: 'Trends',
    settings: 'Settings',
  };

  const last = segments[segments.length - 1];
  return labels[last] ?? last;
}

export function Header() {
  const pathname = usePathname();
  const breadcrumbs = buildBreadcrumbs(pathname);
  const pageTitle = buildPageTitle(pathname);

  return (
    <header className="flex h-14 items-center justify-between border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 px-4">
      {/* Left: title + breadcrumbs */}
      <div>
        <h1 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
          {pageTitle}
        </h1>
        <nav className="flex items-center gap-1 text-xs text-slate-400 dark:text-slate-500 mt-0.5">
          {breadcrumbs.map((crumb, i) => (
            <span key={crumb.href} className="flex items-center gap-1">
              {i > 0 && <ChevronRight className="h-3 w-3" />}
              <span
                className={
                  i === breadcrumbs.length - 1
                    ? 'text-slate-600 dark:text-slate-300'
                    : ''
                }
              >
                {crumb.label}
              </span>
            </span>
          ))}
        </nav>
      </div>

      {/* Right: notification bell + user menu */}
      <div className="flex items-center gap-2">
        <button
          className="flex h-8 w-8 items-center justify-center rounded border border-transparent text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          aria-label="Notifications"
        >
          <Bell className="h-4 w-4" />
        </button>

        <DropdownMenu>
          <DropdownMenuTrigger
            className="flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            aria-label="User menu"
          >
            <User className="h-4 w-4" />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-40">
            <DropdownMenuLabel className="text-xs font-medium text-slate-500">
              SAP User
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem>Profile</DropdownMenuItem>
            <DropdownMenuItem>Sign Out</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
