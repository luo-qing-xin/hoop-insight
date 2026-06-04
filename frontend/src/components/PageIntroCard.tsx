import { Link } from "react-router-dom";

type IntroTag = {
  label: string;
  icon: "grid" | "bars" | "user" | "target";
  to?: string;
};

type PageIntroCardProps = {
  title: string;
  body: string;
  tags: readonly IntroTag[];
};

function IntroIcon({ icon }: { icon: IntroTag["icon"] | "overview" }) {
  const commonProps = {
    width: 20,
    height: 20,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 2,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };

  switch (icon) {
    case "bars":
      return (
        <svg {...commonProps}>
          <path d="M6 20V10" />
          <path d="M12 20V4" />
          <path d="M18 20v-7" />
        </svg>
      );
    case "user":
      return (
        <svg {...commonProps}>
          <circle cx="12" cy="8" r="4" />
          <path d="M20 21a8 8 0 0 0-16 0" />
        </svg>
      );
    case "target":
      return (
        <svg {...commonProps}>
          <circle cx="12" cy="12" r="9" />
          <circle cx="12" cy="12" r="4" />
          <path d="M12 8v4l3 2" />
        </svg>
      );
    case "overview":
      return (
        <svg {...commonProps}>
          <path d="M6 20V12" />
          <path d="M12 20V6" />
          <path d="M18 20v-9" />
        </svg>
      );
    case "grid":
    default:
      return (
        <svg {...commonProps}>
          <rect width="6" height="6" x="4" y="4" rx="1.5" />
          <rect width="6" height="6" x="14" y="4" rx="1.5" />
          <rect width="6" height="6" x="4" y="14" rx="1.5" />
          <rect width="6" height="6" x="14" y="14" rx="1.5" />
        </svg>
      );
  }
}

export default function PageIntroCard({ title, body, tags }: PageIntroCardProps) {
  return (
    <section className="intro-card">
      <div className="intro-main">
        <div className="intro-icon">
          <IntroIcon icon="overview" />
        </div>
        <div>
          <h2>{title}</h2>
          <p>{body}</p>
        </div>
      </div>
      <div className="intro-tags" aria-label="页面数据范围">
        {tags.map((tag) => (
          tag.to ? (
            <Link key={tag.label} to={tag.to} aria-label={`前往${tag.label}`}>
              <IntroIcon icon={tag.icon} />
              {tag.label}
            </Link>
          ) : (
            <span key={tag.label}>
              <IntroIcon icon={tag.icon} />
              {tag.label}
            </span>
          )
        ))}
      </div>
    </section>
  );
}
