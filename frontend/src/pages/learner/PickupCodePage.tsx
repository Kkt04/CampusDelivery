import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { packagesApi, pickupApi } from "../../api/endpoints";
import type { PickupCode } from "../../api/types";
import { useUser } from "../../auth/AuthContext";
import { Alert, Button, ErrorAlert, PageHeader, Spinner, TextLink } from "../../components/ui";
import { useAction, useApi } from "../../lib/useApi";

function useCountdown(expiresAt: string | null) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    if (!expiresAt) return;
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [expiresAt]);
  return expiresAt ? Math.max(0, Math.floor((new Date(expiresAt).getTime() - now) / 1000)) : 0;
}

export function PickupCodePage() {
  const user = useUser();
  const id = Number(useParams().id);
  const pkg = useApi(() => packagesApi.get(id), [id]);
  const [issued, setIssued] = useState<PickupCode | null>(null);
  const [ttl, setTtl] = useState(0);
  // The code is requested by an explicit tap, never automatically, because each request revokes the previous code.
  const requestCode = useAction(() => pickupApi.requestCode(id));
  const secondsLeft = useCountdown(issued?.expires_at ?? null);

  async function onRequest() {
    const result = await requestCode.run();
    if (result) {
      setIssued(result);
      setTtl(Math.max(1, Math.round((new Date(result.expires_at).getTime() - Date.now()) / 1000)));
      void pkg.reload();
    }
  }

  if (pkg.loading && !pkg.data) return <Spinner />;
  if (pkg.error) return <ErrorAlert error={pkg.error} />;
  const p = pkg.data!;
  const expired = issued !== null && secondsLeft === 0;
  const eligible = p.status === "READY_FOR_PICKUP" || p.status === "PICKUP_REQUESTED";

  return (
    <div className="mx-auto max-w-xl">
      <PageHeader title="Pickup code" description={`For package ${p.internal_code} from ${p.courier_name}.`} />

      {!eligible ? (
        <Alert tone="info" title="A pickup code isn’t available for this package">
          {p.status === "COLLECTED" ? "It has already been collected." : "You can request one when the package is ready for pickup."}{" "}
          <TextLink to={`/learner/packages/${p.id}`}>Back to package</TextLink>
        </Alert>
      ) : !issued || expired ? (
        <div className="card space-y-4 p-6">
          {expired && <Alert tone="warn" title="This code has expired">Get a new code when you are at the gate.</Alert>}
          <p className="text-sm text-muted">
            Ask for the code when you are at Gate No. 2. It works once, for a short time, and only for you.
            Getting a new code cancels any earlier one.
          </p>
          <ErrorAlert error={requestCode.error} />
          <Button onClick={onRequest} pending={requestCode.pending}>{expired || p.status === "PICKUP_REQUESTED" ? "Get a new code" : "Get my code"}</Button>
        </div>
      ) : (
        <div className="space-y-5">
          <div className="ticket px-8 py-8 text-center">
            <p className="text-sm text-muted">Show this to the security officer</p>
            <p className="code-text mt-3 text-5xl tracking-[0.18em] text-ink sm:text-6xl" aria-label={`Pickup code ${issued.code.split("").join(" ")}`}>
              {issued.code.slice(0, 3)}<span className="mx-2 text-line">–</span>{issued.code.slice(3)}
            </p>
            <div className="mx-auto mt-6 border-t-2 border-dashed border-line pt-5 text-sm">
              <div className="grid grid-cols-3 gap-2">
                <div><p className="text-muted">Package</p><p className="code-text">{issued.internal_code}</p></div>
                <div><p className="text-muted">Shelf</p><p className="code-text">{p.storage_location?.code ?? "–"}</p></div>
                <div><p className="text-muted">Your ID</p><p className="code-text">{user.institutional_id}</p></div>
              </div>
            </div>
            <div className="mt-6">
              <div className="h-1.5 overflow-hidden rounded-full bg-paper" aria-hidden>
                <div className="h-full bg-brand transition-[width] duration-1000 ease-linear" style={{ width: `${(secondsLeft / ttl) * 100}%` }} />
              </div>
              <p className="mt-2 text-sm font-semibold" role="timer" aria-live="off">
                Valid for {Math.floor(secondsLeft / 60)}:{String(secondsLeft % 60).padStart(2, "0")}
              </p>
            </div>
          </div>
          <p className="text-center text-sm text-muted">
            This code is shown only once. If you leave this page, get a new code; the old one stops working.
          </p>
        </div>
      )}
    </div>
  );
}
