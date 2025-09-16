"use client";
import { Alert, Box, Button, Card, CardContent, Stack, TextField, Typography, ToggleButton, ToggleButtonGroup, InputAdornment, Collapse, Paper, Chip, FormControl, InputLabel, Select, MenuItem, FormHelperText, CircularProgress, Dialog, DialogTitle, DialogContent } from '@mui/material';
import { useEffect, useRef, useState } from 'react';
import { useApi } from '../../../lib/api';
import { useQuery } from '@tanstack/react-query';
import { useRouter, useSearchParams } from 'next/navigation';
import { Gavel, Link as LinkIcon, CloudUpload, PlayArrow } from '@mui/icons-material';

// Simplified single-page flow: select rules -> auto create run -> upload -> start

export default function NewAssessmentPage() {
  const api = useApi();
  const router = useRouter();
  const [ruleSetId, setRuleSetId] = useState<number|undefined>();
  const [ruleSetUrl, setRuleSetUrl] = useState('');
  const [customInput, setCustomInput] = useState('');
  const [customItems, setCustomItems] = useState<string[]>([]);
  const [run, setRun] = useState<any>(null);
  const [error, setError] = useState<string| null>(null);
  const [ruleSource, setRuleSource] = useState<'existing'|'url'>('existing');
  const [creating, setCreating] = useState(false);
  const lastSpecKeyRef = useRef<string>('');
  const [isDragActive, setIsDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [starting, setStarting] = useState(false);
  const [startDialogOpen, setStartDialogOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const preserveRunRef = useRef(false);
  // Keep latest references to avoid stale closures in unmount cleanup
  const runRef = useRef<any>(null);
  const apiRef = useRef(api);
  const searchParams = useSearchParams();

  const ruleSets = useQuery({
    queryKey: ['rule-sets'],
    queryFn: async () => (await (await api('/rules/sets')).json()),
  });

  // Initialize run: from query if provided, otherwise create on first load
  useEffect(() => {
    const init = async () => {
      const idParam = searchParams?.get('runId');
      if (idParam) {
        if (!run || Number(run.id) !== Number(idParam)) {
          setRun({ id: Number(idParam), status: 'created' });
        }
        return;
      }
      if (!run && !creating) {
        setCreating(true);
        try {
          const resp = await api('/assessments/runs', { method: 'POST', body: JSON.stringify({}) });
          if (resp.ok) {
            const created = await resp.json();
            setRun(created);
          } else {
            setError('Failed to create run');
          }
        } finally {
          setCreating(false);
        }
      }
    };
    void init();
  }, [searchParams, run, creating, api]);

  // Sync refs when values change
  useEffect(() => { runRef.current = run; }, [run]);
  useEffect(() => { apiRef.current = api; }, [api]);

  // Cleanup only on unmount: destroy unstarted run unless explicitly preserved
  useEffect(() => {
    return () => {
      const currentRun = runRef.current;
      const shouldDelete = !preserveRunRef.current && currentRun && (['created', 'pending'].includes(String(currentRun.status).toLowerCase()));
      if (shouldDelete) {
        void apiRef.current(`/assessments/runs/${currentRun.id}`, { method: 'DELETE' });
      }
    };
  }, []);

  // Ensure a run exists and bind rule set when selection becomes valid
  useEffect(() => {
    if (!run) return;
    const specKey = JSON.stringify({
      ruleSource,
      ruleSetId: ruleSetId ?? null,
      ruleSetUrl: ruleSetUrl.trim() || null,
      customItems,
    });
    const ready = (ruleSource === 'existing' && !!ruleSetId) || (ruleSource === 'url' && !!ruleSetUrl.trim());
    if (!ready) return;
    if (creating) return;
    if (lastSpecKeyRef.current === specKey) return;

    const bind = async () => {
      try {
        setCreating(true);
        setError(null);
        const body: any = { custom_requirements: customItems };
        if (ruleSource === 'existing') {
          body.rule_set_id = ruleSetId;
        } else {
          body.rule_set_url = ruleSetUrl.trim();
        }
        const resp = await api(`/assessments/runs/${run.id}/rule-set`, { method: 'PUT', body: JSON.stringify(body) });
        if (!resp.ok) { setError('Failed to bind rule set'); return; }
        const updated = await resp.json();
        setRun(updated);
        lastSpecKeyRef.current = specKey;
      } finally {
        setCreating(false);
      }
    };
    void bind();
  }, [ruleSource, ruleSetId, ruleSetUrl, customItems, creating, run, api]);


  const handleFileUpload = async (file: File) => {
    if (!run) return;
    setError(null);
    setUploading(true);
    const fd = new FormData();
    fd.append('file', file);
    const r = await api(`/assessments/runs/${run.id}/upload`, { method: 'POST', body: fd });
    if (r.ok) {
      // Refresh run detail to include applicants/documents for UI feedback
      await refreshRunDetail(run.id);
    } else {
      setError('Upload failed');
    }
    setUploading(false);
  };

  const refreshRunDetail = async (id?: number) => {
    const rid = id ?? run?.id;
    if (!rid) return;
    const resp = await api(`/assessments/runs/${rid}`);
    if (resp.ok) {
      const detail = await resp.json();
      setRun(detail);
    }
  };

  const onUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const inputEl = e.currentTarget;
    const file = inputEl.files?.[0];
    if (!file) return;
    await handleFileUpload(file);
    // Reset input value so the same file can be selected again if needed
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    } else if (inputEl) {
      inputEl.value = '';
    }
  };

  const onStart = async () => {
    if (!run || starting) return;
    setStartDialogOpen(true);
    setStarting(true);
    preserveRunRef.current = true;
    const r = await api(`/assessments/runs/${run.id}/start`, { method: 'POST' });
    if (!r.ok) {
      setError('Failed to start');
      setStarting(false);
      setStartDialogOpen(false);
      return;
    }
    const u = await r.json(); setRun(u);
    // brief pause for UX before navigation
    setTimeout(() => {
      setStarting(false);
      setStartDialogOpen(false);
      router.push('/assessments');
    }, 1800);
  };

  const onCancel = async () => {
    if (!run) return;
    try {
      await api(`/assessments/runs/${run.id}`, { method: 'DELETE' });
    } finally {
      preserveRunRef.current = true; // prevent cleanup double-fire
      router.push('/assessments');
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
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
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
              New Admission Review
            </Typography>
            <Typography variant="body1" color="text.secondary">
              Select programme criteria, upload a ZIP, and start the evaluation
            </Typography>
          </Box>
        </Box>

        {error && <Alert severity="error">{error}</Alert>}

      <Card elevation={2}><CardContent>
          <Stack spacing={3}>
            <Box>
              <Typography variant="h6" sx={{ mb: 1, fontWeight: 600 }}>Choose one</Typography>
              <Paper elevation={0} sx={{ p: 0.5, borderRadius: 999, backgroundColor: 'action.hover', display: 'inline-flex' }}>
                <ToggleButtonGroup
                  color="primary"
                  exclusive
                  value={ruleSource}
                  onChange={(_, v) => {
                    if (!v) return;
                    setRuleSource(v);
                    if (v === 'existing') { setRuleSetUrl(''); }
                    if (v === 'url') { setRuleSetId(undefined); }
                  }}
                  sx={{
                    '& .MuiToggleButton-root': {
                      textTransform: 'none', px: 2.5, py: 1, borderRadius: 999,
                      border: 'none'
                    },
                    '& .Mui-selected': {
                      backgroundColor: 'primary.main',
                      color: 'primary.contrastText',
                      boxShadow: 2,
                      '&:hover': { backgroundColor: 'primary.dark' }
                    }
                  }}
                >
                  <ToggleButton value="existing"><Gavel sx={{ mr: 1 }} />Use Programme Criteria</ToggleButton>
                  <ToggleButton value="url"><LinkIcon sx={{ mr: 1 }} />Programme URL</ToggleButton>
                </ToggleButtonGroup>
              </Paper>
              <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
                Exactly one is required to proceed
              </Typography>
            </Box>

            <Collapse in={ruleSource === 'existing'} mountOnEnter unmountOnExit>
              <FormControl required sx={{ maxWidth: 560 }} size="small" disabled={!((ruleSets.data||[]).length)}>
                <InputLabel id="rule-set-select-label" shrink>Programme Criteria</InputLabel>
                <Select
                  labelId="rule-set-select-label"
                  label="Programme Criteria"
                  value={ruleSetId ?? ''}
                  onChange={(e)=> setRuleSetId(Number(e.target.value))}
                  displayEmpty
                  renderValue={(value: any) => {
                    if (value === '' || value === undefined || value === null) return 'Select programme criteria';
                    const found = (ruleSets.data||[]).find((rs: any)=> rs.id === value);
                    return found?.name || '';
                  }}
                >
                  {(ruleSets.data||[]).map((rs: any)=> (
                    <MenuItem key={rs.id} value={rs.id}>{rs.name}</MenuItem>
                  ))}
                </Select>
                <FormHelperText>
                  {((ruleSets.data||[]).length) ? 'Required when using existing programme criteria' : 'No programme criteria available'}
                </FormHelperText>
              </FormControl>
            </Collapse>

            <Collapse in={ruleSource === 'url'} mountOnEnter unmountOnExit>
              <TextField
                label="Programme URL"
                placeholder="https://www.university.edu/programme-page"
                required
                value={ruleSetUrl}
                onChange={e=>setRuleSetUrl(e.target.value)}
                helperText="Required when importing from a programme page"
                InputProps={{ startAdornment: <InputAdornment position="start"><LinkIcon fontSize="small" /></InputAdornment> }}
                sx={{ maxWidth: 860 }}
              />
            </Collapse>

            <Box>
              <Typography variant="subtitle1" sx={{ mb: 1 }}>Custom requirements</Typography>
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} alignItems={{ sm: 'center' }}>
                <TextField
                  label="Add a requirement"
                  placeholder="e.g., Minimum GPA 3.5"
                  value={customInput}
                  onChange={(e)=> setCustomInput(e.target.value)}
                  onKeyDown={(e)=> {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      const t = customInput.trim();
                      if (!t) return;
                      setCustomItems(prev => prev.includes(t) ? prev : [...prev, t]);
                      setCustomInput('');
                    }
                  }}
                  size="small"
                  sx={{ maxWidth: 560 }}
                />
                <Button
                  variant="outlined"
                  onClick={() => {
                    const t = customInput.trim();
                    if (!t) return;
                    setCustomItems(prev => prev.includes(t) ? prev : [...prev, t]);
                    setCustomInput('');
                  }}
                >Add</Button>
              </Stack>
              {!!customItems.length && (
                <Stack direction="row" spacing={1} sx={{ mt: 1, flexWrap: 'wrap' }}>
                  {customItems.map(item => (
                    <Chip key={item} label={item} onDelete={() => setCustomItems(prev => prev.filter(x => x !== item))} sx={{ mr: 1, mb: 1 }} />
                  ))}
                </Stack>
              )}
            </Box>

            {/* Run is auto-created once selection is valid */}
          </Stack>
        </CardContent></Card>

      <Card elevation={2}><CardContent>
        <Stack spacing={1}>
          <Typography variant="subtitle1" gutterBottom>Upload ZIP (grouped by student folders)</Typography>
          <input
            ref={fileInputRef}
            type="file"
            accept=".zip"
            onChange={onUpload}
            disabled={!run || creating || uploading}
            style={{ display: 'none' }}
          />
          <Paper
            variant="outlined"
            onDragOver={(e)=> { e.preventDefault(); setIsDragActive(true); }}
            onDragLeave={()=> setIsDragActive(false)}
            onDrop={(e)=> {
              e.preventDefault();
              setIsDragActive(false);
              if (!run || creating || uploading) return;
              const file = Array.from(e.dataTransfer.files || []).find(f => f.name.toLowerCase().endsWith('.zip'));
              if (file) { void handleFileUpload(file); }
            }}
            onClick={()=> {
              if (!run || creating || uploading) return;
              fileInputRef.current?.click();
            }}
            sx={{
              p: 4,
              textAlign: 'center',
              borderStyle: 'dashed',
              borderColor: isDragActive ? 'primary.main' : 'divider',
              bgcolor: isDragActive ? 'action.hover' : 'background.paper',
              cursor: (!run || creating || uploading) ? 'not-allowed' : 'pointer'
            }}
          >
            <Stack spacing={1} alignItems="center">
              <CloudUpload sx={{ fontSize: 40, color: 'text.secondary' }} />
              <Typography variant="body1">Drag and drop ZIP here</Typography>
              <Typography variant="body2" color="text.secondary">or click to browse</Typography>
              <Stack direction="row" spacing={1} alignItems="center" justifyContent="center" sx={{ mt: 1 }}>
                {(creating || uploading) && <CircularProgress size={18} />}
              </Stack>
              {run?.status === 'uploaded' && Array.isArray(run?.applicants) && (
                <Typography variant="body2" color="success.main" sx={{ mt: 1 }}>
                  Uploaded {run.applicants.length} applicants
                </Typography>
              )}
            </Stack>
          </Paper>
        </Stack>
      </CardContent></Card>

      {run && (
        <Stack direction="row" spacing={2}>
          <Button 
            variant="contained" 
            startIcon={<PlayArrow />}
            onClick={onStart}
            sx={{
              px: 3, py: 1.25, borderRadius: 2, textTransform: 'none', fontWeight: 600,
              boxShadow: 2,
              '&:hover': { boxShadow: 3 }
            }}
          >
            Start Admission Review
          </Button>
          <Button 
            color="error"
            variant="text"
            onClick={onCancel}
            sx={{ px: 2, py: 1.25, borderRadius: 2, textTransform: 'none' }}
          >
            Cancel
          </Button>
        </Stack>
      )}

      <Dialog open={startDialogOpen} onClose={() => {}} fullWidth maxWidth="sm">
        <DialogTitle sx={{ fontWeight: 700 }}>Starting admission review…</DialogTitle>
        <DialogContent>
          <Stack spacing={2} alignItems="center" sx={{ py: 1 }}>
            <CircularProgress size={28} />
            <Typography variant="body1" align="center" sx={{ fontWeight: 500 }}>
              Each applicant may take around 2 minutes to review.
            </Typography>
            <Typography variant="body2" color="text.secondary" align="center">
              Please be patient. You&apos;ll be redirected to the admission reviews page shortly.
            </Typography>
          </Stack>
        </DialogContent>
      </Dialog>
    </Stack>
    </Box>
  );
}

