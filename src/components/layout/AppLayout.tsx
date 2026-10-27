// ============================================================
// Application Layout Shell
// ============================================================

import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { ToastContainer } from '@/components/ui/Toast';
import { useApp } from '@/context/AppContext';
import { cn } from '@/lib/utils';

export function AppLayout() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { sidebarCollapsed } = useApp();

  return (
    <div className="min-h-screen bg-surface-50">
      <Sidebar
        mobileOpen={mobileMenuOpen}
        onMobileClose={() => setMobileMenuOpen(false)}
      />
      <Header onMobileMenuOpen={() => setMobileMenuOpen(true)} />

      {/* Main content area — offset for sidebar and header */}
      <main
        className={cn(
          'pt-14 min-h-screen transition-all duration-200',
          sidebarCollapsed ? 'lg:pl-16' : 'lg:pl-60'
        )}
      >
        <div className="max-w-[1400px] mx-auto px-4 sm:px-6 py-6">
          <Outlet />
        </div>
      </main>

      <ToastContainer />
    </div>
  );
}
