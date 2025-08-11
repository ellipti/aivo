import './globals.css';
import type { ReactNode } from 'react';

export const metadata = {
  title: 'AIVO Web',
  description: 'AIVO web app',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

