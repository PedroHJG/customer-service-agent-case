import { Suspense } from "react";
import type { Metadata } from "next";
import { Geist_Mono, Nunito } from "next/font/google";
import { Sidebar } from "@/components/layout/Sidebar";
import { TooltipProvider } from "@/components/ui/tooltip";
import "./globals.css";

// Sans-serif arredondada; a variável alimenta o token `font-sans` do Tailwind (globals.css)
const nunito = Nunito({
  variable: "--font-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Empório da Música · Atendimento",
  description: "Protótipo de agente de atendimento da Empório da Música",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="pt-BR" className={`${nunito.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="flex h-full overflow-hidden">
        <TooltipProvider>
          {/* Sidebar lê a rota atual (usePathname), então precisa de um boundary com cacheComponents */}
          <Suspense fallback={<aside className="w-80 shrink-0 border-r" />}>
            <Sidebar />
          </Suspense>
          <main className="min-w-0 flex-1">{children}</main>
        </TooltipProvider>
      </body>
    </html>
  );
}
