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
  IconButton
} from '@mui/material';
import { Assessment, Visibility, Schedule, CheckCircle, HourglassEmpty, Cancel, Delete, Add } from '@mui/icons-material';
import { useRouter } from 'next/navigation';

export default function EvaluationHistoryPage() {
  const api = useApi();
  const router = useRouter();
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [evaluationToDelete, setEvaluationToDelete] = useState<any>(null);
  
  const { data, refetch } = useQuery({
    queryKey: ['runs-list'],
    queryFn: async () => {
      const r = await api('/assessments/runs?visible_only=true');
      return r.ok ? r.json() : [];
    },
  });

  const handleDeleteClick = (evaluation: any) => {
    setEvaluationToDelete(evaluation);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!evaluationToDelete) return;
    
    try {
      const response = await api(`/assessments/runs/${evaluationToDelete.id}`, {
        method: 'DELETE',
      });
      
      if (response.ok) {
        // Refresh the data after successful deletion
        refetch();
        setDeleteDialogOpen(false);
        setEvaluationToDelete(null);
      } else {
        console.error('Failed to delete evaluation');
      }
    } catch (error) {
      console.error('Error deleting evaluation:', error);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteDialogOpen(false);
    setEvaluationToDelete(null);
  };
  const getStatusIcon = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'completed': return <CheckCircle color="success" />;
      case 'running': case 'in_progress': return <HourglassEmpty color="info" />;
      case 'failed': case 'error': return <Cancel color="error" />;
      default: return <Schedule color="action" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'completed': return 'success';
      case 'running': case 'in_progress': return 'info';
      case 'failed': case 'error': return 'error';
      default: return 'default';
    }
  };

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
                Assessments
              </Typography>
              <Typography variant="body1" color="text.secondary">
                View and manage your admission review sessions
              </Typography>
            </Box>
            <Button
              variant="contained"
              startIcon={<Add />}
              onClick={() => router.push('/assessments/new')}
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
                    <TableCell sx={{ fontWeight: 'bold' }}>Evaluation</TableCell>
                    <TableCell sx={{ fontWeight: 'bold' }}>Status</TableCell>
                    <TableCell sx={{ fontWeight: 'bold' }}>Started</TableCell>
                    <TableCell align="center" sx={{ fontWeight: 'bold' }}>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {(Array.isArray(data) ? data : []).map((evaluation: any) => (
                    <TableRow 
                      key={evaluation.id}
                      sx={{ '&:hover': { backgroundColor: 'action.hover' } }}
                    >
                      <TableCell sx={{ py: 2 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Assessment color="primary" />
                          <Typography variant="body1" fontWeight="medium">
                            Evaluation #{evaluation.id}
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
                          {new Date(evaluation.created_at).toLocaleString()}
                        </Typography>
                      </TableCell>
                      <TableCell align="center" sx={{ py: 2 }}>
                        <Box sx={{ display: 'flex', gap: 1, justifyContent: 'center' }}>
                          <IconButton
                            color="primary"
                            onClick={() => router.push(`/assessments/runs/${evaluation.id}`)}
                            title="View Details"
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
          
          {(!data || data.length === 0) && (
            <Card elevation={1} sx={{ p: 4, textAlign: 'center' }}>
              <Assessment sx={{ fontSize: 80, color: 'text.secondary', mb: 2 }} />
              <Typography variant="h6" color="text.secondary" gutterBottom>
                No evaluations found
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Start a new evaluation to see it here.
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
            Are you sure you want to delete Evaluation #{evaluationToDelete?.id}? 
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
