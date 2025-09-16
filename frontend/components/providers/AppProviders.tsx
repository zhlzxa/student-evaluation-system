"use client";
import { PropsWithChildren } from 'react';
import { ReactQueryProvider } from './react-query';
import { CssBaseline, ThemeProvider, createTheme } from '@mui/material';
import { AppShell } from '../layout/AppShell';
import { ErrorBoundary } from './ErrorBoundary';
import { ToastProvider } from './ToastProvider';
import { AuthProvider } from '@/hooks/useAuth';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: '#1976d2' },
    error: { main: '#d32f2f', light: '#fde7e7' },
    success: { main: '#2e7d32', light: '#e7f5e8' },
    warning: { main: '#ed6c02', light: '#fff4e5' },
  },
  shape: { borderRadius: 8 },
  typography: {
    fontSize: 14,
  },
  components: {
    MuiCard: {
      defaultProps: { elevation: 0 },
      styleOverrides: {
        root: {
          borderRadius: 12,
        },
      },
    },
  },
});

export function AppProviders({ children }: PropsWithChildren) {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <ToastProvider>
          <ReactQueryProvider>
            <ThemeProvider theme={theme}>
              <CssBaseline />
              <AppShell>{children}</AppShell>
            </ThemeProvider>
          </ReactQueryProvider>
        </ToastProvider>
      </AuthProvider>
    </ErrorBoundary>
  );
}

