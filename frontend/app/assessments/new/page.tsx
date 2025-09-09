"use client";
import { Alert, Box, Button, Card, CardContent, Stack, TextField, Typography, ToggleButton, ToggleButtonGroup, InputAdornment, Collapse, Paper, Chip, FormControl, InputLabel, Select, MenuItem, FormHelperText, CircularProgress } from '@mui/material';
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
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const preserveRunRef = useRef(false);
  const searchParams = useSearchParams();

  const ruleSets = useQuery({
    queryKey: ['rule-sets'],
    queryFn: async () => (await (await api('/rules/sets')).json()),
  });

  // Initialize run from query param when landing from Create
  useEffect(() => {
    const idParam = searchParams?.get('runId');
    if (!idParam) return;
    if (run && Number(run.id) === Number(idParam)) return;
    setRun({ id: Number(idParam), status: 'created' });
  }, [searchParams, run]);

  // Cleanup: destroy unstarted run when leaving the page unless explicitly preserved
  useEffect(() => {
    return () => {
      const shouldDelete = !preserveRunRef.current && run && (['created', 'pending'].includes(String(run.status).toLowerCase()));
      if (shouldDelete) {
        void api(`/assessments/runs/${run.id}`, { method: 'DELETE' });
      }
    };
  }, [api, run]);

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

  // Create run on demand (via Create button)
  const createRun = async () => {
    if (run || creating) return;
    try {
      setCreating(true);
      setError(null);
      const resp = await api('/assessments/runs', { method: 'POST', body: JSON.stringify({}) });
      if (!resp.ok) { setError('Failed to create run'); return; }
      const created = await resp.json();
      setRun(created);
    } finally {
      setCreating(false);
    }
  };

  const handleFileUpload = async (file: File) => {
    if (!run) return;
    setError(null);
    setUploading(true);
    const fd = new FormData();
    fd.append('file', file);
    const r = await api(`/assessments/runs/${run.id}/upload`, { method: 'POST', body: fd });
    if (r.ok) {
      const u = await r.json();
      setRun(u);
    } else {
      setError('Upload failed');
    }
    setUploading(false);
  };

  const onUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    await handleFileUpload(file);
    // Reset input value so the same file can be selected again if needed
    e.currentTarget.value = '';
  };

  const onStart = async () => {
    if (!run) return;
    preserveRunRef.current = true;
    const r = await api(`/assessments/runs/${run.id}/start`, { method: 'POST' });
    if (!r.ok) { setError('Failed to start'); return; }
    const u = await r.json(); setRun(u);
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
              New Assessment
            </Typography>
            <Typography variant="body1" color="text.secondary">
              Select a rule set, upload a ZIP, and start the evaluation
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
                  <ToggleButton value="existing"><Gavel sx={{ mr: 1 }} />Use Rule Set</ToggleButton>
                  <ToggleButton value="url"><LinkIcon sx={{ mr: 1 }} />Programme URL</ToggleButton>
                </ToggleButtonGroup>
              </Paper>
              <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
                Exactly one is required to proceed
              </Typography>
            </Box>

            <Collapse in={ruleSource === 'existing'} mountOnEnter unmountOnExit>
              <FormControl required sx={{ maxWidth: 560 }} size="small" disabled={!((ruleSets.data||[]).length)}>
                <InputLabel id="rule-set-select-label" shrink>Rule Set</InputLabel>
                <Select
                  labelId="rule-set-select-label"
                  label="Rule Set"
                  value={ruleSetId ?? ''}
                  onChange={(e)=> setRuleSetId(Number(e.target.value))}
                  displayEmpty
                  renderValue={(value: any) => {
                    if (value === '' || value === undefined || value === null) return 'Select a rule set';
                    const found = (ruleSets.data||[]).find((rs: any)=> rs.id === value);
                    return found?.name || '';
                  }}
                >
                  {(ruleSets.data||[]).map((rs: any)=> (
                    <MenuItem key={rs.id} value={rs.id}>{rs.name}</MenuItem>
                  ))}
                </Select>
                <FormHelperText>
                  {((ruleSets.data||[]).length) ? 'Required when using an existing rule set' : 'No rule sets available'}
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
            Start Evaluation
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
    </Stack>
    </Box>
  );
}

