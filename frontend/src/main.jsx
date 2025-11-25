// src/main.jsx
import React from "react";
import ReactDOM from "react-dom/client";
import {
  createBrowserRouter,
  RouterProvider,
  useRouteError,
  isRouteErrorResponse,
  Link,
} from "react-router-dom";
import "./index.css";

import RootLayout from "./ui/RootLayout.jsx";
import HomePage from "./pages/HomePage.jsx";
import ProductDetail from "./pages/ProductDetail.jsx";
import CartPage from "./pages/CartPage.jsx";
import CheckoutPage from "./pages/CheckoutPage.jsx";
import OrdersPage from "./pages/OrdersPage.jsx";
import OrderDetail from "./pages/OrderDetail.jsx";
import Login from "./pages/Login.jsx";
import MyOrders from "./pages/MyOrders.jsx";
import Returns from "./pages/Returns.jsx";
import SearchResultsPage from "./pages/SearchResultsPage.jsx";
import Wishlist from "./pages/Wishlist.jsx";

// NEW: legal pages
import PrivacyPolicy from "./pages/PrivacyPolicy.jsx";
import TermsOfUse from "./pages/TermsOfUse.jsx";
import ShippingPolicy from "./pages/ShippingPolicy.jsx";

// Admin
import AdminLayout from "./admin/AdminLayout.jsx";
import AdminDashboard from "./admin/pages/Dashboard.jsx";
import AdminBanners from "./admin/pages/Banners.jsx";
import AdminCoupons from "./admin/pages/Coupons.jsx";
import AdminGuard from "./admin/AdminGuard.jsx";

function ErrorScreen() {
  const error = useRouteError();
  let title = "Something went wrong";
  let message = "Unknown error";

  if (isRouteErrorResponse(error)) {
    title = `${error.status} ${error.statusText}`;
    message =
      typeof error.data === "string"
        ? error.data
        : error.data?.message || JSON.stringify(error.data || {}, null, 2);
  } else if (error instanceof Error) {
    message = error.message;
  } else if (typeof error === "string") {
    message = error;
  }

  return (
    <div className="max-w-3xl p-4">
      <h1 className="text-xl font-bold mb-2">{title}</h1>
      <pre className="text-sm bg-gray-50 border rounded p-3 overflow-auto">
        {message}
      </pre>
      <div className="mt-3">
        <Link to="/" className="text-indigo-600 underline">
          Go Home
        </Link>
      </div>
    </div>
  );
}

const router = createBrowserRouter([
  {
    path: "/",
    element: <RootLayout />,
    errorElement: <ErrorScreen />,
    children: [
      { index: true, element: <HomePage /> },
      { path: "search", element: <SearchResultsPage /> },
      { path: "product/:slug", element: <ProductDetail /> },
      { path: "cart", element: <CartPage /> },
      { path: "checkout", element: <CheckoutPage /> },
      { path: "orders", element: <OrdersPage /> },
      { path: "orders/:id", element: <OrderDetail /> },
      { path: "login", element: <Login /> },
      { path: "my-orders", element: <MyOrders /> },
      { path: "returns", element: <Returns /> },
      { path: "wishlist", element: <Wishlist /> },

      // NEW: legal / info pages
      { path: "privacy-policy", element: <PrivacyPolicy /> },
      { path: "terms-of-use", element: <TermsOfUse /> },
      { path: "shipping-policy", element: <ShippingPolicy /> },

      // Admin
      {
        path: "admin",
        element: (
          <AdminGuard>
            <AdminLayout />
          </AdminGuard>
        ),
        children: [
          { index: true, element: <AdminDashboard /> },
          { path: "banners", element: <AdminBanners /> },
          { path: "coupons", element: <AdminCoupons /> },
        ],
      },
    ],
  },
]);

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
);
