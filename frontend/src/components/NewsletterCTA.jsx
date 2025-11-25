// src/components/NewsletterCTA.jsx
import { useState } from "react";

export default function NewsletterCTA() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [ok, setOk] = useState(false);
  const [err, setErr] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setErr("");
    setBusy(true);

    try {
      // If you later expose a backend endpoint, plug it in here:
      // await api.post("/cms/newsletter/subscribe/", { email });
      await new Promise((r) => setTimeout(r, 500)); // mock
      setOk(true);
    } catch (e) {
      setErr("Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="mt-12 border rounded-xl bg-white p-6">
      <div className="md:flex items-center justify-between gap-6">
        <div className="mb-4 md:mb-0">
          <h2 className="text-lg font-semibold">Get updates & offers</h2>
          <p className="text-sm text-gray-600">No spam. Unsubscribe anytime.</p>
        </div>

        {ok ? (
          <div
            className="text-sm text-green-700 bg-green-50 border border-green-200 rounded-lg px-3 py-2"
            role="status"
            aria-live="polite"
          >
            Thanks! You’re on the list.
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="w-full md:w-auto flex flex-col sm:flex-row gap-2">
            {/* Honeypot (basic bot trap) */}
            <input type="text" tabIndex={-1} autoComplete="off" className="hidden" aria-hidden="true" />
            <label htmlFor="newsletter-email" className="sr-only">
              Email address
            </label>
            <input
              id="newsletter-email"
              type="email"
              inputMode="email"
              autoComplete="email"
              required
              placeholder="your@email.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="border rounded-lg px-3 py-2 w-full sm:w-72 focus:outline-none focus:ring-2 focus:ring-black/70"
            />
            <button
              type="submit"
              disabled={!email || busy}
              className="px-4 py-2 rounded-lg bg-black text-white disabled:opacity-60"
            >
              {busy ? "Subscribing…" : "Subscribe"}
            </button>

            {!!err && (
              <div className="text-xs text-red-600 sm:ml-2 sm:self-center" role="alert" aria-live="polite">
                {err}
              </div>
            )}
          </form>
        )}
      </div>
    </section>
  );
}
