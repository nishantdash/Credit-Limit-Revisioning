type IconName =
  | "home" | "users" | "upload" | "checklist" | "bolt" | "audit"
  | "search" | "bell" | "chevron-right" | "chevron-down" | "arrow-right"
  | "arrow-up" | "arrow-down" | "trend-up" | "trend-down" | "card"
  | "shield" | "layers" | "plus" | "download" | "filter" | "info"
  | "check" | "x" | "more" | "edit" | "play" | "alert-circle"
  | "spark" | "user" | "calendar" | "external";

type Props = { name: IconName; size?: number; stroke?: number; className?: string };

export function Icon({ name, size = 18, stroke = 1.75, className }: Props) {
  const common = {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: stroke,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    className,
  };
  switch (name) {
    case "home":
      return <svg {...common}><path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V20a1 1 0 0 0 1 1h4v-6h4v6h4a1 1 0 0 0 1-1V9.5"/></svg>;
    case "users":
      return <svg {...common}><circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0"/><circle cx="17" cy="9" r="2.5"/><path d="M21.5 18a4.5 4.5 0 0 0-5-4.4"/></svg>;
    case "upload":
      return <svg {...common}><path d="M12 16V4"/><path d="M7 9l5-5 5 5"/><path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/></svg>;
    case "checklist":
      return <svg {...common}><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M8 9l2 2 4-4"/><path d="M8 15h8"/></svg>;
    case "bolt":
      return <svg {...common}><path d="M13 2 4 14h7l-1 8 9-12h-7l1-8z"/></svg>;
    case "audit":
      return <svg {...common}><path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6"/><path d="M9 13h6"/><path d="M9 17h4"/></svg>;
    case "search":
      return <svg {...common}><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>;
    case "bell":
      return <svg {...common}><path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M10 21a2 2 0 0 0 4 0"/></svg>;
    case "chevron-right":
      return <svg {...common}><path d="m9 6 6 6-6 6"/></svg>;
    case "chevron-down":
      return <svg {...common}><path d="m6 9 6 6 6-6"/></svg>;
    case "arrow-right":
      return <svg {...common}><path d="M5 12h14"/><path d="m13 5 7 7-7 7"/></svg>;
    case "arrow-up":
      return <svg {...common}><path d="M12 19V5"/><path d="m5 12 7-7 7 7"/></svg>;
    case "arrow-down":
      return <svg {...common}><path d="M12 5v14"/><path d="m19 12-7 7-7-7"/></svg>;
    case "trend-up":
      return <svg {...common}><path d="m3 17 6-6 4 4 8-8"/><path d="M17 7h4v4"/></svg>;
    case "trend-down":
      return <svg {...common}><path d="m3 7 6 6 4-4 8 8"/><path d="M17 17h4v-4"/></svg>;
    case "card":
      return <svg {...common}><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 10h18"/><path d="M7 15h3"/></svg>;
    case "shield":
      return <svg {...common}><path d="M12 3 4 6v6c0 5 3.5 8.5 8 9 4.5-.5 8-4 8-9V6l-8-3z"/><path d="m9 12 2 2 4-4"/></svg>;
    case "layers":
      return <svg {...common}><path d="m12 3 9 5-9 5-9-5 9-5z"/><path d="m3 13 9 5 9-5"/><path d="m3 17 9 5 9-5"/></svg>;
    case "plus":
      return <svg {...common}><path d="M12 5v14"/><path d="M5 12h14"/></svg>;
    case "download":
      return <svg {...common}><path d="M12 4v12"/><path d="m7 11 5 5 5-5"/><path d="M4 19h16"/></svg>;
    case "filter":
      return <svg {...common}><path d="M3 5h18l-7 8v6l-4-2v-4z"/></svg>;
    case "info":
      return <svg {...common}><circle cx="12" cy="12" r="9"/><path d="M12 11v5"/><circle cx="12" cy="8" r="0.5" fill="currentColor"/></svg>;
    case "check":
      return <svg {...common}><path d="m5 12 5 5L20 7"/></svg>;
    case "x":
      return <svg {...common}><path d="M6 6l12 12"/><path d="M18 6 6 18"/></svg>;
    case "more":
      return <svg {...common}><circle cx="5" cy="12" r="1.2" fill="currentColor"/><circle cx="12" cy="12" r="1.2" fill="currentColor"/><circle cx="19" cy="12" r="1.2" fill="currentColor"/></svg>;
    case "edit":
      return <svg {...common}><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 1 1 3 3L7 19l-4 1 1-4z"/></svg>;
    case "play":
      return <svg {...common}><path d="M6 4v16l14-8z"/></svg>;
    case "alert-circle":
      return <svg {...common}><circle cx="12" cy="12" r="9"/><path d="M12 8v5"/><circle cx="12" cy="16" r="0.5" fill="currentColor"/></svg>;
    case "spark":
      return <svg {...common}><path d="M12 3v4"/><path d="M12 17v4"/><path d="M3 12h4"/><path d="M17 12h4"/><path d="m5.5 5.5 2.5 2.5"/><path d="m16 16 2.5 2.5"/><path d="m5.5 18.5 2.5-2.5"/><path d="m16 8 2.5-2.5"/></svg>;
    case "user":
      return <svg {...common}><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></svg>;
    case "calendar":
      return <svg {...common}><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4"/><path d="M8 3v4"/><path d="M3 10h18"/></svg>;
    case "external":
      return <svg {...common}><path d="M7 17 17 7"/><path d="M8 7h9v9"/></svg>;
  }
}
