export { default } from 'next-auth/middleware';

export const config = {
  matcher: ['/((?!login|register|_next|api|favicon.ico).*)'],
};

