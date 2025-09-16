import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Simple middleware that just allows all requests through
// Authentication is handled client-side with our useAuth hook
export function middleware(request: NextRequest) {
  return NextResponse.next();
}

// Only run middleware on relevant paths
export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
};

