type Props = {
  name?: string;
  id?: string;
  size?: "sm" | "md" | "lg";
  round?: boolean;
};

function initials(name?: string, id?: string): string {
  if (name) {
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
    return parts[0].slice(0, 2).toUpperCase();
  }
  if (id) return id.split("-").pop()?.slice(0, 2).toUpperCase() ?? "?";
  return "?";
}

function colorBucket(seed: string): number {
  let h = 0;
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) >>> 0;
  return (h % 8) + 1;
}

export function Avatar({ name, id, size = "md", round = false }: Props) {
  const seed = (name || id || "").trim();
  const cls = ["avatar", round ? "round" : "", size === "sm" ? "sm" : size === "lg" ? "lg" : "", `av-${colorBucket(seed)}`].filter(Boolean).join(" ");
  return <div className={cls}>{initials(name, id)}</div>;
}
