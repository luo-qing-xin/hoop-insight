import type { ReactNode } from "react";
import { APP_COPY } from "../constants/zhLabels";
import Sidebar from "./Sidebar";

type LayoutProps = {
  title: string;
  description: string;
  children: ReactNode;
  className?: string;
};

export default function Layout({ title, description, children, className = "" }: LayoutProps) {
  return (
    <div className={`app-shell${className ? ` ${className}` : ""}`}>
      <Sidebar />
      <div className="main-shell">
        <header className="topbar">
          <div>
            <p className="eyebrow">{APP_COPY.eyebrow}</p>
            <h1>{title}</h1>
            <p>{description}</p>
          </div>
          <div className="topbar-actions">
            <button className="ghost-button" type="button">
              {APP_COPY.export}
            </button>
            <button className="primary-button" type="button">
              {APP_COPY.newReport}
            </button>
          </div>
        </header>
        <main className="content-area">{children}</main>
      </div>
    </div>
  );
}
