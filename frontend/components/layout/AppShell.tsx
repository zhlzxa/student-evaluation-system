"use client";
import { PropsWithChildren, useMemo } from 'react';
import { AppBar, Box, Container, CssBaseline, Drawer, List, ListItemButton, ListItemIcon, ListItemText, Toolbar, Typography, Button } from '@mui/material';
import DashboardIcon from '@mui/icons-material/Dashboard';
import RuleIcon from '@mui/icons-material/Rule';
import HistoryIcon from '@mui/icons-material/History';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import LogoutIcon from '@mui/icons-material/Logout';
import { usePathname, useRouter } from 'next/navigation';
import { signOut, useSession } from 'next-auth/react';

export function AppShell({ children }: PropsWithChildren) {
  const pathname = usePathname();
  const router = useRouter();
  const { data: session } = useSession();
  const drawerWidth = 260;
  
  const nav = useMemo(() => [
    { label: 'Dashboard', icon: <DashboardIcon />, href: '/' },
    { label: 'New Assessment', icon: <AddCircleOutlineIcon />, href: '/assessments/new' },
    { label: 'Evaluation History', icon: <HistoryIcon />, href: '/assessments' },
    { label: 'Rules', icon: <RuleIcon />, href: '/rules' },
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
        <Container maxWidth={false} disableGutters>
          {children}
        </Container>
      </Box>
    </Box>
  );
}

