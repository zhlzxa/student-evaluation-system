"use client";
import { useState } from 'react';
import { useApi } from '../../lib/api';
import { useQuery } from '@tanstack/react-query';
import {
  Button,
  Chip,
  Stack,
  Typography,
  Card,
  Box,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  TableSortLabel,
  Menu,
  MenuItem
} from '@mui/material';
import { Assessment, Visibility, Schedule, CheckCircle, HourglassEmpty, Cancel, Delete, Add, MoreVert } from '@mui/icons-material';
import { formatLocalDateTime } from '../../lib/date';
import { useRouter } from 'next/navigation';

export default function AdmissionReviewHistoryPage() {
  const api = useApi();
  const router = useRouter();
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [admissionReviewToDelete, setAdmissionReviewToDelete] = useState<any>(null);
  const [orderBy, setOrderBy] = useState<'status' | 'started' | null>('started');
  const [order, setOrder] = useState<'asc' | 'desc'>('desc');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [statusMenuAnchor, setStatusMenuAnchor] = useState<null | HTMLElement>(null);
  
  const { data, refetch } = useQuery({
    queryKey: ['runs-list'],
    queryFn: async () => {
      const r = await api('/assessments/runs?visible_only=true');
      return r.ok ? r.json() : [];
    },
  });

  const handleDeleteClick = (evaluation: any) => {
    setAdmissionReviewToDelete(evaluation);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!admissionReviewToDelete) return;
    
    try {
      const response = await api(`/assessments/runs/${admissionReviewToDelete.id}`, {
        method: 'DELETE',
      });
      
      if (response.ok) {
        // Refresh the data after successful deletion
        refetch();
        setDeleteDialogOpen(false);
        setAdmissionReviewToDelete(null);
      } else {
        console.error('Failed to delete evaluation');
      }
    } catch (error) {
      console.error('Error deleting evaluation:', error);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteDialogOpen(false);
    setAdmissionReviewToDelete(null);
  };
  const getStatusIcon = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'completed': return <CheckCircle color="success" />;
      case 'running': case 'in_progress': case 'processing': return <HourglassEmpty color="info" />;
      case 'failed': case 'error': return <Cancel color="error" />;
      default: return <Schedule color="action" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'completed': return 'success';
      case 'running': case 'in_progress': case 'processing': return 'info';
      case 'failed': case 'error': return 'error';
      default: return 'default';
    }
  };

  const handleRequestSort = (key: 'status' | 'started') => {
    if (orderBy === key) {
      setOrder(order === 'asc' ? 'desc' : 'asc');
    } else {
      setOrderBy(key);
      setOrder('asc');
    }
  };

  const normalizeStatus = (s: string) => (s || '').toLowerCase();
  // Map各种后端状态到规范集合，确保筛选菜单稳定
  const canonicalizeStatus = (s: string): 'pending' | 'processing' | 'completed' | 'failed' => {
    const v = normalizeStatus(s);
    if (v === 'completed') return 'completed';
    if (v === 'failed' || v === 'error') return 'failed';
    if (v === 'running' || v === 'in_progress' || v === 'processing') return 'processing';
    return 'pending';
  };
  const CANONICAL_STATUS_ORDER: Array<'processing'|'completed'|'failed'> = ['processing','completed','failed'];
  const displayStatus = (c: string) => c; // keep backend naming


  const filteredAndSorted = (Array.isArray(data) ? data : [])
    .filter((evaluation: any) => {
      const status = canonicalizeStatus(evaluation.status);
      if (statusFilter !== 'all' && status !== statusFilter) return false;
      return true;
    })
    .sort((a: any, b: any) => {
      if (!orderBy) return 0;
      const dir = order === 'asc' ? 1 : -1;
      if (orderBy === 'status') {
        const av = canonicalizeStatus(a.status);
        const bv = canonicalizeStatus(b.status);
        return av.localeCompare(bv) * dir;
      } else {
        const av = new Date(a.created_at).getTime();
        const bv = new Date(b.created_at).getTime();
        return (av - bv) * dir;
      }
    });

  return (
    <Box
      sx={{
        minHeight: '100vh',
        backgroundColor: '#ffffff',
        py: 4,
        px: { xs: 2, sm: 4, md: 6, lg: 8 }
      }}
    >
          <Stack spacing={4}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
            <Box>
              <Typography 
                variant="h4" 
                component="h1" 
                sx={{ 
                  fontWeight: 600,
                  fontSize: '2rem',
                  color: 'text.primary',
                  mb: 0.5
                }}
              >
                Admission Reviews
              </Typography>
              <Typography variant="body1" color="text.secondary">
                View and manage your admission review sessions
              </Typography>
            </Box>
            <Button
              variant="contained"
              startIcon={<Add />}
              onClick={() => {
                router.push('/assessments/new');
              }}
              sx={{
                backgroundColor: 'primary.main',
                color: 'primary.contrastText',
                px: 3,
                py: 1.5,
                borderRadius: 2,
                fontWeight: 600,
                textTransform: 'none',
                boxShadow: 2,
                '&:hover': {
                  backgroundColor: 'primary.dark',
                  boxShadow: 3,
                }
              }}
            >
              Create
            </Button>
          </Box>
          <TableContainer component={Paper} elevation={2}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 'bold' }}>Admission Review</TableCell>
                    <TableCell sx={{ fontWeight: 'bold', position: 'relative', pr: 6, '&:hover .status-menu-btn': { opacity: 1, pointerEvents: 'auto' } }}>
                      <TableSortLabel
                        active={orderBy === 'status'}
                        direction={orderBy === 'status' ? order : 'asc'}
                        onClick={() => handleRequestSort('status')}
                      >
                        Status
                      </TableSortLabel>
                      <IconButton size="small" className="status-menu-btn" onClick={(e) => setStatusMenuAnchor(e.currentTarget)} sx={{ position: 'absolute', right: 8, top: '50%', transform: 'translateY(-50%)', opacity: 0, pointerEvents: 'none', transition: 'opacity 0.2s' }}>
                        <MoreVert fontSize="small" />
                      </IconButton>
                    </TableCell>
                    <TableCell sx={{ fontWeight: 'bold' }}>
                      <TableSortLabel
                        active={orderBy === 'started'}
                        direction={orderBy === 'started' ? order : 'asc'}
                        onClick={() => handleRequestSort('started')}
                      >
                        Started
                      </TableSortLabel>
                    </TableCell>
                    <TableCell align="center" sx={{ fontWeight: 'bold' }}>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredAndSorted.map((evaluation: any) => (
                    <TableRow 
                      key={evaluation.id}
                      sx={{ '&:hover': { backgroundColor: 'action.hover' } }}
                    >
                      <TableCell sx={{ py: 2 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Assessment color="primary" />
                          <Typography variant="body1" fontWeight="medium">
                            {evaluation.name || `Admission Review #${evaluation.id}`}
                          </Typography>
                        </Box>
                      </TableCell>
                      <TableCell sx={{ py: 2 }}>
                        <Chip
                          icon={getStatusIcon(evaluation.status)}
                          label={evaluation.status}
                          color={getStatusColor(evaluation.status)}
                          variant="outlined"
                          size="small"
                        />
                      </TableCell>
                      <TableCell sx={{ py: 2 }}>
                        <Typography variant="body2" color="text.secondary">
                          {formatLocalDateTime(evaluation.created_at)}
                        </Typography>
                      </TableCell>
                      <TableCell align="center" sx={{ py: 2 }}>
                        <Box sx={{ display: 'flex', gap: 1, justifyContent: 'center' }}>
                          <IconButton
                            color="primary"
                            onClick={() => router.push(`/assessments/runs/${evaluation.id}`)}
                            title={evaluation.status?.toLowerCase() === 'completed' ? 'View Details' : 'Available after completion'}
                            disabled={evaluation.status?.toLowerCase() !== 'completed'}
                          >
                            <Visibility />
                          </IconButton>
                          <IconButton
                            color="error"
                            onClick={() => handleDeleteClick(evaluation)}
                            title="Delete"
                          >
                            <Delete />
                          </IconButton>
                        </Box>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>

          <Menu
            anchorEl={statusMenuAnchor}
            open={Boolean(statusMenuAnchor)}
            onClose={() => setStatusMenuAnchor(null)}
          >
            <MenuItem selected={statusFilter === 'all'} onClick={() => { setStatusFilter('all'); setStatusMenuAnchor(null); }}>All</MenuItem>
            {CANONICAL_STATUS_ORDER.map((s) => (
              <MenuItem 
                key={s} 
                selected={statusFilter === s} 
                onClick={() => { setStatusFilter(s); setStatusMenuAnchor(null); }}
              >
                {displayStatus(s)}
              </MenuItem>
            ))}
          </Menu>
          
          {(!data || data.length === 0) && (
            <Card elevation={1} sx={{ p: 4, textAlign: 'center' }}>
              <Assessment sx={{ fontSize: 80, color: 'text.secondary', mb: 2 }} />
              <Typography variant="h6" color="text.secondary" gutterBottom>
                No admission reviews found
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Start a new admission review to see it here.
              </Typography>
            </Card>
          )}
          </Stack>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialogOpen}
        onClose={handleDeleteCancel}
        aria-labelledby="delete-dialog-title"
        aria-describedby="delete-dialog-description"
      >
        <DialogTitle id="delete-dialog-title">
          Confirm Deletion
        </DialogTitle>
        <DialogContent>
          <DialogContentText id="delete-dialog-description">
            Are you sure you want to delete {admissionReviewToDelete?.name || `Admission Review #${admissionReviewToDelete?.id}`}? 
            This action cannot be undone and will permanently remove all associated data.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleDeleteCancel} color="primary">
            Cancel
          </Button>
          <Button onClick={handleDeleteConfirm} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
