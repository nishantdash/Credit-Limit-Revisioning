"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const ITEMS = [
  { href: "/", label: "Dashboard", layer: "L7" },
  { href: "/customers", label: "Customers", layer: "L1" },
  { href: "/ingest", label: "Upload dump", layer: "L1" },
  { href: "/hitl", label: "HITL queue", layer: "L3" },
  { href: "/triggers", label: "Trigger simulator", layer: "L3" },
  { href: "/audit", label: "Audit log", layer: "L6" },
];

export function Nav() {
  const path = usePathname();
  return (
    <nav>
      {ITEMS.map((item) => {
        const active = path === item.href || (item.href !== "/" && path.startsWith(item.href));
        return (
          <Link
            key={item.href}
            href={item.href}
            className={active ? "active" : ""}
          >
            {item.label}
            <span className="layer-badge">{item.layer}</span>
          </Link>
        );
      })}
    </nav>
  );
}
