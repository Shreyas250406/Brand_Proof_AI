// ============================================================
// Application Sidebar Navigation
// ============================================================

import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  FileScan,
  History,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  Shield,
  X,
} from 'lucide-react';
import { useApp } from '@/context/AppContext';
import { DemoBanner } from '@/components/ui/DemoBanner';
import { cn } from '@/lib/utils';

interface NavItem {
  to: string;
  icon: React.ReactNode;
  label: string;
  exact?: boolean;
}

const NAV_ITEMS: NavItem[] = [
  {
    to: '/',
    icon: <LayoutDashboard className="w-4.5 h-4.5" />,
    label: 'Overview',
    exact: true,
  },
  {
    to: '/analyse',
    icon: <FileScan className="w-4.5 h-4.5" />,
    label: 'Upload & Analyse',
  },
  {
    to: '/history',
    icon: <History className="w-4.5 h-4.5" />,
    label: 'History',
  },
  {
    to: '/brand',
    icon: <BookOpen className="w-4.5 h-4.5" />,
    label: 'Brand Knowledge',
  },
];

interface SidebarProps {
  mobileOpen?: boolean;
  onMobileClose?: () => void;
}

export function Sidebar({ mobileOpen = false, onMobileClose }: SidebarProps) {
  const { sidebarCollapsed, setSidebarCollapsed } = useApp();
  const location = useLocation();

  const isActive = (item: NavItem) => {
    if (item.exact) return location.pathname === item.to;
    return location.pathname.startsWith(item.to);
  };

  return (
    <>
      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-30 lg:hidden"
          onClick={onMobileClose}
          aria-hidden="true"
        />
      )}

      {/* Sidebar panel */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-40 flex flex-col bg-navy-900 transition-all duration-200 ease-in-out',
          // Desktop: always visible, width toggles
          sidebarCollapsed ? 'lg:w-16' : 'lg:w-60',
          // Mobile: slide in/out
          mobileOpen ? 'translate-x-0 w-60' : '-translate-x-full lg:translate-x-0'
        )}
        aria-label="Primary navigation"
      >
        {/* Brand header */}
        <div className={cn(
          'flex items-center h-14 px-4 border-b border-navy-800 shrink-0',
          sidebarCollapsed ? 'lg:justify-center' : 'justify-between'
        )}>
          <div className={cn('flex items-center gap-2.5', sidebarCollapsed && 'lg:hidden')}>
            <div className="w-7 h-7 rounded-lg bg-brand-600 flex items-center justify-center shrink-0">
              <Shield className="w-4 h-4 text-white" />
            </div>
            <span className="text-sm font-bold text-white tracking-tight">BrandProof AI</span>
          </div>

          {/* Collapsed icon (desktop only) */}
          <div className={cn('hidden items-center justify-center', sidebarCollapsed && 'lg:flex')}>
            <div className="w-7 h-7 rounded-lg bg-brand-600 flex items-center justify-center">
              <Shield className="w-4 h-4 text-white" />
            </div>
          </div>

          {/* Mobile close */}
          <button
            onClick={onMobileClose}
            className="lg:hidden text-navy-300 hover:text-white p-1"
            aria-label="Close navigation"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation links */}
        <nav className="flex-1 px-2 py-4 space-y-0.5 overflow-y-auto" aria-label="Main menu">
          {NAV_ITEMS.map(item => {
            const active = isActive(item);
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.exact}
                onClick={onMobileClose}
                title={sidebarCollapsed ? item.label : undefined}
                className={cn(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors duration-150',
                  active
                    ? 'bg-navy-700 text-white'
                    : 'text-navy-200 hover:bg-navy-800 hover:text-white',
                  sidebarCollapsed && 'lg:justify-center lg:px-2'
                )}
                aria-current={active ? 'page' : undefined}
              >
                <span className="shrink-0">{item.icon}</span>
                <span className={cn('truncate', sidebarCollapsed && 'lg:hidden')}>
                  {item.label}
                </span>
              </NavLink>
            );
          })}
        </nav>

        {/* Demo indicator */}
        <div className={cn(
          'px-3 pb-3',
          sidebarCollapsed && 'lg:hidden'
        )}>
          <DemoBanner />
        </div>

        {/* Collapse toggle (desktop only) */}
        <button
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          className="hidden lg:flex items-center justify-center h-10 border-t border-navy-800 text-navy-400 hover:text-white hover:bg-navy-800 transition-colors shrink-0"
          aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {sidebarCollapsed
            ? <ChevronRight className="w-4 h-4" />
            : <ChevronLeft className="w-4 h-4" />
          }
        </button>
      </aside>
    </>
  );
}
