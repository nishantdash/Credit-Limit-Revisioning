type Props = {
  variant?:
    | "green" | "amber" | "red" | "purple" | "blue" | "gray" | "orange"
    | "UPGRADE" | "DOWNGRADE" | "FREEZE"
    | "PENDING" | "APPROVED" | "REJECTED" | "EXECUTED"
    | "PREMIUM" | "MASS"
    | "GOLD" | "SILVER" | "PLATINUM";
  bare?: boolean;
  children: React.ReactNode;
};

export function Pill({ variant = "gray", bare, children }: Props) {
  const cls = ["pill", `pill-${variant}`, bare ? "bare" : ""].filter(Boolean).join(" ");
  return <span className={cls}>{children}</span>;
}
