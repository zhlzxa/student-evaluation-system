"use client";
import { Box, Button, Typography, Alert, Container } from '@mui/material';
import { useAuth } from '@/hooks/useAuth';

interface AuthErrorProps {
  error?: string;
  title?: string;
  message?: string;
}

export function AuthError({
  error = 'authentication_error',
  title = 'Authentication Error',
  message = 'There was a problem with authentication. Please try logging in again.'
}: AuthErrorProps) {
  const { logout } = useAuth();

  const handleLoginRedirect = () => {
    logout();
  };

  return (
    <Container maxWidth="sm">
      <Box 
        sx={{ 
          display: 'flex', 
          flexDirection: 'column', 
          alignItems: 'center', 
          justifyContent: 'center',
          minHeight: '60vh',
          gap: 3 
        }}
      >
        <Typography variant="h4" component="h1" gutterBottom>
          {title}
        </Typography>
        
        <Alert severity="error" sx={{ width: '100%' }}>
          {message}
          {error && (
            <Box sx={{ mt: 1, fontSize: '0.875rem', opacity: 0.8 }}>
              Error code: {error}
            </Box>
          )}
        </Alert>

        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          <Button 
            variant="contained" 
            onClick={handleLoginRedirect}
          >
            Go to Login
          </Button>
          <Button 
            variant="outlined" 
            onClick={() => window.location.reload()}
          >
            Retry
          </Button>
        </Box>
      </Box>
    </Container>
  );
}
