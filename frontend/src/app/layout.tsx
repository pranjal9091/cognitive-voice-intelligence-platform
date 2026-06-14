import type { Metadata } from "next";
import { Outfit } from "next/font/google";
import "./globals.css";

const outfit = Outfit({ 
  subsets: ["latin"],
  variable: "--font-outfit"
});

export const metadata: Metadata = {
  title: "Cognitive Voice Platform - Assessment Dashboard",
  description: "Voice Intelligence Platform for Speech & Linguistic Analytics & Cognitive Risk Evaluation",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${outfit.variable}`}>
      <body className="antialiased bg-background text-foreground min-h-screen">
        {children}
      </body>
    </html>
  );
}
