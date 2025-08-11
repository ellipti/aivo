import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const isAuthed = request.cookies.get('auth')?.value === '1';
  const pathname = request.nextUrl.pathname;
  const isProtected = pathname.startsWith('/dashboard') || pathname.startsWith('/analyze');

  if (isProtected && !isAuthed) {
    const url = new URL('/login', request.url);
    url.searchParams.set('next', pathname);
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next|api|.*\\..*).*)'],
};
