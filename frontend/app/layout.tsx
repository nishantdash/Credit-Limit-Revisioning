import "./globals.css";
import type { Metadata } from "next";
import { Nav } from "./Nav";
import { TopBar } from "./TopBar";

export const metadata: Metadata = {
  title: "CLR — Intent-Driven Credit Limit Revisioning",
  description: "Real-time, intent-driven credit-limit revisioning on India's AA + DPDP + RBI rails",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="shell">
          <aside className="sidebar">
            <Nav />
          </aside>
          <div>
            <TopBar />
            <main>{children}</main>
          </div>
        </div>
      </body>
    </html>
  );
}
