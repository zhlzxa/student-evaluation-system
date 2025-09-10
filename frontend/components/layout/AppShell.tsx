"use client";
import { PropsWithChildren, useMemo } from 'react';
import { AppBar, Box, Container, CssBaseline, Drawer, List, ListItemButton, ListItemIcon, ListItemText, Toolbar, Typography, Button } from '@mui/material';
import InsightsIcon from '@mui/icons-material/Insights';
import HomeIcon from '@mui/icons-material/Home';
import LogoutIcon from '@mui/icons-material/Logout';
import { usePathname, useRouter } from 'next/navigation';
import { signOut, useSession } from 'next-auth/react';

export function AppShell({ children }: PropsWithChildren) {
  const pathname = usePathname();
  const router = useRouter();
  const { data: session } = useSession();
  const drawerWidth = 260;
  
  const nav = useMemo(() => [
    { label: 'Home', icon: <HomeIcon />, href: '/assessments' },
    { label: 'Metrics', icon: <InsightsIcon />, href: '/rules' },
  ], []);

  const handleLogout = async () => {
    await signOut({ callbackUrl: '/login' });
  };

  if (pathname === '/login' || pathname === '/register') {
    return <>{children}</>;
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
          <Typography variant="h6" sx={{ flexGrow: 1 }}>Student Evaluation System</Typography>
          {session && (
            <Button 
              color="inherit" 
              startIcon={<LogoutIcon />} 
              onClick={handleLogout}
            >
              Logout
            </Button>
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

