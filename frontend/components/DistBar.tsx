export type Seg = { label: string; value: number; color: string };

const COLORS: Record<string, string> = {
  GROWTH: "var(--green)", DISTRESS: "var(--red)", SEASONAL: "var(--orange)",
  NEUTRAL: "var(--text-muted)", KNOCKOUT: "var(--purple)",
  tier1: "var(--green)", tier2: "var(--primary)", tier3: "var(--amber)", tier4: "var(--red)",
  INCREASE: "var(--green)", DECREASE: "var(--red)", MAINTAIN: "var(--text-muted)", FREEZE: "var(--amber)",
};

export function colorFor(key: string): string {
  return COLORS[key] ?? "var(--primary)";
}

export function DistBar({ segments }: { segments: Seg[] }) {
  const total = segments.reduce((s, x) => s + x.value, 0) || 1;
  const shown = segments.filter((s) => s.value > 0);
  return (
    <div>
      <div className="distbar">
        {shown.map((s) => (
          <span key={s.label} style={{ width: `${(s.value / total) * 100}%`, background: s.color }} title={`${s.label}: ${s.value}`} />
        ))}
      </div>
      <div className="dist-legend">
        {shown.map((s) => (
          <div key={s.label} className="item">
            <span className="dot" style={{ background: s.color }} />
            {s.label} <strong style={{ color: "var(--text)" }}>{s.value}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}
