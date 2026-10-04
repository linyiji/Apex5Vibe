import type { components } from "./backend-schema";

export type Workspace = components["schemas"]["Workspace"];
export type Module = components["schemas"]["ModuleView"];
export type ModuleKey = components["schemas"]["ModuleKey"];
export type PartySelection = components["schemas"]["PartySelection"];
export type PartyResolution = components["schemas"]["PartyResolution"];
export type Capabilities = components["schemas"]["Capabilities"];
export type Entity = components["schemas"]["EntityList"]["items"][number];
export type QueuePage = components["schemas"]["QueuePage"];
export type Accepted = components["schemas"]["MutationAccepted"];
export type RunDetail = components["schemas"]["RunDetail"];
export type EventPage = components["schemas"]["EventPage"];
export type Snapshot = NonNullable<Workspace["aggregate"]["current_result"]>;

export const MODULE_NAMES: Record<ModuleKey, string> = {
  invoice_integrity: "Invoice Integrity",
  buyer_verification: "Buyer Verification",
  seller_verification: "Seller Verification",
  relationship: "Buyer–Seller Relationship",
  market_price: "Product & Market Price",
  payment_history: "Payment History",
  duplicate_financing: "Duplicate Financing",
};

export function amount(value: string | null | undefined, currency = "GBP") {
  if (value == null) return "—";
  // Display the server's decimal amount; never calculate a financing offer in the browser.
  const [integer, fraction = "00"] = value.split(".");
  return `${currency} ${integer.replace(/\B(?=(\d{3})+(?!\d))/g, ",")}.${fraction.padEnd(2, "0")}`;
}

export function validateFiles(
  files: File[],
  capabilities: Capabilities,
  invoice = false,
) {
  if (!files.length) throw new Error("Choose a file first.");
  if (files.length > (invoice ? 1 : capabilities.max_files_per_request))
    throw new Error("Too many files selected.");
  const supported = invoice
    ? [".pdf"]
    : capabilities.formats
        .filter((f) => f.status === "ready")
        .map((f) => f.extension);
  for (const file of files) {
    const extension = `.${file.name.split(".").pop()?.toLowerCase()}`;
    if (!supported.includes(extension))
      throw new Error(
        `${file.name}: supported formats are ${supported.join(", ")}.`,
      );
    if (!file.size || file.size > capabilities.max_file_bytes)
      throw new Error(
        `${file.name}: file must be between 1 byte and ${capabilities.max_file_bytes / 1024 / 1024} MiB.`,
      );
  }
}
