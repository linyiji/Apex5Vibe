"use client";

import { CircleAlert, CircleCheck, CircleDashed, Pencil } from "lucide-react";
import type { FieldStatus, InvoiceField, InvoiceFieldKey } from "@/lib/types";

const FIELDS: { key: InvoiceFieldKey; label: string; wide?: boolean; right?: boolean }[] = [
  { key: "seller", label: "Seller", wide: true },
  { key: "buyer", label: "Buyer", wide: true },
  { key: "buyer_registration", label: "Buyer registration no." },
  { key: "invoice_number", label: "Invoice number" },
  { key: "invoice_date", label: "Invoice date" },
  { key: "due_date", label: "Due date" },
  { key: "amount", label: "Amount", right: true },
  { key: "currency", label: "Currency" },
  { key: "bank_account", label: "Bank account" },
  { key: "po_reference", label: "PO reference" },
];

const STATUS: Record<FieldStatus, { icon: typeof CircleCheck; cls: string; label: string }> = {
  extracted: { icon: CircleCheck, cls: "text-ok", label: "Extracted" },
  uncertain: { icon: CircleAlert, cls: "text-warn", label: "Uncertain: please check" },
  missing: { icon: CircleDashed, cls: "text-faint", label: "Not found" },
  edited: { icon: Pencil, cls: "text-accent-2", label: "Edited by you" },
};

interface Props {
  fields: Record<InvoiceFieldKey, InvoiceField>;
  onChange: (key: InvoiceFieldKey, value: string) => void;
}

export default function InvoiceFieldsForm({ fields, onChange }: Props) {
  return (
    <div>
      <ul className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted mb-5">
        {(Object.keys(STATUS) as FieldStatus[]).map((s) => {
          const { icon: Icon, cls, label } = STATUS[s];
          return (
            <li key={s} className="flex items-center gap-1.5">
              <Icon size={13} className={cls} /> {label.split(":")[0]}
            </li>
          );
        })}
      </ul>

      <div className="grid sm:grid-cols-2 gap-x-6 gap-y-4">
        {FIELDS.map(({ key, label, wide, right }) => {
          const field = fields[key];
          const { icon: Icon, cls, label: statusLabel } = STATUS[field.status];
          const border =
            field.status === "uncertain" ? "border-warn/60" : field.status === "missing" ? "border-dashed border-line-strong" : "border-line";
          return (
            <label key={key} className={wide ? "sm:col-span-2" : ""}>
              <span className="flex items-center justify-between text-xs text-muted mb-1.5">
                {label}
                <span className={`flex items-center gap-1 ${cls}`} title={field.source ? `Found in document: “${field.source}”` : statusLabel}>
                  <Icon size={13} />
                  <span className="sr-only">{statusLabel}</span>
                </span>
              </span>
              <input
                value={field.value ?? ""}
                placeholder="Not found — add if known"
                onChange={(e) => onChange(key, e.target.value)}
                className={`w-full bg-surface border rounded-lg px-3 py-2 text-[15px] outline-none focus:border-accent placeholder:text-faint ${border} ${right ? "text-right num" : ""}`}
              />
              {field.status === "uncertain" && field.source && (
                <span className="block mt-1 text-xs text-warn/90">Read as “{field.source.replace(/^.*?:\s*/, "")}”</span>
              )}
            </label>
          );
        })}
      </div>
    </div>
  );
}
