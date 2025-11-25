// src/components/TrustStrip.jsx
import { memo } from "react";

/**
 * TrustStrip
 * - Lightweight benefits strip with optional custom items
 * - Each item: { icon?: ReactNode, title: string, desc?: string }
 */
function DefaultIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      className="h-6 w-6 shrink-0"
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M12 2l7 4v6c0 5-3.5 9-7 10-3.5-1-7-5-7-10V6l7-4z"
        fill="currentColor"
        opacity="0.12"
      />
      <path
        d="M12 3.3L6.5 6.4v5.6c0 4.4 2.9 7.9 5.5 9 2.6-1.1 5.5-4.6 5.5-9V6.4L12 3.3zm0 6.2l3.7 2-1 1.7-2.1-1.2-2.1 1.2-1-1.7 3.6-2z"
        fill="currentColor"
      />
    </svg>
  );
}

const DEFAULT_ITEMS = [
  { title: "Free returns", desc: "7-day easy returns" },
  { title: "Secure payments", desc: "UPI / Cards / Netbanking" },
  { title: "Fast delivery", desc: "Across India" },
];

function TrustStrip({ items = DEFAULT_ITEMS, className = "" }) {
  if (!items?.length) return null;

  return (
    <section
      className={["mt-12", className].filter(Boolean).join(" ")}
      aria-label="Shop assurances"
    >
      <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3">
        {items.map((it, i) => (
          <div
            key={i}
            className="group rounded-xl border bg-white p-4 transition-shadow hover:shadow-sm focus-within:shadow-sm"
          >
            <div className="flex items-start gap-3">
              <div className="text-indigo-600">
                {it.icon ?? <DefaultIcon />}
              </div>
              <div>
                <div className="font-semibold leading-6">{it.title}</div>
                {it.desc ? (
                  <div className="text-sm text-gray-600">{it.desc}</div>
                ) : null}
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

export default memo(TrustStrip);
