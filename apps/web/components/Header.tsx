'use client';
import Link from 'next/link';
import { useTheme } from 'next-themes';
import { useRouter } from 'next/navigation';

export function Header() {
  const { theme, setTheme } = useTheme();
  const router = useRouter();

  return (
    <header className="border-b">
      <div className="container mx-auto px-4 h-14 flex items-center justify-between">
        <Link href="/" className="font-semibold text-primary">
          AIVO AI TRADE
        </Link>
        <div className="flex items-center gap-3">
          <button
            className="text-sm border rounded-md px-2 py-1"
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          >
            {theme === 'dark' ? 'Light' : 'Dark'}
          </button>
          <button
            className="text-sm border rounded-md px-2 py-1"
            onClick={() => {
              document.cookie = `locale=mn; path=/`;
              router.refresh();
            }}
          >
            MN
          </button>
          <button
            className="text-sm border rounded-md px-2 py-1"
            onClick={() => {
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
