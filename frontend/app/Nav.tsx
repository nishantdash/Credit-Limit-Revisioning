"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Icon } from "../components/Icon";
import { API_BASE } from "../lib/api";

const ITEMS: { href: string; label: string; icon: Parameters<typeof Icon>[0]["name"]; badgeKey?: "review" }[] = [
  { href: "/", label: "Dashboard", icon: "home" },
  { href: "/customers", label: "Customers", icon: "users" },
  { href: "/matrix", label: "Risk × Intent matrix", icon: "layers" },
  { href: "/offers", label: "Offers (consent)", icon: "card" },
  { href: "/actions", label: "Actions (decreases)", icon: "trend-down" },
  { href: "/review", label: "Review queue", icon: "checklist", badgeKey: "review" },
  { href: "/triggers", label: "Triggers", icon: "bolt" },
  { href: "/ingest", label: "Upload dump", icon: "upload" },
  { href: "/config", label: "Tenant config", icon: "shield" },
  { href: "/audit", label: "Audit log", icon: "audit" },
];

export function Nav() {
  const path = usePathname();
  const [reviewCount, setReviewCount] = useState<number | null>(null);

  useEffect(() => {
    let alive = true;
    const load = () => {
      fetch(`${API_BASE}/analytics/funnel`, { cache: "no-store" })
        .then((r) => (r.ok ? r.json() : null))
        .then((d) => { if (alive && d) setReviewCount(d.review_pending); })
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
          const badge = item.badgeKey === "review" && reviewCount && reviewCount > 0 ? reviewCount : null;
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
