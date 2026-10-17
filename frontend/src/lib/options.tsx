import { createContext, useContext, type ReactNode } from "react";
import { api } from "../services/functions.service";
import { useResource } from "./useResource";
import type { AppOptions } from "../types";

/** Allowed values and their display labels come from the backend (GET /api/options); nothing is listed here. */
const OptionsContext = createContext<AppOptions | null>(null);

export function OptionsProvider({ children }: { children: ReactNode }) {
  // Never blocks: until options arrive (or if the API is down), pages show their own loading/error states and
  // values are shown as written.
  const options = useResource(() => api.options(), []);
  return <OptionsContext.Provider value={options.data ?? null}>{children}</OptionsContext.Provider>;
}

export type EnumGroup = keyof AppOptions["labels"] & keyof AppOptions["enums"];

const humanize = (value: string) => {
  const text = value.replaceAll("_", " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
};

/** (group, value) → display label from the backend, or the value humanized if no label exists. */
export function useLabel(): (group: EnumGroup, value: string | null | undefined) => string {
  const options = useContext(OptionsContext);
  return (group, value) => (value ? options?.labels[group]?.[value] ?? humanize(value) : "—");
}

/** Allowed values of a group in the backend's order (empty until loaded). */
export function useEnum(group: EnumGroup): string[] {
  const options = useContext(OptionsContext);
  const values = options?.enums[group];
  return Array.isArray(values) ? values : [];
}

export function useOptionsData(): AppOptions | null {
  return useContext(OptionsContext);
}

/** <option>s for a backend enum. The current value is always included so a select never shows a wrong choice. */
export function EnumOptions({ group, current }: { group: EnumGroup; current?: string }) {
  const values = useEnum(group);
  const label = useLabel();
  const list = current && !values.includes(current) ? [current, ...values] : values;
  return (
    <>
      {list.map((value) => (
        <option key={value} value={value}>
          {label(group, value)}
        </option>
      ))}
    </>
  );
}

export function EnumLabel({ group, value }: { group: EnumGroup; value: string | null | undefined }) {
  return <>{useLabel()(group, value)}</>;
}
