// ============================================================
// Top Header Component
// ============================================================

import { useLocation } from 'react-router-dom';
import { Menu, Bell, HelpCircle } from 'lucide-react';
import { useApp } from '@/context/AppContext';
import { cn } from '@/lib/utils';

const PAGE_METADATA: Record<string, { title: string; description: string }> = {
  '/': {
    title: 'Overview',
    description: 'Your content quality dashboard',
  },
  '/analyse': {
    title: 'Upload & Analyse',
    description: 'Submit content for brand quality review',
  },
  '/review': {
    title: 'Analysis Review',
    description: 'Review findings, apply corrections and provide feedback',
  },
  '/history': {
    title: 'Analysis History',
    description: 'Browse and reopen previous content analyses',
  },
  '/brand': {
    title: 'Brand Knowledge',
    description: 'Manage your brand guidelines and terminology',
  },
};

function getPageMeta(pathname: string) {
  // Exact match first
  if (PAGE_METADATA[pathname]) return PAGE_METADATA[pathname];
  // Prefix match
  for (const [path, meta] of Object.entries(PAGE_METADATA)) {
    if (path !== '/' && pathname.startsWith(path)) return meta;
  }
  return { title: 'BrandProof AI', description: '' };
}

interface HeaderProps {
  onMobileMenuOpen: () => void;
}

export function Header({ onMobileMenuOpen }: HeaderProps) {
  const { sidebarCollapsed } = useApp();
  const location = useLocation();
  const meta = getPageMeta(location.pathname);

  return (
    <header
      className={cn(
        'fixed top-0 right-0 z-20 h-14 bg-white border-b border-surface-200',
        'flex items-center justify-between px-4 gap-4 transition-all duration-200',
        sidebarCollapsed ? 'lg:left-16' : 'lg:left-60',
        'left-0'
      )}
    >
      {/* Left: mobile menu + page title */}
      <div className="flex items-center gap-3 min-w-0">
        <button
          onClick={onMobileMenuOpen}
          className="lg:hidden btn-ghost p-2 -ml-1"
          aria-label="Open navigation menu"
        >
          <Menu className="w-5 h-5" />
        </button>
        <div className="min-w-0">
          <h1 className="text-sm font-semibold text-surface-900 truncate leading-tight">
            {meta.title}
          </h1>
          {meta.description && (
            <p className="text-xs text-surface-400 truncate leading-tight hidden sm:block">
              {meta.description}
            </p>
          )}
        </div>
      </div>

      {/* Right: utility actions */}
      <div className="flex items-center gap-1 shrink-0">
        <button
          className="btn-ghost p-2 relative"
          aria-label="Notifications"
          title="Notifications"
        >
          <Bell className="w-4.5 h-4.5 text-surface-500" />
        </button>
        <button
          className="btn-ghost p-2"
          aria-label="Help"
          title="Help"
        >
          <HelpCircle className="w-4.5 h-4.5 text-surface-500" />
        </button>

        {/* Simple user avatar placeholder */}
        <div
          className="w-7 h-7 rounded-full bg-navy-600 flex items-center justify-center ml-1 cursor-pointer"
          aria-label="User account"
          title="User account"
          role="button"
          tabIndex={0}
        >
          <span className="text-xs font-semibold text-white">B</span>
        </div>
      </div>
    </header>
  );
}
