"use client";
import { Box, Button, Paper, Stack, TextField, Typography, Alert } from '@mui/material';
import { useMemo, useState } from 'react';
import { signIn } from 'next-auth/react';
import { useRouter, useSearchParams } from 'next/navigation';

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);

  const sessionNotice = useMemo(() => {
    const err = searchParams.get('error');
    if (!err) return null;
    // next-auth middleware redirects with error=SessionRequired when auth is needed
    if (err === 'SessionRequired') return 'Your session has expired. Please sign in again.';
    if (err === 'AccessDenied') return 'Access denied. Please sign in with an authorized account.';
    return null;
  }, [searchParams]);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    const res = await signIn('credentials', { redirect: false, email, password });
    if (res?.ok) router.push('/');
    else setError('Login failed');
  };

  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', mt: 8 }}>
      <Paper sx={{ p: 4, width: 420 }}>
        <Typography variant="h5" gutterBottom>Login</Typography>
        {sessionNotice && (
          <Alert severity="warning" sx={{ mb: 2 }}>{sessionNotice}</Alert>
        )}
        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
        <form onSubmit={onSubmit}>
          <Stack spacing={2}>
            <TextField label="Email" type="email" value={email} onChange={e=>setEmail(e.target.value)} required />
            <TextField label="Password" type="password" value={password} onChange={e=>setPassword(e.target.value)} required />
            <Button type="submit" variant="contained">Sign in</Button>
            <Button onClick={()=>router.push('/register')}>Create account</Button>
          </Stack>
        </form>
      </Paper>
    </Box>
  );
}
