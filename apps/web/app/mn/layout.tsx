import '../globals.css';
import type { ReactNode } from 'react';
import { Providers } from '../../components/Providers';
import { Header } from '../../components/Header';
import { Footer } from '../../components/Footer';

export const metadata = {
  title: 'AIVO Web (MN)',
  description: 'AIVO web app',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  const locale: 'mn' | 'en' = 'mn';
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
