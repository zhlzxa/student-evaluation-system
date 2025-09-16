"use client";
import { Box, Button, Paper, Stack, TextField, Typography, Alert } from '@mui/material';
import { useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { useRouter } from 'next/navigation';

export default function RegisterPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [invite, setInvite] = useState('');
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/auth/register`, {
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, full_name: fullName, invite_code: invite }),
      });
      
      if (!res.ok) {
        const errorData = await res.json().catch(() => null);
        const errorMessage = errorData?.detail || 'Registration failed. Please try again.';
        setError(errorMessage);
        return;
      }
      
      // Auto login after successful registration
      try {
        await login(email, password);
        // Redirect will be handled by the login function
      } catch {
        setError('Registration successful, but auto login failed. Please login manually.');
        router.push('/login');
      }
    } catch {
      setError('Network error. Please check your connection and try again.');
    }
  };

  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', mt: 8 }}>
      <Paper sx={{ p: 4, width: 480 }}>
        <Typography variant="h5" gutterBottom>Register</Typography>
        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
        <form onSubmit={onSubmit}>
          <Stack spacing={2}>
            <TextField label="Full name" value={fullName} onChange={e=>setFullName(e.target.value)} required />
            <TextField label="Email" type="email" value={email} onChange={e=>setEmail(e.target.value)} required />
            <TextField label="Password" type="password" value={password} onChange={e=>setPassword(e.target.value)} required />
            <TextField 
              label="Invite code" 
              value={invite} 
              onChange={e=>setInvite(e.target.value)} 
              required 
              helperText="Please enter the invite code provided to you" 
            />
            <Button type="submit" variant="contained">Create account</Button>
            <Button onClick={()=>router.push('/login')}>Back to login</Button>
          </Stack>
        </form>
      </Paper>
    </Box>
  );
}
