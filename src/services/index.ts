import { demoStudioApi } from "./demoStudioApi";
import type { StudioApi } from "./studioApi";

export type { StudioApi, DataSourceMode } from "./studioApi";

/**
 * The single data source used by the whole app.
 *
 * Today this is the bundled demo data. When Booski Core is available, implement
 * `StudioApi` against it (e.g. `liveStudioApi.ts`) and change this line.
 */
export const studioApi: StudioApi = demoStudioApi;
