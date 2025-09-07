"use client";
import { PropsWithChildren } from 'react';
import { SessionProvider } from 'next-auth/react';
import { ReactQueryProvider } from './react-query';
import { CssBaseline, ThemeProvider, createTheme } from '@mui/material';
import { AppShell } from '../layout/AppShell';
import { ErrorBoundary } from './ErrorBoundary';
import { ToastProvider } from './ToastProvider';

const theme = createTheme({ palette: { mode: 'light', primary: { main: '#1976d2' } } });

export function AppProviders({ children }: PropsWithChildren) {
  return (
    <ErrorBoundary>
      <SessionProvider>
        <ToastProvider>
          <ReactQueryProvider>
            <ThemeProvider theme={theme}>
              <CssBaseline />
              <AppShell>{children}</AppShell>
            </ThemeProvider>
          </ReactQueryProvider>
        </ToastProvider>
      </SessionProvider>
    </ErrorBoundary>
  );
}

