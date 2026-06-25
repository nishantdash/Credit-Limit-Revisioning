import { api, Decision } from "../../lib/api";
import { HitlQueue } from "./HitlQueue";
import { MetricCard } from "../../components/MetricCard";

export default async function HitlPage() {
  const [queue, all] = await Promise.all([
    api<Decision[]>("/hitl/queue"),
    api<Decision[]>("/decisions?limit=200"),
  ]);
  const approved = all.filter((d) => d.hitl_status === "APPROVED").length;
  const rejected = all.filter((d) => d.hitl_status === "REJECTED").length;
  const totalRequiringHitl = all.filter((d) => d.hitl_required).length;

  return (
    <>
      <div className="page-head">
        <div>
          <h2 className="page-title">HITL queue</h2>
          <p className="page-sub" style={{ marginBottom: 0 }}>
            Limit revisions over the ₹50,000 auto-approve threshold — RBI maker-checker workflow.
          </p>
        </div>
      </div>

      <div className="grid cols-4">
        <MetricCard label="Awaiting your approval" value={queue.length.toString()} sub="Action needed" iconName="checklist" />
        <MetricCard label="Approved" value={approved.toString()} sub="This cycle" iconName="check" />
        <MetricCard label="Rejected" value={rejected.toString()} sub="This cycle" iconName="x" />
        <MetricCard label="Avg decision time" value="4.2h" sub="Maker-checker SLA target: 24h" iconName="calendar" />
      </div>

      <div style={{ height: 24 }} />

      <HitlQueue initial={queue} pendingCount={queue.length} decidedCount={approved + rejected} totalCount={totalRequiringHitl} />
    </>
  );
}
