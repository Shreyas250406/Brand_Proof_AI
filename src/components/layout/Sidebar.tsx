// ============================================================
// Application Sidebar Navigation
// ============================================================

import { NavLink, useLocation, Link, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  FileScan,
  History,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  Shield,
  X,
  LogOut,
  LogIn,
} from 'lucide-react';
import { useApp } from '@/context/AppContext';
import { useAuth } from '@/context/AuthContext';
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
  const { sidebarCollapsed, setSidebarCollapsed, addToast } = useApp();
  const { user, isAuthenticated, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    addToast({
      title: 'Signed out',
      description: 'You have been signed out successfully.',
      variant: 'info',
    });
    navigate('/login');
  };

  const isActive = (item: NavItem) => {
    if (item.exact) return location.pathname === item.to;
    return location.pathname.startsWith(item.to);
  };

  const userInitial = user?.displayName
    ? user.displayName.charAt(0).toUpperCase()
    : user?.email
    ? user.email.charAt(0).toUpperCase()
    : 'U';

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
          sidebarCollapsed ? 'lg:w-16' : 'lg:w-60',
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

        {/* User Account / Sign In section */}
        <div className={cn('p-3 border-t border-navy-800 shrink-0')}>
          {isAuthenticated && user ? (
            <div className={cn('flex items-center gap-2.5', sidebarCollapsed && 'lg:justify-center')}>
              <div
                className="w-8 h-8 rounded-full bg-brand-600 text-white flex items-center justify-center text-xs font-bold shrink-0 shadow-xs"
                title={user.email}
              >
                {userInitial}
              </div>
              <div className={cn('flex-1 min-w-0', sidebarCollapsed && 'lg:hidden')}>
                <p className="text-xs font-semibold text-white truncate">
                  {user.displayName || user.email.split('@')[0]}
                </p>
                <p className="text-[11px] text-navy-400 truncate">
                  {user.email}
                </p>
              </div>
              <button
                onClick={handleLogout}
                className={cn(
                  'text-navy-400 hover:text-red-400 p-1.5 rounded-md hover:bg-navy-800 transition-colors',
                  sidebarCollapsed && 'lg:hidden'
                )}
                title="Sign out"
                aria-label="Sign out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <Link
              to="/login"
              className={cn(
                'flex items-center gap-2.5 w-full py-2 px-3 rounded-lg text-xs font-medium bg-brand-600 hover:bg-brand-500 text-white transition-colors',
                sidebarCollapsed && 'lg:justify-center lg:px-2'
              )}
            >
              <LogIn className="w-4 h-4 shrink-0" />
              <span className={cn('truncate', sidebarCollapsed && 'lg:hidden')}>
                Sign In
              </span>
            </Link>
          )}
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
