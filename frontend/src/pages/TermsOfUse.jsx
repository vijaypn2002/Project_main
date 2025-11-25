// src/pages/TermsOfUse.jsx
export default function TermsOfUse() {
  return (
    <main className="max-w-3xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-4">Terms of use</h1>
      <p className="text-sm text-gray-600 mb-6">
        These example terms are placeholders. Replace them with proper terms
        drafted / approved for your business.
      </p>

      <section className="space-y-4 text-sm text-gray-700">
        <div>
          <h2 className="font-semibold mb-1">Use of website</h2>
          <p>
            By using this website, you agree not to misuse the services, and to
            comply with applicable laws and regulations.
          </p>
        </div>
        <div>
          <h2 className="font-semibold mb-1">Orders & payments</h2>
          <p>
            All orders are subject to availability and confirmation of the order
            price. Payments must be made using supported payment methods.
          </p>
        </div>
        <div>
          <h2 className="font-semibold mb-1">Liability</h2>
          <p>
            To the maximum extent permitted by law, we are not liable for any
            indirect or consequential loss arising from your use of this site.
          </p>
        </div>
      </section>
    </main>
  );
}
