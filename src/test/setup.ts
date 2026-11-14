import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";
import { setCsrfToken } from "../api/client";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  setCsrfToken(null);
  document.cookie = "__Host-booski_csrf=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/; secure";
  window.localStorage.clear();
});
