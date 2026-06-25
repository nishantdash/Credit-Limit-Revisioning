import { IngestUploader } from "./IngestUploader";

export default function IngestPage() {
  return (
    <>
      <h2>Upload transaction dump <span className="layer-badge">L1</span></h2>
      <p className="page-sub">
        Bank use case: upload a CSV export from CBS for a specific customer cohort,
        then run CLR on just that cohort. Useful for piloting against a hand-picked
        50k-customer slice before opening the firehose.
      </p>
      <IngestUploader />
    </>
  );
}
