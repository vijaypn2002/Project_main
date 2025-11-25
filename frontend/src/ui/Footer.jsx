// src/ui/Footer.jsx
import { Link } from "react-router-dom";

const nav = {
  shop: [
    { label: "New arrivals", to: "/search?ordering=-id" }, // newest first
    { label: "Best sellers", to: "/search?ordering=-id" }, // placeholder: same sort your UI understands
    { label: "Deals", to: "/search?price_max=999" },       // compatible with SearchResultsPage
    { label: "All products", to: "/search" },
  ],
  help: [
    { label: "Orders", to: "/orders" },
    { label: "Returns", to: "/returns" },
    { label: "Wishlist", to: "/wishlist" },
    { label: "Login", to: "/login" },
  ],
  company: [
    { label: "About us", to: "/about" },
    { label: "Contact", to: "/contact" },
    { label: "Careers", to: "/careers" },
  ],
  legal: [
    { label: "Privacy policy", to: "/privacy-policy" },
    { label: "Terms of use", to: "/terms-of-use" },
    { label: "Shipping policy", to: "/shipping-policy" },
  ],
};

export default function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="mt-14 border-t bg-white text-sm">
      {/* top */}
      <div className="max-w-6xl mx-auto px-4 py-10 grid grid-cols-2 md:grid-cols-4 gap-8">
        <div>
          <div className="text-lg font-semibold mb-3">MyShop</div>
          <p className="text-gray-600">
            Quality products. Fast delivery. Easy returns.
          </p>

          {/* Socials (placeholders; replace hrefs) */}
          <div className="flex gap-3 mt-4">
            <a className="hover:opacity-80" href="#" aria-label="Instagram">
              <svg
                width="22"
                height="22"
                viewBox="0 0 24 24"
                fill="currentColor"
                className="text-gray-500"
              >
                <path d="M7 2h10a5 5 0 0 1 5 5v10a5 5 0 0 1-5 5H7a5 5 0 0 1-5-5V7a5 5 0 0 1 5-5Zm5 5a5 5 0 1 0 0 10 5 5 0 0 0 0-10Zm6.5-.25a1.25 1.25 0 1 0 0 2.5 1.25 1.25 0 0 0 0-2.5Z" />
              </svg>
            </a>
            <a className="hover:opacity-80" href="#" aria-label="Facebook">
              <svg
                width="22"
                height="22"
                viewBox="0 0 24 24"
                fill="currentColor"
                className="text-gray-500"
              >
                <path d="M13 22v-8h3l1-4h-4V7.5A1.5 1.5 0 0 1 14.5 6H17V2h-3.5A5.5 5.5 0 0 0 8 7.5V10H5v4h3v8h5Z" />
              </svg>
            </a>
            <a className="hover:opacity-80" href="#" aria-label="X">
              <svg
                width="22"
                height="22"
                viewBox="0 0 24 24"
                fill="currentColor"
                className="text-gray-500"
              >
                <path d="M3 3h3l6 8 6-8h3l-7.5 10L21 21h-3l-6-8-6 8H3l7.5-8.5L3 3Z" />
              </svg>
            </a>
          </div>
        </div>

        <Column title="Shop" items={nav.shop} />
        <Column title="Help" items={nav.help} />
        <div>
          <Column title="Company" items={nav.company} />
          <div className="mt-6">
            <div className="font-medium mb-2">Newsletter</div>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                alert("Thanks! You're subscribed.");
              }}
              className="flex gap-2"
            >
              <input
                type="email"
                required
                placeholder="your@email.com"
                className="border rounded-lg px-3 py-2 flex-1"
              />
              <button className="px-3 py-2 rounded-lg bg-black text-white">
                Join
              </button>
            </form>
          </div>
        </div>
      </div>

      {/* middle: payments + legal quick links */}
      <div className="border-t">
        <div className="max-w-6xl mx-auto px-4 py-6 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3 text-gray-500">
            <span className="text-xs">Payments:</span>
            <Badge>UPI</Badge>
            <Badge>Visa</Badge>
            <Badge>Mastercard</Badge>
            <Badge>Rupay</Badge>
            <Badge>Netbanking</Badge>
          </div>

          <div className="flex gap-4">
            {nav.legal.map((l) => (
              <Link
                key={l.label}
                to={l.to}
                className="text-gray-600 hover:text-black"
              >
                {l.label}
              </Link>
            ))}
          </div>
        </div>
      </div>

      {/* bottom */}
      <div className="border-t">
        <div className="max-w-6xl mx-auto px-4 py-6 flex flex-col md:flex-row items-center justify-between gap-3">
          <div className="text-gray-600">
            © {year} MyShop. All rights reserved.
          </div>
          <button
            onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
            className="text-indigo-600 hover:underline"
          >
            Back to top ↑
          </button>
        </div>
      </div>
    </footer>
  );
}

function Column({ title, items }) {
  return (
    <div>
      <div className="font-medium mb-3">{title}</div>
      <ul className="space-y-2">
        {items.map((it) => (
          <li key={it.label}>
            <Link to={it.to} className="text-gray-600 hover:text-black">
              {it.label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Badge({ children }) {
  return (
    <span className="border rounded-md px-2 py-1 text-xs bg-white">
      {children}
    </span>
  );
}
