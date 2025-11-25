// src/lib/api.js
import axios from "axios";
import { auth } from "./auth";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000/api/v1",
  withCredentials: true, // keep for cart session cookie
});

// Attach JWT unless the caller marks the request as public via params._public
api.interceptors.request.use((cfg) => {
  const isPublic =
    (cfg?.params && String(cfg.params._public) === "1") ||
    (cfg?.params && cfg.params._public === 1) ||
    (cfg?.params && cfg.params._public === true);

  if (!isPublic) {
    const token = auth.access?.();
    if (token) cfg.headers.Authorization = `Bearer ${token}`;
  } else if (cfg.headers?.Authorization) {
    delete cfg.headers.Authorization;
  }
  return cfg;
});

export default api;
