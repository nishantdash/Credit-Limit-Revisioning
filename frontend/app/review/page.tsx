import { api, Decision } from "../../lib/api";
import { MetricCard } from "../../components/MetricCard";
import { ReviewQueue } from "./ReviewQueue";

export default async function ReviewPage() {
  const [queue, all] = await Promise.all([
    api<Decision[]>("/review/queue"),
    api<Decision[]>("/decisions?limit=300"),
  ]);
  const approved = all.filter((d) => d.review_status === "APPROVED").length;
  const rejected = all.filter((d) => d.review_status === "REJECTED").length;

  return (
    <>
      <div className="page-head">
        <div>
          <h2 className="page-title">Review queue</h2>
          <p className="page-sub" style={{ marginBottom: 0 }}>
            Confidence-gated human-in-the-loop. Low-confidence decisions don't auto-apply — increases are held before
            the offer is dispatched, sharp decreases before application.
          </p>
        </div>
      </div>

      <div className="grid cols-4">
        <MetricCard label="Awaiting review" value={queue.length.toString()} sub="Action needed" iconName="checklist" />
        <MetricCard label="Approved" value={approved.toString()} sub="Released to pipeline" iconName="check" />
        <MetricCard label="Rejected" value={rejected.toString()} sub="This cycle" iconName="x" />
        <MetricCard label="Avg decision time" value="3.8h" sub="SLA target: 24h" iconName="calendar" />
      </div>

      <div style={{ height: 24 }} />

      <ReviewQueue initial={queue} />
    </>
  );
}
