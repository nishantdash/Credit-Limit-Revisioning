import { api, Decision } from "../../lib/api";
import { HitlQueue } from "./HitlQueue";

export default async function HitlPage() {
  const queue = await api<Decision[]>("/hitl/queue");
  return (
    <>
      <h2>HITL queue <span className="layer-badge">L3</span></h2>
      <p className="page-sub">
        Decisions exceeding the bank's auto-approve threshold (₹50,000 delta). Maker-checker workflow per RBI compliance — officer reviews within 24h.
      </p>
      <HitlQueue initial={queue} />
    </>
  );
}
