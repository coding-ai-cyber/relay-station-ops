import {
  AppstoreOutlined,
  AuditOutlined,
  BankOutlined,
  BarChartOutlined,
  ApiOutlined,
  BellOutlined,
  CalendarOutlined,
  CloudServerOutlined,
  ShopOutlined,
  LineChartOutlined,
  DatabaseOutlined,
  DollarOutlined,
  ExperimentOutlined,
  FileTextOutlined,
  LogoutOutlined,
  MenuOutlined,
  SafetyCertificateOutlined,
  UserOutlined,
  TeamOutlined
} from "@ant-design/icons";
import { Avatar, Badge, Button, Drawer, Empty, Layout, Menu, Popover, Space, Switch, Tag, Tooltip, Typography } from "antd";
import type { MenuProps } from "antd";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Link, useLocation } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { useAppTheme } from "../theme/ThemeContext";
import { getExpiringAssets } from "../api/endpoints";
import { dateOnly } from "../utils/format";

const { Header, Sider, Content } = Layout;

const navigationItems: MenuProps["items"] = [
  {
    type: "group",
    label: "经营分析",
    children: [
      { key: "dashboard", icon: <BarChartOutlined />, label: <Link to="/">仪表盘</Link> },
      { key: "reports", icon: <LineChartOutlined />, label: <Link to="/reports">盈亏报表</Link> }
    ]
  },
  {
    type: "group",
    label: "采购与资产",
    children: [
      { key: "suppliers", icon: <BankOutlined />, label: <Link to="/suppliers">供应商</Link> },
      { key: "purchases", icon: <FileTextOutlined />, label: <Link to="/purchases">采购记录</Link> },
      { key: "sub2api-instances", icon: <ApiOutlined />, label: <Link to="/sub2api-instances">中转站配置</Link> },
      { key: "operations-platforms", icon: <SafetyCertificateOutlined />, label: <Link to="/operations-platforms">平台配置</Link> },
      { key: "accounts", icon: <UserOutlined />, label: <Link to="/accounts">账号资产</Link> },
      { key: "servers", icon: <CloudServerOutlined />, label: <Link to="/servers">服务器资产</Link> },
      { key: "proxy-pools", icon: <ApiOutlined />, label: <Link to="/proxy-pools">IP地址池资产</Link> },
      { key: "shop-monitors", icon: <ShopOutlined />, label: <Link to="/shop-monitors">店铺监控</Link> },
      { key: "evaluations", icon: <ExperimentOutlined />, label: <Link to="/evaluations">账号测评</Link> }
    ]
  },
  {
    type: "group",
    label: "财务与系统",
    children: [
      { key: "revenues", icon: <DollarOutlined />, label: <Link to="/revenues">收入管理</Link> },
      { key: "costs", icon: <DatabaseOutlined />, label: <Link to="/costs">成本管理</Link> },
      { key: "audit-logs", icon: <AuditOutlined />, label: <Link to="/audit-logs">审计日志</Link> },
      { key: "system-maintenance", icon: <SafetyCertificateOutlined />, label: <Link to="/system-maintenance">系统维护</Link> },
      { key: "users", icon: <TeamOutlined />, label: <Link to="/users">用户管理</Link> }
    ]
  }
];

const pageNames: Record<string, string> = {
  dashboard: "仪表盘",
  suppliers: "供应商",
  purchases: "采购记录",
  "sub2api-instances": "中转站配置",
  "operations-platforms": "平台配置",
  accounts: "账号资产",
  servers: "服务器资产",
  "proxy-pools": "IP地址池资产",
  "shop-monitors": "店铺监控",
  evaluations: "账号测评",
  revenues: "收入管理",
  costs: "成本管理",
  reports: "盈亏报表",
  "audit-logs": "审计日志",
  "system-maintenance": "系统维护",
  users: "用户管理"
};

function assetTypeLabel(type: string) {
  if (type === "account") {
    return "账号资产";
  }
  if (type === "server") {
    return "服务器资产";
  }
  if (type === "proxy_pool") {
    return "IP地址池资产";
  }
  return type;
}

function Brand() {
  return (
    <div className="brand-card">
      <div className="brand-logo">
        <AppstoreOutlined />
      </div>
      <div>
        <Typography.Title level={4} className="brand-title">
          Sub2API Ops
        </Typography.Title>
        <div className="brand-subtitle">经营管理后台</div>
      </div>
    </div>
  );
}

