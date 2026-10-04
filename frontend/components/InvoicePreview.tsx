import { DEMO_TOTALS } from "@/lib/mock-data";
import { formatDate, money, parseAmount } from "@/lib/format";
import type { ExtractedInvoice } from "@/lib/types";

interface Props {
  invoice: ExtractedInvoice;
  /** Object URL of the uploaded file, when there is one. */
  preview: { url: string; kind: "pdf" | "image" } | null;
}

/** Shows the uploaded file, or a rendering of the demo invoice when there's no file. */
export default function InvoicePreview({ invoice, preview }: Props) {
  if (preview) {
    return (
      <div className="rounded-xl bg-white overflow-hidden h-[70vh] min-h-[480px] grid place-items-center">
        {preview.kind === "image" ? (
          // eslint-disable-next-line @next/next/no-img-element -- local object URL, not optimisable
          <img src={preview.url} alt="Uploaded invoice" className="max-w-full max-h-full object-contain" />
        ) : (
          <embed src={preview.url} type="application/pdf" className="w-full h-full" />
        )}
      </div>
    );
  }

  const f = invoice.fields;
  const cur = f.currency.value;
  return (
    <div className="rounded-xl bg-[#f6f7f8] text-slate-800 p-6 sm:p-8 text-[13px] leading-relaxed min-h-[480px]">
      <div className="flex justify-between gap-4 border-b border-slate-300 pb-4 mb-5">
        <div>
          <div className="text-2xl font-bold text-slate-900 tracking-tight">INVOICE</div>
          <div className="text-slate-500">{f.invoice_number.value}</div>
        </div>
        <div className="text-right">
          <div className="font-semibold">{f.seller.value}</div>
          <div className="text-slate-500">18 Shoreditch High Street, London</div>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-6">
        <div>
          <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1">Bill to</div>
          <div className="font-semibold">{f.buyer.value}</div>
          <div>22 Rivington Street</div>
          <div>London EC2A 3DU</div>
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1">Details</div>
          <div>Issue: {formatDate(f.invoice_date.value)}</div>
          <div>Due: {formatDate(f.due_date.value)}</div>
          <div>Your ref: <span className="blur-[0.4px]">P0-20931</span></div>
        </div>
      </div>
      <table className="w-full mt-6">
        <thead>
          <tr className="text-[10px] uppercase text-slate-500 border-b border-slate-300">
            <th className="text-left py-2 font-medium">Description</th>
            <th className="text-right py-2 font-medium">Qty</th>
            <th className="text-right py-2 font-medium">Unit</th>
            <th className="text-right py-2 font-medium">Amount</th>
          </tr>
        </thead>
        <tbody className="num">
          {invoice.line_items.map((li) => (
            <tr key={li.description} className="border-b border-slate-200">
              <td className="py-2">{li.description}</td>
              <td className="py-2 text-right">{li.quantity}</td>
              <td className="py-2 text-right">{money(li.unit_price, cur)}</td>
              <td className="py-2 text-right">{money(li.amount, cur)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="ml-auto w-1/2 mt-4 num space-y-1">
        <div className="flex justify-between"><span>Subtotal</span><span>{money(DEMO_TOTALS.subtotal, cur)}</span></div>
        <div className="flex justify-between"><span>Discount</span><span>−{money(DEMO_TOTALS.discount, cur)}</span></div>
        <div className="flex justify-between"><span>Tax</span><span>{money(DEMO_TOTALS.tax, cur)}</span></div>
        <div className="flex justify-between text-base font-bold border-t border-slate-300 pt-2 mt-2">
          <span>Total</span><span>{money(parseAmount(f.amount.value), cur, 2)}</span>
        </div>
      </div>
      <div className="mt-8 text-slate-500 text-xs">
        Pay to: Adaeze Okonkwo Studio · Sort code 20-45-77 · Account 6119 4821
      </div>
    </div>
  );
}
