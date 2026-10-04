# ApexVibe frontend

Next.js (App Router) + TypeScript + Tailwind + lucide-react.
Answers one question: **"Should we finance this invoice, and why?"**

## Run

```
npm install
npm run dev          # http://localhost:3000
```

Copy `.env.example` to `.env.local` to switch modes. With `NEXT_PUBLIC_API_MODE=mock`
(default) the risk engine and AI Risk Analyst are simulated in the browser and the UI says so.

## Demo script (mock mode)

1. **Use Demo Invoice** → review fields (PO reference is flagged *uncertain*, buyer registration *missing*) → **Run Assessment**
2. Decision: **23/100 Medium risk · Manual review · 71% complete (preliminary)**
3. Under "Bank details changed" click **Add note or document** → the notes box opens on Seller Verification.
   Type *"Supplier emailed us on 2 Oct confirming the new account"* → **Send & reassess**
4. **23 → 9, Medium → Low, −14 points**: eligible, 80% advance (£3,224); "What changed?" shows Seller Verification before/after
5. In completeness, **Add evidence** next to Purchase order → attach any file → **Send & reassess** → **9 → 5**, 100% complete

Alternative paths: a note saying the seller *never* notified a change (→ 33 High, do not finance),
a bank-letter file for Seller Verification (→ 7), or *"we don't have a PO"* (→ 27 High).
Mock mode reads notes with simple keyword rules and counts documents by file name.

## Where things are

| Path | What |
|---|---|
| `app/page.tsx` | Upload screen |
| `app/assessment/[id]/page.tsx` | Review → processing → decision |
| `components/DecisionView.tsx` | Results + analyst notes + reassessment |
| `lib/types.ts` | Data contracts the backend must return (CLAUDE.md §6) |
| `lib/api.ts` | The only place that talks to the backend (mock or live) |
| `lib/mock-engine.ts`, `lib/mock-notes.ts`, `lib/mock-data.ts` | Mock-mode stand-ins for the backend |
