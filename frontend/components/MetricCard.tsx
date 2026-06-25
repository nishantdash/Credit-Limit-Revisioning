import { Icon } from "./Icon";

type Props = {
  label: string;
  value: string;
  sub?: string;
  delta?: { value: string; direction: "up" | "down" | "flat" };
  iconName?: Parameters<typeof Icon>[0]["name"];
};

export function MetricCard({ label, value, sub, delta, iconName }: Props) {
  return (
    <div className="metric">
      <div className="row-top">
        <span className="label">{label}</span>
        {iconName && (
          <div className="icon-wrap">
            <Icon name={iconName} size={16} />
          </div>
        )}
      </div>
      <div className="value">{value}</div>
      {(delta || sub) && (
        <div className="row" style={{ gap: 6 }}>
          {delta && (
            <span className={`delta ${delta.direction === "up" ? "up" : delta.direction === "down" ? "down" : ""}`}>
              {delta.direction === "up" && <Icon name="trend-up" size={12} />}
              {delta.direction === "down" && <Icon name="trend-down" size={12} />}
              {" "}{delta.value}
            </span>
          )}
          {sub && <span className="sub">{sub}</span>}
        </div>
      )}
    </div>
  );
}
