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
  CardContent,
  CardActions,
  Box,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions
} from '@mui/material';
import { Assessment, Visibility, Description, Schedule, CheckCircle, HourglassEmpty, Cancel, Delete } from '@mui/icons-material';
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
        // Keep horizontal padding to 0 here; AppShell's Container
        // already handles gutters to maintain perfect symmetry
        px: 0
      }}
    >
          <Stack spacing={4}>
          <Box textAlign="center">
            <Typography variant="h4" gutterBottom sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 2 }}>
              <Assessment color="primary" sx={{ fontSize: 40 }} />
              Evaluation History
            </Typography>
            <Typography variant="h6" color="text.secondary">
              View and manage your student evaluation sessions
            </Typography>
          </Box>
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: {
                xs: '1fr',
                sm: 'repeat(2, 1fr)',
                md: 'repeat(3, 1fr)'
              },
              gap: 4,
              justifyItems: 'center'
            }}
          >
        {(Array.isArray(data) ? data : []).map((evaluation: any) => (
          <Box key={evaluation.id} sx={{ width: '100%', maxWidth: 400 }}>
            <Card 
              elevation={2} 
              sx={{ 
                height: '100%',
                minHeight: 280,
                display: 'flex',
                flexDirection: 'column',
                transition: 'transform 0.2s, box-shadow 0.2s',
                '&:hover': {
                  transform: 'translateY(-2px)',
                  boxShadow: 4,
                }
              }}
            >
              <CardContent sx={{ flexGrow: 1, pb: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                  <Typography variant="h6" component="div" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Assessment color="primary" />
                    Evaluation #{evaluation.id}
                  </Typography>
                  <Chip
                    icon={getStatusIcon(evaluation.status)}
                    label={evaluation.status}
                    color={getStatusColor(evaluation.status)}
                    variant="outlined"
                    size="small"
                  />
                </Box>
                
                <Divider sx={{ mb: 2 }} />
                
                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2" color="text.secondary" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Schedule fontSize="small" />
                    Started: {new Date(evaluation.created_at).toLocaleString()}
                  </Typography>
                </Box>
                
                <Typography variant="body2" color="text.secondary">
                  {evaluation.status === 'completed' 
                    ? 'Assessment completed - ready for review' 
                    : evaluation.status === 'running' 
                    ? 'Assessment in progress...' 
                    : `Status: ${evaluation.status}`
                  }
                </Typography>
              </CardContent>
              
              <CardActions sx={{ p: 2, pt: 1, display: 'flex', gap: 1, alignItems: 'stretch' }}>
                <Button
                  variant="outlined"
                  color="primary"
                  startIcon={<Visibility />}
                  onClick={() => router.push(`/assessments/runs/${evaluation.id}`)}
                  size="medium"
                  sx={{ height: 50, flex: 1 }}
                >
                  View Details
                </Button>
                <Button
                  variant="contained"
                  color="primary"
                  startIcon={<Description />}
                  onClick={() => router.push(`/reports/${evaluation.id}`)}
                  disabled={evaluation.status !== 'completed'}
                  size="medium"
                  sx={{ height: 50, flex: 1 }}
                >
                  Final Report
                </Button>
                <Button
                  variant="outlined"
                  color="error"
                  startIcon={<Delete />}
                  onClick={() => handleDeleteClick(evaluation)}
                  size="medium"
                  sx={{ height: 50, flex: 1 }}
                >
                  Delete
                </Button>
              </CardActions>
            </Card>
          </Box>
        ))}
          </Box>
          
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
