import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Header from "@/components/Header";
import { API_MODE } from "@/lib/runtime-config";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Apex5Vibe — Invoice Financing Assessment",
  description: "AI-powered invoice financing risk assessment",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col font-sans">
        <Header />
        <main className="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-8 py-8">{children}</main>
        <footer className="w-full max-w-7xl mx-auto px-4 sm:px-8 pb-8 flex flex-wrap justify-between gap-2 text-xs text-faint">
          <span>
            {API_MODE === "mock"
              ? "Demo: simulated assessment engine and synthetic reference data. No backend connected."
              : "Live AI assessment · synthetic local reference data · demonstration only."}
          </span>
          <span className="font-medium text-muted">Evidence informs · AI assesses · Analyst reviews</span>
        </footer>
      </body>
    </html>
  );
}
