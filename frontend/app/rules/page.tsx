"use client";
import { useApi } from '../../lib/api';
import { useApiQuery, useApiMutation } from '../../lib/useApiQuery';
import { Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle, Stack, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography, CircularProgress } from '@mui/material';
import { useState } from 'react';
import { useToast } from '../../components/providers/ToastProvider';

export default function RulesPage() {
  const api = useApi();
  const { addToast } = useToast();
  const rules = useApiQuery(['rules-sets'], '/rules/sets');
  const [open, setOpen] = useState(false);
  const [url, setUrl] = useState('');
  const [name, setName] = useState('');
  const [desc, setDesc] = useState('');

  const createMutation = useApiMutation(
    async (data: { name: string; description: string; metadata_json: any }) => {
      return api('/rules/sets', { 
        method: 'POST', 
        body: JSON.stringify(data)
      });
    },
    {
      onSuccess: () => {
        addToast({
          message: 'Rule set created successfully',
          severity: 'success'
        });
        setOpen(false);
        setUrl('');
        setName('');
        setDesc('');
        rules.refetch();
      },
      onError: (error) => {
        console.error('Create rule set error:', error);
        addToast({
          message: 'Failed to create rule set',
          severity: 'error'
        });
      }
    }
  );

  const onCreate = async () => {
    if (!name.trim()) {
      addToast({
        message: 'Please enter a name for the rule set',
        severity: 'warning'
      });
      return;
    }

    const meta = { source_url: url || undefined } as any;
    createMutation.mutate({
      name: name.trim(),
      description: desc.trim(),
      metadata_json: meta
    });
  };

  if (rules.isLoading) {
    return (
      <Stack spacing={2} alignItems="center" sx={{ py: 4 }}>
        <CircularProgress />
        <Typography>Loading rules...</Typography>
      </Stack>
    );
  }

  if (rules.isError) {
    return (
      <Stack spacing={2}>
        <Typography variant="h5">Rule Management</Typography>
        <Alert severity="error">
          Failed to load rules. Please try refreshing the page.
        </Alert>
      </Stack>
    );
  }

  return (
    <Stack spacing={2}>
      <Typography variant="h5">Rule Management</Typography>
      <Button variant="contained" onClick={() => setOpen(true)}>
        Create / Import from URL
      </Button>
      
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>ID</TableCell>
            <TableCell>Name</TableCell>
            <TableCell>Created</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {(rules.data || []).map((rs: any) => (
            <TableRow key={rs.id}>
              <TableCell>{rs.id}</TableCell>
              <TableCell>{rs.name}</TableCell>
              <TableCell>{new Date(rs.created_at).toLocaleString()}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      
      <Dialog open={open} onClose={() => setOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>New Rule Set</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField 
              label="Name" 
              value={name} 
              onChange={e => setName(e.target.value)}
              required
              fullWidth
            />
            <TextField 
              label="Description" 
              value={desc} 
              onChange={e => setDesc(e.target.value)}
              multiline
              rows={3}
              fullWidth
            />
            <TextField 
              label="Programme URL (optional)" 
              value={url} 
              onChange={e => setUrl(e.target.value)}
              fullWidth
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)} disabled={createMutation.isPending}>
            Cancel
          </Button>
          <Button 
            onClick={onCreate} 
            variant="contained" 
            disabled={createMutation.isPending || !name.trim()}
          >
            {createMutation.isPending ? <CircularProgress size={20} /> : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}

