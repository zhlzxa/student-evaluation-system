"use client";
import { PropsWithChildren, useMemo } from 'react';
import { AppBar, Box, Container, CssBaseline, Drawer, IconButton, List, ListItemButton, ListItemIcon, ListItemText, Toolbar, Typography, Button } from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import DashboardIcon from '@mui/icons-material/Dashboard';
import RuleIcon from '@mui/icons-material/Rule';
import HistoryIcon from '@mui/icons-material/History';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import LogoutIcon from '@mui/icons-material/Logout';
import { usePathname, useRouter } from 'next/navigation';
import { useState } from 'react';
import { signOut, useSession } from 'next-auth/react';

export function AppShell({ children }: PropsWithChildren) {
  const pathname = usePathname();
  const router = useRouter();
  const { data: session } = useSession();
  const [open, setOpen] = useState(false);
  
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
      <AppBar position="fixed">
        <Toolbar>
          <IconButton color="inherit" edge="start" onClick={() => setOpen(true)}>
            <MenuIcon />
          </IconButton>
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
      <Drawer anchor="left" open={open} onClose={() => setOpen(false)}>
        <Box role="presentation" sx={{ width: 260 }}>
          <List>
            {nav.map(item => (
              <ListItemButton key={item.href} selected={pathname === item.href} onClick={() => { router.push(item.href); setOpen(false); }}>
                <ListItemIcon>{item.icon}</ListItemIcon>
                <ListItemText primary={item.label} />
              </ListItemButton>
            ))}
          </List>
        </Box>
      </Drawer>
      <Box component="main" sx={{ flexGrow: 1, p: 3 }}>
        <Toolbar />
        <Container maxWidth="lg">
          {children}
        </Container>
      </Box>
    </Box>
  );
}

