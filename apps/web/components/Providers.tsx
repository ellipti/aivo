'use client';
import { ReactNode } from 'react';
import { NextIntlClientProvider } from 'next-intl';
import { ThemeProvider } from 'next-themes';
import mn from '../i18n/mn.json';
import en from '../i18n/en.json';
import { ToastProvider } from './Toast';

export function Providers({ children, locale }: { children: ReactNode; locale: 'mn' | 'en' }) {
  const messages = locale === 'mn' ? mn : en;
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      <NextIntlClientProvider locale={locale} messages={messages as any}>
        <ToastProvider>{children}</ToastProvider>
      </NextIntlClientProvider>
    </ThemeProvider>
  );
}
