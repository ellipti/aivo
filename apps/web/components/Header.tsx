'use client';
import Link from 'next/link';
import { useTheme } from 'next-themes';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import type { Route } from 'next';

export function Header() {
  const { theme, setTheme } = useTheme();
  const router = useRouter();
  const t = useTranslations();

  return (
    <header className="border-b">
      <div className="container mx-auto px-4 h-14 flex items-center justify-between">
        <Link href="/" className="font-semibold text-primary">
          {t('nav.brand')}
        </Link>
        <div className="flex items-center gap-3">
          <nav className="hidden sm:flex items-center gap-3">
            <Link href="/login" className="text-sm hover:underline">
              {t('nav.login')}
            </Link>
            <Link href={'/admin' as Route} className="text-sm hover:underline">
              {t('nav.admin')}
            </Link>
          </nav>
          <button
            className="text-sm border rounded-md px-2 py-1"
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          >
            {theme === 'dark' ? 'Light' : 'Dark'}
          </button>
          <button
            className="text-sm border rounded-md px-2 py-1"
            onClick={() => {
              try {
                localStorage.setItem('locale', 'mn');
              } catch (e) {
                // ignore
              }
              document.cookie = `locale=mn; path=/`;
              router.refresh();
            }}
          >
            MN
          </button>
          <button
            className="text-sm border rounded-md px-2 py-1"
            onClick={() => {
              try {
                localStorage.setItem('locale', 'en');
              } catch (e) {
                // ignore
              }
              document.cookie = `locale=en; path=/`;
              router.refresh();
            }}
          >
            EN
          </button>
        </div>
      </div>
    </header>
  );
}
