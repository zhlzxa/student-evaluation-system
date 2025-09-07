import NextAuth from 'next-auth';
import Credentials from 'next-auth/providers/credentials';

const backend = process.env.NEXT_PUBLIC_BACKEND_BASE_URL!;

const authOptions = {
  session: { strategy: 'jwt' },
  pages: {
    signIn: '/login',
    error: '/login',
  },
  providers: [
    Credentials({
      name: 'Credentials',
      credentials: {
        email: { label: 'Email', type: 'email' },
        password: { label: 'Password', type: 'password' },
      },
      async authorize(cred) {
        if (!cred?.email || !cred?.password) return null;
        
        try {
          const res = await fetch(`${backend}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: cred.email, password: cred.password }),
          });
          
          if (!res.ok) {
            console.error('Login failed:', res.status, res.statusText);
            return null;
          }
          
          const data = await res.json();
          return {
            id: String(data.user.id),
            email: data.user.email,
            name: data.user.full_name,
            access_token: data.access_token,
          } as any;
        } catch (error) {
          console.error('Login error:', error);
          return null;
        }
      },
    }),
  ],
  callbacks: {
    async jwt(params: any) {
      const { token, user } = params;
      if (user) {
        token.access_token = (user as any).access_token;
        token.email = user.email;
        token.name = user.name;
      }
      return token as any;
    },
    async session(params: any) {
      const { session, token } = params;
      (session as any).access_token = (token as any).access_token;
      session.user = {
        email: token.email,
        name: token.name,
      };
      return session;
    },
    async redirect({ url, baseUrl }: { url: string, baseUrl: string }) {
      if (url.startsWith('/')) return `${baseUrl}${url}`;
      if (new URL(url).origin === baseUrl) return url;
      return baseUrl;
    },
  },
  events: {
    async signOut() {
      console.log('User signed out');
    },
    async session() {
    },
  },
};

const handler = NextAuth(authOptions as any);
export { handler as GET, handler as POST };
