"use client";
import { PropsWithChildren, useMemo } from 'react';
import { AppBar, Box, Container, CssBaseline, Drawer, List, ListItemButton, ListItemIcon, ListItemText, Toolbar, Typography, Button, CircularProgress } from '@mui/material';
import InsightsIcon from '@mui/icons-material/Insights';
import HomeIcon from '@mui/icons-material/Home';
import LogoutIcon from '@mui/icons-material/Logout';
import { usePathname, useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';

export function AppShell({ children }: PropsWithChildren) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout, loading, isAuthenticated } = useAuth();
  const drawerWidth = 260;
  
  const nav = useMemo(() => [
    { label: 'Home', icon: <HomeIcon />, href: '/assessments' },
    { label: 'Programme Criteria', icon: <InsightsIcon />, href: '/rules' },
  ], []);

  const handleLogout = () => {
    logout();
  };

  // Show login/register pages without shell
  if (pathname === '/login' || pathname === '/register') {
    return <>{children}</>;
  }

  // Show loading while checking auth
  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
        <CircularProgress />
      </Box>
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    router.push('/login');
    return null;
  }

  return (
    <Box sx={{ display: 'flex' }}>
      <CssBaseline />
      <AppBar 
        position="fixed"
        sx={{
          zIndex: (theme) => theme.zIndex.drawer + 1,
        }}
      >
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>Student Admission Review System</Typography>
          {user && (
            <Box display="flex" alignItems="center" gap={2}>
              <Typography variant="body2" color="inherit">
                {user.full_name || user.email}
              </Typography>
              <Button
                color="inherit"
                startIcon={<LogoutIcon />}
                onClick={handleLogout}
              >
                Logout
              </Button>
            </Box>
          )}
        </Toolbar>
      </AppBar>
      <Drawer
        anchor="left"
        variant="permanent"
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: drawerWidth,
            boxSizing: 'border-box',
          },
        }}
      >
        <Toolbar />
        <Box role="presentation">
          <List>
            {nav.map(item => (
              <ListItemButton key={item.href} selected={pathname === item.href} onClick={() => { router.push(item.href); }}>
                <ListItemIcon>{item.icon}</ListItemIcon>
                <ListItemText primary={item.label} />
              </ListItemButton>
            ))}
          </List>
        </Box>
      </Drawer>
      <Box component="main" sx={{ flexGrow: 1, p: 3 }}>
        <Toolbar />
        {/* Constrain content width for better readability and consistent card layout */}
        <Container maxWidth="lg" sx={{ px: 2 }}>
          {children}
        </Container>
      </Box>
    </Box>
  );
}

