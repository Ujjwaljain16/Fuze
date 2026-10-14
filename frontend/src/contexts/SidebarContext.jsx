/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useCallback } from 'react';
import { isMobileWidth } from '../utils/breakpoints';

const SidebarContext = createContext(null);

export function SidebarProvider({ children }) {
  const [isOpen, setIsOpen] = useState(() => {
    // On a phone "open" means a drawer covering the whole screen, so it always starts closed there (it used to start
    // open for every new visitor and on every load until closed). On a desktop the choice persists across refreshes.
    if (isMobileWidth()) return false;
    return localStorage.getItem('sidebar_open') !== 'false';
  });
  const [isCollapsed, setIsCollapsed] = useState(() => {
    return localStorage.getItem('sidebar_collapsed') === 'true';
  });

  const toggle = useCallback(() => {
    setIsOpen(prev => {
      const next = !prev;
      localStorage.setItem('sidebar_open', String(next));
      return next;
    });
  }, []);

  const collapse = useCallback(() => {
    setIsCollapsed(prev => {
      const next = !prev;
      localStorage.setItem('sidebar_collapsed', String(next));
      return next;
    });
  }, []);

  // Update setCollapsed for direct control if needed
  const setCollapsed = useCallback((value) => {
    setIsCollapsed(value);
    localStorage.setItem('sidebar_collapsed', String(value));
  }, []);

  const setOpen = useCallback((value) => {
    setIsOpen(value);
    localStorage.setItem('sidebar_open', String(value));
  }, []);

  return (
    <SidebarContext.Provider value={{ isOpen, isCollapsed, toggle, collapse, setCollapsed, setOpen }}>
      {children}
    </SidebarContext.Provider>
  );
}

export function useSidebar() {
  const ctx = useContext(SidebarContext);
  if (!ctx) throw new Error('useSidebar must be inside SidebarProvider');
  return ctx;
}
