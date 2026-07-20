"use client";

import { create } from "zustand";

type DashboardUiStore = {
  isNavigationOpen: boolean;
  openNavigation: () => void;
  closeNavigation: () => void;
};

export const useDashboardUiStore = create<DashboardUiStore>((set) => ({
  isNavigationOpen: false,
  openNavigation: () => set({ isNavigationOpen: true }),
  closeNavigation: () => set({ isNavigationOpen: false }),
}));
