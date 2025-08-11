import './globals.css';
import type { ReactNode } from 'react';
import { headers } from 'next/headers';

export const metadata = {
  title: 'AIVO Admin',
  description: 'Admin Control Panel',
};

function Shell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-dvh bg-background text-foreground">
      <header className="border-b">
        <div className="container mx-auto px-4 h-14 flex items-center justify-between">
          <a href="/" className="font-semibold">
            AIVO Admin
          </a>
          <nav className="flex gap-3 text-sm">
            <a href="/dashboard">Dashboard</a>
            <a href="/users">Users</a>
            <a href="/signals">Signals</a>
            <a href="/orders">Orders</a>
            <a href="/settings">Settings</a>
          </nav>
        </div>
      </header>
      <main className="container mx-auto px-4 py-8">{children}</main>
      <footer className="border-t mt-12">
        <div className="container mx-auto px-4 py-6 text-sm text-muted-foreground">
          © {new Date().getFullYear()} AIVO
        </div>
      </footer>
    </div>
  );
}

export default function RootLayout({ children }: { children: ReactNode }) {
  const cookieHeader = headers().get('cookie') || '';
  const localeMatch = cookieHeader.match(/locale=([^;]+)/);
  const locale = (localeMatch?.[1] || 'mn') as 'mn' | 'en';

  return (
    <html lang={locale} suppressHydrationWarning>
      <body>
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}
