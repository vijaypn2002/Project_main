// src/pages/ShippingPolicy.jsx
export default function ShippingPolicy() {
  return (
    <main className="max-w-3xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-4">Shipping policy</h1>
      <p className="text-sm text-gray-600 mb-6">
        This is a basic shipping policy template. Update it with your actual
        shipping rules, carriers and timelines.
      </p>

      <section className="space-y-4 text-sm text-gray-700">
        <div>
          <h2 className="font-semibold mb-1">Delivery time</h2>
          <p>
            Orders are typically processed within 1–2 business days. Delivery
            time depends on your location and the selected shipping method.
          </p>
        </div>
        <div>
          <h2 className="font-semibold mb-1">Shipping charges</h2>
          <p>
            Shipping charges are calculated at checkout based on cart value,
            weight and destination. Free shipping may be available on eligible
            orders.
          </p>
        </div>
        <div>
          <h2 className="font-semibold mb-1">Returns & damaged items</h2>
          <p>
            If an item arrives damaged or incorrect, please raise a return
            request from the Returns section and our team will assist you.
          </p>
        </div>
      </section>
    </main>
  );
}
