"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Icon } from "../components/Icon";

const ITEMS: { href: string; label: string; icon: Parameters<typeof Icon>[0]["name"]; badgeKey?: "hitl" }[] = [
  { href: "/", label: "Dashboard", icon: "home" },
  { href: "/customers", label: "Customers", icon: "users" },
  { href: "/ingest", label: "Upload dump", icon: "upload" },
  { href: "/hitl", label: "HITL queue", icon: "checklist", badgeKey: "hitl" },
  { href: "/triggers", label: "Triggers", icon: "bolt" },
  { href: "/audit", label: "Audit log", icon: "audit" },
];

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

export function Nav() {
  const path = usePathname();
  const [hitlCount, setHitlCount] = useState<number | null>(null);

  useEffect(() => {
    let alive = true;
    const load = () => {
      fetch(`${API_BASE}/analytics/funnel`, { cache: "no-store" })
        .then((r) => r.ok ? r.json() : null)
        .then((d) => { if (alive && d) setHitlCount(d.hitl_pending); })
        .catch(() => {});
    };
    load();
    const t = setInterval(load, 5000);
    return () => { alive = false; clearInterval(t); };
  }, []);

  return (
    <>
      <Link href="/" className="brand-mark" title="CLR">CLR</Link>
      <nav>
        {ITEMS.map((item) => {
          const active = path === item.href || (item.href !== "/" && path.startsWith(item.href));
          const badge = item.badgeKey === "hitl" && hitlCount && hitlCount > 0 ? hitlCount : null;
          return (
            <Link key={item.href} href={item.href} className={`nav-item ${active ? "active" : ""}`} aria-label={item.label}>
              <Icon name={item.icon} size={20} />
              {badge !== null && <span className="badge-count">{badge}</span>}
              <span className="tip">{item.label}</span>
            </Link>
          );
        })}
      </nav>
      <div className="user-pill" title="Nishant Dash">ND</div>
    </>
  );
}
