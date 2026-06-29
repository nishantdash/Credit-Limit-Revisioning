type Props = {
  variant?: string;
  bare?: boolean;
  children: React.ReactNode;
  title?: string;
};

export function Pill({ variant = "gray", bare, children, title }: Props) {
  const cls = ["pill", `pill-${variant}`, bare ? "bare" : ""].filter(Boolean).join(" ");
  return <span className={cls} title={title}>{children}</span>;
}