export function AppLayout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const { logout, user } = useAuth();
  const { mode, toggleMode } = useAppTheme();
  const menuTheme = mode === "light" ? "light" : "dark";
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [alertOpen, setAlertOpen] = useState(false);
  const expiringSoon = useQuery({
    queryKey: ["dashboard", "expiring-assets", 7],
    queryFn: () => getExpiringAssets(7),
    staleTime: 60_000
  });

  const selectedKey = useMemo(() => {
    const segment = location.pathname.split("/")[1];
    return segment || "dashboard";
  }, [location.pathname]);

  useEffect(() => {
    setMobileMenuOpen(false);
  }, [location.pathname]);

  const alertCount = expiringSoon.data?.length ?? 0;
  const alertContent = (
    <div className="alert-popover">
      <div className="alert-popover-head">
        <span>到期提醒</span>
        <Tag color={alertCount > 0 ? "red" : "default"}>{alertCount} 条</Tag>
      </div>
      {alertCount > 0 ? (
        <div className="alert-popover-list">
          {expiringSoon.data?.slice(0, 6).map((asset) => (
            <div className="alert-popover-row" key={`${asset.asset_type}-${asset.asset_id}`}>
              <span className="alert-popover-icon">
                <CalendarOutlined />
              </span>
              <span className="alert-popover-body">
                <strong>{asset.name}</strong>
                <small>{assetTypeLabel(asset.asset_type)} / {dateOnly(asset.expired_at)}</small>
              </span>
              <Tag color={asset.days_left <= 3 ? "red" : "gold"}>{asset.days_left} 天</Tag>
            </div>
          ))}
          {alertCount > 6 ? <div className="alert-popover-more">还有 {alertCount - 6} 条到期提醒</div> : null}
        </div>
      ) : (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无告警信息" />
      )}
    </div>
  );

  return (
    <Layout className="app-shell">
      <a className="skip-link" href="#main-content">跳到主要内容</a>
      <Sider width={236} className="app-sider desktop-sider" trigger={null}>
        <Brand />
        <Menu
          className="side-menu"
          theme={menuTheme}
          mode="inline"
          selectedKeys={[selectedKey]}
          items={navigationItems}
        />
      </Sider>
      <Drawer
        className="mobile-nav-drawer"
        placement="left"
        size={280}
        open={mobileMenuOpen}
        onClose={() => setMobileMenuOpen(false)}
        title={<Brand />}
      >
        <Menu
          className="side-menu"
          theme={menuTheme}
          mode="inline"
          selectedKeys={[selectedKey]}
          items={navigationItems}
        />
      </Drawer>
      <Layout>
        <Header className="app-header">
          <div className="header-left">
            <Tooltip title="打开导航">
              <Button
                className="mobile-menu-button"
                type="text"
                icon={<MenuOutlined />}
                aria-label="打开导航"
                onClick={() => setMobileMenuOpen(true)}
              />
            </Tooltip>
            <div className="header-context">
              <span className="header-context-root">经营工作台</span>
              <span className="header-context-divider">/</span>
              <strong>{pageNames[selectedKey] ?? "经营工作台"}</strong>
            </div>
          </div>
          <Space size={12}>
            <Popover
              trigger="click"
              placement="bottomRight"
              open={alertOpen}
              onOpenChange={setAlertOpen}
              content={alertContent}
              overlayClassName="alert-popover-overlay"
            >
              <Badge count={expiringSoon.data?.length ?? 0} size="small">
                <Button
                  icon={<BellOutlined />}
                  aria-label="查看到期提醒"
                />
              </Badge>
            </Popover>
            <span className="system-status">
              <SafetyCertificateOutlined /> 数据已连接
            </span>
            <Tooltip title={mode === "dark" ? "切换浅色主题" : "切换深色主题"}>
              <span className="theme-mode-control">
                <Switch
                  className="theme-mode-switch"
                  checked={mode === "light"}
                  aria-label={mode === "dark" ? "切换浅色主题" : "切换深色主题"}
                  onChange={toggleMode}
                />
                <span className="theme-mode-label">{mode === "light" ? "浅色" : "深色"}</span>
              </span>
            </Tooltip>
            <div className="user-chip">
              <Avatar size={30} icon={<UserOutlined />} />
              <span>
                <span className="user-name">{user?.username}</span>
                <span className="user-role">{user?.role}</span>
              </span>
            </div>
            <Tooltip title="退出登录">
              <Button icon={<LogoutOutlined />} aria-label="退出登录" onClick={logout} />
            </Tooltip>
          </Space>
        </Header>
        <Content id="main-content" className="app-content">{children}</Content>
      </Layout>
    </Layout>
  );
}
