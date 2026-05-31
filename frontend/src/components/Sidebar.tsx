import { NavLink } from "react-router-dom";
import { APP_COPY, NAV_ITEMS } from "../constants/zhLabels";

const NAV_GROUPS = [
  { title: "核心分析", paths: ["/", "/games", "/players", "/teams", "/shots"] },
  { title: "智能能力", paths: ["/ask-ai"] },
  { title: "数据管理", paths: ["/data-center"] },
];

const NAV_ICONS: Record<string, IconName> = {
  "/": "dashboard",
  "/games": "calendar",
  "/players": "user",
  "/teams": "users",
  "/shots": "target",
  "/ask-ai": "bot",
  "/data-center": "database",
};

type IconName = "dashboard" | "calendar" | "user" | "users" | "target" | "bot" | "database" | "arrow";

function NavIcon({ name }: { name: IconName }) {
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

  switch (name) {
    case "calendar":
      return (
        <svg {...commonProps}>
          <path d="M8 2v4" />
          <path d="M16 2v4" />
          <rect width="18" height="18" x="3" y="4" rx="3" />
          <path d="M3 10h18" />
        </svg>
      );
    case "user":
      return (
        <svg {...commonProps}>
          <path d="M20 21a8 8 0 0 0-16 0" />
          <circle cx="12" cy="7" r="4" />
        </svg>
      );
    case "users":
      return (
        <svg {...commonProps}>
          <path d="M16 21a6 6 0 0 0-12 0" />
          <circle cx="10" cy="7" r="4" />
          <path d="M22 21a5 5 0 0 0-4-4.9" />
          <path d="M17 3.3a4 4 0 0 1 0 7.4" />
        </svg>
      );
    case "target":
      return (
        <svg {...commonProps}>
          <circle cx="12" cy="12" r="9" />
          <circle cx="12" cy="12" r="5" />
          <circle cx="12" cy="12" r="1.5" />
        </svg>
      );
    case "bot":
      return (
        <svg {...commonProps}>
          <path d="M12 8V4" />
          <rect width="16" height="12" x="4" y="8" rx="4" />
          <path d="M2 14h2" />
          <path d="M20 14h2" />
          <path d="M9 13h.01" />
          <path d="M15 13h.01" />
          <path d="M10 17h4" />
        </svg>
      );
    case "database":
      return (
        <svg {...commonProps}>
          <ellipse cx="12" cy="5" rx="8" ry="3" />
          <path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5" />
          <path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3" />
        </svg>
      );
    case "arrow":
      return (
        <svg {...commonProps}>
          <path d="M5 12h14" />
          <path d="m13 6 6 6-6 6" />
        </svg>
      );
    case "dashboard":
    default:
      return (
        <svg {...commonProps}>
          <rect width="7" height="7" x="3" y="3" rx="2" />
          <rect width="7" height="7" x="14" y="3" rx="2" />
          <rect width="7" height="7" x="14" y="14" rx="2" />
          <rect width="7" height="7" x="3" y="14" rx="2" />
        </svg>
      );
  }
}

export default function Sidebar() {
  const itemsByPath = new Map(NAV_ITEMS.map((item) => [item.to, item]));

  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">HI</div>
        <div className="brand-copy">
          <strong>{APP_COPY.brand}</strong>
          <span>{APP_COPY.brandSubtitle}</span>
        </div>
      </div>

      <nav className="nav-groups" aria-label="主导航">
        {NAV_GROUPS.map((group) => (
          <section className="nav-group" key={group.title}>
            <h2 className="nav-group-title">{group.title}</h2>
            <div className="nav-list">
              {group.paths.map((path) => {
                const item = itemsByPath.get(path);

                if (!item) {
                  return null;
                }

                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.to === "/"}
                    className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
                  >
                    <span className="nav-icon">
                      <NavIcon name={NAV_ICONS[item.to]} />
                    </span>
                    <span>{item.label}</span>
                  </NavLink>
                );
              })}
            </div>
          </section>
        ))}
      </nav>

      <div className="sidebar-panel">
        <span className="sidebar-panel-kicker">{APP_COPY.liveModelLabel}</span>
        <div className="sidebar-panel-title">
          <strong>{APP_COPY.liveApiTitle}</strong>
          <span className="sidebar-panel-arrow" aria-hidden="true">
            <NavIcon name="arrow" />
          </span>
        </div>
        <p>{APP_COPY.liveApiDescription}</p>
        <div className="sidebar-panel-status">
          <span aria-hidden="true" />
          {APP_COPY.liveApiStatus}
        </div>
      </div>
    </aside>
  );
}
