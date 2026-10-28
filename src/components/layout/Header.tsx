// ============================================================
// Top Header Component
// ============================================================

import { useLocation, Link, useNavigate } from 'react-router-dom';
import { Menu, Bell, HelpCircle, LogOut, LogIn } from 'lucide-react';
import { useApp } from '@/context/AppContext';
import { useAuth } from '@/context/AuthContext';
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
  '/login': {
    title: 'Sign In',
    description: 'Access your account',
  },
};

function getPageMeta(pathname: string) {
  if (PAGE_METADATA[pathname]) return PAGE_METADATA[pathname];
  for (const [path, meta] of Object.entries(PAGE_METADATA)) {
    if (path !== '/' && pathname.startsWith(path)) return meta;
  }
  return { title: 'BrandProof AI', description: '' };
}

interface HeaderProps {
  onMobileMenuOpen: () => void;
}

export function Header({ onMobileMenuOpen }: HeaderProps) {
  const { sidebarCollapsed, addToast } = useApp();
  const { user, isAuthenticated, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const meta = getPageMeta(location.pathname);

  const handleLogout = async () => {
    await logout();
    addToast({
      title: 'Signed out',
      description: 'You have been signed out successfully.',
      variant: 'info',
    });
    navigate('/login');
  };

  const userInitial = user?.displayName
    ? user.displayName.charAt(0).toUpperCase()
    : user?.email
    ? user.email.charAt(0).toUpperCase()
    : 'U';

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

      {/* Right: utility actions and user account */}
      <div className="flex items-center gap-2 shrink-0">
        <button
          className="btn-ghost p-2 relative hidden sm:inline-flex"
          aria-label="Notifications"
          title="Notifications"
        >
          <Bell className="w-4.5 h-4.5 text-surface-500" />
        </button>
        <button
          className="btn-ghost p-2 hidden sm:inline-flex"
          aria-label="Help"
          title="Help"
        >
          <HelpCircle className="w-4.5 h-4.5 text-surface-500" />
        </button>

        {isAuthenticated && user ? (
          <div className="flex items-center gap-2 pl-2 border-l border-surface-200">
            {/* User display */}
            <div className="flex items-center gap-2">
              <div
                className="w-7 h-7 rounded-full bg-brand-600 flex items-center justify-center text-white text-xs font-semibold shadow-xs"
                title={user.email}
              >
                {userInitial}
              </div>
              <div className="hidden md:block text-left">
                <p className="text-xs font-medium text-surface-800 leading-none truncate max-w-[120px]">
                  {user.displayName || user.email.split('@')[0]}
                </p>
                <p className="text-[10px] text-surface-400 leading-none truncate max-w-[120px] mt-0.5">
                  {user.email}
                </p>
              </div>
            </div>

            {/* Logout button */}
            <button
              onClick={handleLogout}
              className="btn-ghost p-1.5 text-surface-500 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors ml-1"
              title="Sign out"
              aria-label="Sign out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <Link
            to="/login"
            className="btn-primary py-1.5 px-3 text-xs font-medium flex items-center gap-1.5"
          >
            <LogIn className="w-3.5 h-3.5" />
            <span>Sign In</span>
          </Link>
        )}
      </div>
    </header>
  );
}
