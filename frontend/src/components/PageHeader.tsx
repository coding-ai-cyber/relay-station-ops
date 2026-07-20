import { Typography } from "antd";

type PageHeaderProps = {
  title: string;
  subtitle?: string;
  extra?: React.ReactNode;
  meta?: React.ReactNode;
};

export function PageHeader({ title, subtitle, extra, meta }: PageHeaderProps) {
  return (
    <div className="page-hero">
      <div className="page-heading">
        <div className="page-breadcrumb">经营工作台 / {title}</div>
        <Typography.Title level={1} className="page-title">
          {title}
        </Typography.Title>
        {subtitle ? <div className="page-subtitle">{subtitle}</div> : null}
        {meta ? <div className="page-meta">{meta}</div> : null}
      </div>
      {extra ? <div className="page-header-extra">{extra}</div> : null}
    </div>
  );
}
