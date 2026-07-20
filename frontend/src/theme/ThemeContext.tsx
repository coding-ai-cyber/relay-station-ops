import { createContext, useContext } from "react";

export type AppThemeMode = "dark" | "light";

export type AppThemeContextValue = {
  mode: AppThemeMode;
  toggleMode: () => void;
};

export const APP_THEME_STORAGE_KEY = "sub2api_ops_theme";

export const AppThemeContext = createContext<AppThemeContextValue | null>(null);

export function useAppTheme() {
  const context = useContext(AppThemeContext);
  if (!context) {
    throw new Error("useAppTheme must be used inside AppThemeContext.Provider");
  }
  return context;
}
