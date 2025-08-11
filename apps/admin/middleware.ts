import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const isAdmin = request.cookies.get('role')?.value === 'admin';
  const pathname = request.nextUrl.pathname;
  const isProtected = !pathname.startsWith('/api') && pathname !== '/login';
  if (isProtected && !isAdmin) {
    const url = new URL('/login', request.url);
    url.searchParams.set('next', pathname);
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next|api|.*\\..*).*)'],
};
