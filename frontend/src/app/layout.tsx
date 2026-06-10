import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ArthaOS",
  description: "Financial operating system for India's independent businesses.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
