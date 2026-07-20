import React from "react";
import ReactDOM from "react-dom/client";
import { ConfigProvider, App as AntApp, theme } from "antd";
import zhCN from "antd/locale/zh_CN";
import dayjs from "dayjs";
import "dayjs/locale/zh-cn";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";

import { RootApp } from "./RootApp";
import { APP_THEME_STORAGE_KEY, AppThemeContext } from "./theme/ThemeContext";
import type { AppThemeMode } from "./theme/ThemeContext";
import "./styles.css";

dayjs.locale("zh-cn");

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1
    }
  }
});

function getInitialThemeMode(): AppThemeMode {
  const saved = localStorage.getItem(APP_THEME_STORAGE_KEY);
  return saved === "light" ? "light" : "dark";
}

function ThemedApp() {
  const [mode, setMode] = useState<AppThemeMode>(getInitialThemeMode);
  const isLight = mode === "light";
  const themeContextValue = useMemo(
    () => ({
      mode,
      toggleMode: () =>
        setMode((current) => (current === "dark" ? "light" : "dark"))
    }),
    [mode]
  );

  useEffect(() => {
    document.documentElement.dataset.theme = mode;
    localStorage.setItem(APP_THEME_STORAGE_KEY, mode);
  }, [mode]);

  return (
    <AppThemeContext.Provider value={themeContextValue}>
      <ConfigProvider
        locale={zhCN}
        theme={{
          algorithm: isLight ? theme.defaultAlgorithm : theme.darkAlgorithm,
          token: {
            colorPrimary: isLight ? "#5b5ce2" : "#8b5cf6",
            colorInfo: isLight ? "#0891b2" : "#22d3ee",
            colorSuccess: isLight ? "#059669" : "#34d399",
            colorWarning: isLight ? "#d97706" : "#f59e0b",
            colorError: isLight ? "#e11d48" : "#fb7185",
            colorText: isLight ? "#172033" : "#f5f8ff",
            colorTextSecondary: isLight ? "#52617a" : "#c2cbe0",
            colorTextTertiary: isLight ? "#75839a" : "#9eabc7",
            colorBorder: isLight ? "#d6ddec" : "rgba(177, 193, 232, 0.32)",
            colorBgLayout: isLight ? "#eef3fb" : "#101729",
            colorBgContainer: isLight ? "#ffffff" : "#172033",
            colorBgElevated: isLight ? "#ffffff" : "#1b2540",
            borderRadius: 12,
            boxShadow: isLight
              ? "0 14px 34px rgba(42, 54, 88, 0.11)"
              : "0 18px 46px rgba(0, 0, 0, 0.24)",
            fontFamily:
              "Fira Sans, Noto Sans SC, Microsoft YaHei, ui-sans-serif, system-ui, sans-serif"
          },
          components: {
            Layout: {
              headerBg: isLight ? "rgba(255, 255, 255, 0.88)" : "rgba(8, 12, 26, 0.78)",
              siderBg: isLight ? "#f8fbff" : "#090d1c"
            },
            Menu: {
              darkItemBg: isLight ? "#f8fbff" : "#090d1c",
              darkSubMenuItemBg: isLight ? "#f8fbff" : "#090d1c",
              darkItemSelectedBg: isLight ? "#e9edff" : "rgba(139, 92, 246, 0.32)",
              darkItemColor: isLight ? "#52617a" : "#a9b6d6",
              darkItemHoverColor: isLight ? "#172033" : "#ffffff",
              darkItemSelectedColor: isLight ? "#3234a8" : "#ffffff",
              itemBorderRadius: 10
            },
            Button: {
              borderRadius: 10,
              controlHeight: 36
            },
            Table: {
              headerBg: isLight ? "#edf2fb" : "rgba(55, 65, 100, 0.74)",
              headerColor: isLight ? "#344158" : "#e4ebfa",
              rowHoverBg: isLight ? "#f2f6ff" : "rgba(65, 82, 128, 0.42)"
            },
            Modal: {
              borderRadiusLG: 16
            },
            Input: {
              borderRadius: 10
            },
            Select: {
              borderRadius: 10
            },
            DatePicker: {
              borderRadius: 10
            }
          }
        }}
      >
        <AntApp>
          <QueryClientProvider client={queryClient}>
            <BrowserRouter>
              <RootApp />
            </BrowserRouter>
          </QueryClientProvider>
        </AntApp>
      </ConfigProvider>
    </AppThemeContext.Provider>
  );
}

document.documentElement.dataset.theme = getInitialThemeMode();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ThemedApp />
  </React.StrictMode>
);
