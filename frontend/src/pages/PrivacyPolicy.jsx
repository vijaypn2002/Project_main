// src/pages/PrivacyPolicy.jsx
export default function PrivacyPolicy() {
  return (
    <main className="max-w-3xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-4">Privacy policy</h1>
      <p className="text-sm text-gray-600 mb-6">
        This is a sample privacy policy page for your store. Replace this content
        with your actual policy drafted / reviewed by a legal professional.
      </p>

      <section className="space-y-4 text-sm text-gray-700">
        <div>
          <h2 className="font-semibold mb-1">Information we collect</h2>
          <p>
            We may collect information such as your name, email address, phone
            number, shipping address and payment details when you place an order
            or create an account.
          </p>
        </div>
        <div>
          <h2 className="font-semibold mb-1">How we use your information</h2>
          <p>
            We use your information to process orders, provide customer support,
            improve our services and send important updates related to your
            purchases.
          </p>
        </div>
        <div>
          <h2 className="font-semibold mb-1">Contact</h2>
          <p>
            If you have any questions about this policy, please contact us at
            <span className="font-medium"> support@example.com</span>.
          </p>
        </div>
      </section>
    </main>
  );
}
