import { QueryClient } from "@tanstack/react-query";
import { isApiError } from "./client";

/** Retry only failures that might go away by themselves (network blips, 5xx), never 4xx answers. */
export function shouldRetry(failureCount: number, error: unknown): boolean {
  if (failureCount >= 2) return false;
  if (isApiError(error)) return error.kind === "network" || error.kind === "server";
  return false;
}

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000, // data counts as fresh for 30 s; after that it refreshes in the background
        retry: shouldRetry,
        refetchOnWindowFocus: true,
      },
      mutations: { retry: false },
    },
  });
}
