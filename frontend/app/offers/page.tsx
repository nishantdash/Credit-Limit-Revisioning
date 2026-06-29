import { api, Decision, Funnel, Roi, inrCompact } from "../../lib/api";
import { MetricCard } from "../../components/MetricCard";
import { OffersClient } from "./OffersClient";

export default async function OffersPage() {
  const [pending, funnel, roi] = await Promise.all([
    api<Decision[]>("/offers?status=PENDING_CONSENT"),
    api<Funnel>("/analytics/funnel"),
    api<Roi>("/analytics/roi"),
  ]);

  return (
    <>
      <div className="page-head">
        <div>
          <h2 className="page-title">Offer pipeline</h2>
          <p className="page-sub" style={{ marginBottom: 0 }}>
            Consent-gated limit increases. RBI requires explicit approval — the limit stays paused until the customer
            consents via OTP/MPIN. Silence is never approval.
          </p>
        </div>
      </div>

      <div className="grid cols-4">
        <MetricCard label="Awaiting consent" value={funnel.offers_pending_consent.toString()} sub="OTP/MPIN required" iconName="card" />
        <MetricCard label="Accepted" value={funnel.offers_accepted.toString()} sub="Activated this cycle" iconName="check" />
        <MetricCard label="Offered uplift" value={inrCompact(roi.offered_uplift_inr)} sub="Total across open offers" iconName="trend-up" />
        <MetricCard label="Temporary offers" value={roi.temporary_offers.toString()} sub="Seasonal · auto-revert" iconName="calendar" />
      </div>

      <div style={{ height: 24 }} />

      <OffersClient initial={pending} />
    </>
  );
}
