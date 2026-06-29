"use client";
import { useEffect, useState } from "react";
import { Icon } from "../components/Icon";
import { API_BASE } from "../lib/api";

export function TopBar() {
  const [tenant, setTenant] = useState<{ name: string; archetype: string } | null>(null);

  useEffect(() => {
    let alive = true;
    const load = () =>
      fetch(`${API_BASE}/config`, { cache: "no-store" })
        .then((r) => (r.ok ? r.json() : null))
        .then((d) => { if (alive && d) setTenant({ name: d.name, archetype: d.archetype }); })
        .catch(() => {});
    load();
    const t = setInterval(load, 5000);
    return () => { alive = false; clearInterval(t); };
  }, []);

  return (
    <div className="topbar">
      <div className="org">
        <div className="org-mark">{tenant?.archetype?.[0] ?? "H"}</div>
        <div className="org-meta">
          <div className="org-name">
            {tenant?.name ?? "CLR"}
            <span style={{ marginLeft: 4, color: "var(--text-dim)" }}><Icon name="chevron-down" size={12} /></span>
          </div>
          <div className="org-sub">Intent-driven CLR · {tenant?.archetype ?? "tenant"} deployment</div>
        </div>
      </div>
      <div className="search">
        <Icon name="search" size={14} />
        <input placeholder="Search customers, decisions..." />
        <span className="kbd">⌘K</span>
      </div>
      <div className="right">
        <button className="icon-btn" aria-label="Notifications">
          <Icon name="bell" size={18} />
          <span className="dot" />
        </button>
        <div className="user">
          <div className="av">ND</div>
          <div className="user-meta">
            <div className="user-name">Nishant Dash</div>
            <div className="user-role">Credit Policy · Risk</div>
          </div>
          <Icon name="chevron-down" size={12} />
        </div>
      </div>
    </div>
  );
}
