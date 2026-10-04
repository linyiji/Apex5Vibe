import type { Entity, PartySelection } from "@/lib/backend-types";

export const control =
  "w-full rounded-lg border border-line bg-bg px-3 py-2 text-sm text-text disabled:opacity-50 focus:outline-accent";
export const button =
  "rounded-lg border border-line px-4 py-2 text-sm hover:border-accent disabled:opacity-40 disabled:cursor-not-allowed";
export const primary = `${button} bg-accent text-bg font-semibold border-accent`;

export default function PartyPicker({
  side,
  value,
  onChange,
  entities,
  disabled,
}: {
  side: "Buyer" | "Seller";
  value: PartySelection;
  onChange: (value: PartySelection) => void;
  entities: Entity[];
  disabled?: boolean;
}) {
  return (
    <fieldset
      disabled={disabled}
      className="space-y-3 rounded-xl border border-line bg-surface p-4"
    >
      <legend className="px-1 text-sm font-medium">{side}</legend>
      <label className="block text-xs text-muted">
        {side} selection
        <select
          aria-label={`${side} selection`}
          className={`${control} mt-1`}
          value={value.mode}
          onChange={(e) =>
            onChange(
              e.target.value === "skip"
                ? { mode: "skip" }
                : e.target.value === "existing"
                  ? {
                      mode: "existing",
                      entity_id: entities[0]?.entity_id ?? "",
                    }
                  : { mode: "manual", legal_name: "" },
            )
          }
        >
          <option value="skip">Skip — identify from invoice</option>
          <option value="existing">Select existing</option>
          <option value="manual">Manual</option>
        </select>
      </label>
      {value.mode === "skip" && (
        <p className="text-xs text-muted">
          The invoice will identify and link the {side.toLowerCase()}.
        </p>
      )}
      {value.mode === "existing" && (
        <label className="block text-xs text-muted">
          {side} company
          <select
            required
            aria-label={`${side} company`}
            className={`${control} mt-1`}
            value={value.entity_id}
            onChange={(e) =>
              onChange({ mode: "existing", entity_id: e.target.value })
            }
          >
            {entities.map((entity) => (
              <option key={entity.entity_id} value={entity.entity_id}>
                {entity.legal_name}
              </option>
            ))}
          </select>
        </label>
      )}
      {value.mode === "manual" && (
        <div className="space-y-2">
          <input
            required
            aria-label={`${side} company name`}
            placeholder="Company name"
            className={control}
            value={value.legal_name}
            onChange={(e) => onChange({ ...value, legal_name: e.target.value })}
          />
          <input
            aria-label={`${side} registration number`}
            placeholder="Registration number (optional)"
            className={control}
            value={value.tax_id ?? ""}
            onChange={(e) =>
              onChange({ ...value, tax_id: e.target.value || undefined })
            }
          />
          <input
            aria-label={`${side} country`}
            placeholder="Country (optional)"
            className={control}
            value={value.country ?? ""}
            onChange={(e) =>
              onChange({ ...value, country: e.target.value || undefined })
            }
          />
        </div>
      )}
    </fieldset>
  );
}
