import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";
import { t } from "../i18n/index.js";
import Icon from "./Icon.jsx";

const NAV = [
  { to: "/agenda", icon: "agenda", label: "Agenda" },
  { to: "/surveys", icon: "survey", label: "Surveys" },
  { to: "/tracker", icon: "tracker", label: "Tracker" },
  { to: "/classroom", icon: "classroom", label: "Classroom" },
  { to: "/checklist", icon: "checklist", label: "Lesson checklist", prototype: true },
  { to: "/reports", icon: "reports", label: "Reports", prototype: true },
];

export default function Layout() {
  const { user, signOut } = useAuth();
  const [open, setOpen] = useState(false);
  const location = useLocation();
  useEffect(() => setOpen(false), [location.pathname]);
  return (
    <div className="shell">
      <aside className={`sidebar ${open ? "open" : ""}`} aria-label={t("Main menu")}>
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">T</span>
          <span>
            <b>{t("Training")}</b>
            <small>{t("Management System")}</small>
          </span>
        </div>
        <nav>
          <p className="nav-group">{t("Training")}</p>
          {NAV.map((item) => (
            <NavLink key={item.to} to={item.to}>
              <Icon name={item.icon} />
              <span>{t(item.label)}</span>
              {item.prototype ? <span className="nav-tag">{t("Prototype")}</span> : null}
            </NavLink>
          ))}
        </nav>
        <p className="sidebar-foot">{t("Demo data · mock integrations")}</p>
      </aside>
      {open ? <button type="button" className="scrim" aria-label={t("Close menu")} onClick={() => setOpen(false)} /> : null}
      <div className="main">
        <header className="topbar">
          <button type="button" className="icon-button burger" aria-label={t("Open menu")} onClick={() => setOpen(true)}>
            <Icon name="menu" />
          </button>
          <div className="topbar-right">
            <span className="avatar" aria-hidden="true">
              {(user?.name || "?").slice(0, 1).toUpperCase()}
            </span>
            <span className="user">
              <b>{user?.name}</b>
              <small>{t("Training office")}</small>
            </span>
            <button type="button" className="icon-button" onClick={signOut} aria-label={t("Sign out")} title={t("Sign out")}>
              <Icon name="logout" />
            </button>
          </div>
        </header>
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
