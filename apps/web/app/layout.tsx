import './globals.css';
import type { ReactNode } from 'react';
import { headers } from 'next/headers';
import { Providers } from '../components/Providers';
import { Header } from '../components/Header';
import { Footer } from '../components/Footer';

export const metadata = {
  title: 'AIVO Web',
  description: 'AIVO web app',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  const cookieHeader = headers().get('cookie') || '';
  const localeMatch = cookieHeader.match(/locale=([^;]+)/);
  const locale = (localeMatch?.[1] || 'mn') as 'mn' | 'en';

  return (
    <html lang={locale} suppressHydrationWarning>
      <body className="min-h-dvh bg-background text-foreground">
        <Providers locale={locale}>
          <Header />
          <div className="min-h-[calc(100dvh-200px)]">{children}</div>
          <Footer />
        </Providers>
      </body>
    </html>
  );
}
