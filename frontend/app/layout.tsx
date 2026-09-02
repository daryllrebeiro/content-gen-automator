import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Inter, Outfit } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const outfit = Outfit({ subsets: ["latin"], variable: "--font-outfit" });

import FaroInitializer from "../components/FaroInitializer";

export const metadata: Metadata = {
  title: "Shorts Prompt Agent | Automation Engine",
  description: "Create consistent animated YouTube Shorts prompts.",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en" className={`${inter.variable} ${outfit.variable}`}>
      <body>
        <FaroInitializer />
        {children}
      </body>
    </html>
  );
}
