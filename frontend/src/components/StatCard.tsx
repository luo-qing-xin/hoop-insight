import type { ReactNode } from "react";

type StatCardProps = {
  label: string;
  value: ReactNode;
  trend?: string;
  description?: string;
  tooltip?: string;
  tone?: "blue" | "violet" | "green" | "amber";
  icon?: "trend" | "shield" | "pulse" | "timer";
  className?: string;
  valueClassName?: string;
  valueTitle?: string;
};

function StatIcon({ icon = "trend" }: { icon?: StatCardProps["icon"] }) {
  const commonProps = {
    width: 22,
    height: 22,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 2,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };

  switch (icon) {
    case "shield":
      return (
        <svg {...commonProps}>
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />
          <path d="M12 8v7" />
          <path d="M9 11h6" />
        </svg>
      );
    case "pulse":
      return (
        <svg {...commonProps}>
          <path d="M3 12h4l2-5 4 10 2-5h6" />
        </svg>
      );
    case "timer":
      return (
        <svg {...commonProps}>
          <path d="M10 2h4" />
          <path d="M12 14l3-3" />
          <circle cx="12" cy="14" r="8" />
        </svg>
      );
    case "trend":
    default:
      return (
        <svg {...commonProps}>
          <path d="M4 19V5" />
          <path d="M4 19h16" />
          <path d="m7 14 4-4 3 3 5-6" />
        </svg>
      );
  }
}

export default function StatCard({
  label,
  value,
  trend,
  description,
  tooltip,
  tone = "blue",
  icon = "trend",
  className,
  valueClassName,
  valueTitle,
}: StatCardProps) {
  return (
    <article className={`stat-card stat-card-${tone}${className ? ` ${className}` : ""}`}>
      <div className="stat-icon">
        <StatIcon icon={icon} />
      </div>
      <div className="stat-card-copy">
        <div className="stat-card-label">
          <p>{label}</p>
          {tooltip ? (
            <span className="stat-info-tooltip" tabIndex={0} aria-label={`${label} 指标解释`}>
              ?
              <span className="stat-info-tooltip-panel" role="tooltip">
                {tooltip}
              </span>
            </span>
          ) : null}
        </div>
        <strong className={valueClassName} title={valueTitle}>
          {value}
        </strong>
        <span>{description ?? trend}</span>
      </div>
    </article>
  );
}
