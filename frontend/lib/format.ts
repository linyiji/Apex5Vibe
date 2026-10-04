import type { ModuleStatus, Recommendation, RiskBand } from "./types";

/** Parses "£4,030.00" / "4030" / "4,030" into a number, or null. */
export function parseAmount(value: string | null): number | null {
  if (!value) return null;
  const n = Number(value.replace(/[^0-9.-]/g, ""));
  return Number.isFinite(n) && value.match(/\d/) ? n : null;
}

const SYMBOLS: Record<string, string> = { GBP: "£", USD: "$", HKD: "HK$", EUR: "€" };

export function money(amount: number | null, currency: string | null, decimals = 0): string {
  if (amount === null) return "—";
  const code = (currency || "").toUpperCase();
  const formatted = amount.toLocaleString("en-GB", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
  return SYMBOLS[code] ? `${SYMBOLS[code]}${formatted}` : `${formatted}${code ? " " + code : ""}`;
}

export function formatDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

export const BAND_LABEL: Record<RiskBand, string> = {
  low: "Low risk",
  medium: "Medium risk",
  high: "High risk",
};

export const RECOMMENDATION_LABEL: Record<Recommendation, string> = {
  eligible: "Eligible",
  manual_review: "Manual review",
  decline: "Do not finance",
};

/** Tailwind text colour per band / module status. Red is reserved for significant risk. */
export const BAND_TEXT: Record<RiskBand, string> = {
  low: "text-ok",
  medium: "text-warn",
  high: "text-risk",
};

export const STATUS_TEXT: Record<ModuleStatus, string> = {
  clear: "text-ok",
  watch: "text-warn",
  risk: "text-risk",
};
