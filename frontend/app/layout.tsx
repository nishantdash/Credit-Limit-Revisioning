import "./globals.css";
import type { Metadata } from "next";
import { Nav } from "./Nav";

export const metadata: Metadata = {
  title: "CLR — Credit Limit Revisioning Engine",
  description: "Continuous, event-driven, AI-personalised credit-limit management",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="layout">
          <aside className="sidebar">
            <h1>CLR</h1>
            <div className="tag">Credit Limit Revisioning</div>
            <Nav />
          </aside>
          <main>{children}</main>
        </div>
      </body>
    </html>
  );
}
