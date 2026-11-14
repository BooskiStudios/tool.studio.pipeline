import { previewApi } from "./demoStudioApi";
import type { PreviewApi } from "./studioApi";

export type { PreviewApi } from "./studioApi";

/**
 * Preview content for screens awaiting later phases (agents, usage, integrations…). Live studio data
 * comes from Booski Core through `src/api` instead.
 */
export const studioApi: PreviewApi = previewApi;
