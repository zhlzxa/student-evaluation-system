"use client";
import { Alert, Box, Button, Card, CardContent, CircularProgress, FormControl, InputLabel, MenuItem, Select, Stack, Step, StepLabel, Stepper, TextField, Typography } from '@mui/material';
import { useState } from 'react';
import { useApi } from '../../../lib/api';
import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';

const steps = ['Select Rules', 'Upload Materials', 'Start & Monitor'];

export default function NewAssessmentPage() {
  const api = useApi();
  const router = useRouter();
  const [active, setActive] = useState(0);
  const [ruleSetId, setRuleSetId] = useState<number|undefined>();
  const [ruleSetUrl, setRuleSetUrl] = useState('');
  const [custom, setCustom] = useState('');
  const [agentModels, setAgentModels] = useState<Record<string,string>>({});
  const [run, setRun] = useState<any>(null);
  const [error, setError] = useState<string| null>(null);

  const cfg = useQuery({
    queryKey: ['model-config'],
    queryFn: async () => (await (await api('/models/config')).json()),
  });
  const ruleSets = useQuery({
    queryKey: ['rule-sets'],
    queryFn: async () => (await (await api('/rules/sets')).json()),
  });

  const onCreateRun = async () => {
    setError(null);
    const body: any = { custom_requirements: custom ? custom.split('\n').map(s=>s.trim()).filter(Boolean) : [] };
    if (ruleSetId) body.rule_set_id = ruleSetId;
    if (ruleSetUrl) body.rule_set_url = ruleSetUrl;
    if (Object.keys(agentModels).length) body.agent_models = agentModels;
    const r = await api('/assessments/runs', { method: 'POST', body: JSON.stringify(body) });
    if (!r.ok) { setError('Failed to create run'); return; }
    const created = await r.json();
    setRun(created);
    setActive(1);
  };

  const onUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!run) return;
    const file = e.target.files?.[0];
    if (!file) return;
    const fd = new FormData();
    fd.append('file', file);
    const r = await api(`/assessments/runs/${run.id}/upload`, { method: 'POST', body: fd });
    if (r.ok) {
      const u = await r.json();
      setRun(u);
      setActive(2);
    } else setError('Upload failed');
  };

  const onStart = async () => {
    if (!run) return;
    const r = await api(`/assessments/runs/${run.id}/start`, { method: 'POST' });
    if (!r.ok) { setError('Failed to start'); return; }
    const u = await r.json(); setRun(u);
  };

  const supported: string[] = cfg.data?.supported_models || [];
  const agents: string[] = cfg.data?.agent_types || [];

  return (
    <Stack spacing={2}>
      <Typography variant="h5">New Assessment</Typography>
      <Stepper activeStep={active}>
        {steps.map((s)=>(<Step key={s}><StepLabel>{s}</StepLabel></Step>))}
      </Stepper>
      {error && <Alert severity="error">{error}</Alert>}

      {active === 0 && (
        <Card><CardContent>
          <Stack spacing={2}>
            <TextField select label="Rule Set" value={ruleSetId || ''} onChange={(e)=>setRuleSetId(e.target.value? Number(e.target.value): undefined)} helperText="Optional">
              <MenuItem value="">None</MenuItem>
              {(ruleSets.data||[]).map((rs: any)=> (
                <MenuItem key={rs.id} value={rs.id}>{rs.name}</MenuItem>
              ))}
            </TextField>
            <TextField label="Programme URL" value={ruleSetUrl} onChange={e=>setRuleSetUrl(e.target.value)} helperText="Optional; backend can preview/parse" />
            <TextField label="Custom requirements" value={custom} onChange={e=>setCustom(e.target.value)} multiline minRows={4} />
            <Box>
              <Typography variant="subtitle1" sx={{ mb: 1 }}>Agent Models</Typography>
              {cfg.isLoading ? <CircularProgress size={18} /> : (
                <Stack spacing={2}>
                  {agents?.map(a => (
                    <FormControl key={a} size="small" sx={{ maxWidth: 360 }}>
                      <InputLabel>{a}</InputLabel>
                      <Select label={a} value={agentModels[a] || cfg.data?.agent_models?.[a] || cfg.data?.default_model || ''}
                        onChange={(e)=> setAgentModels(s=> ({ ...s, [a]: String(e.target.value) }))}>
                        {(supported||[]).map(m => (<MenuItem key={m} value={m}>{m}</MenuItem>))}
                      </Select>
                    </FormControl>
                  ))}
                </Stack>
              )}
            </Box>
            <Button variant="contained" onClick={onCreateRun}>Create Run</Button>
          </Stack>
        </CardContent></Card>
      )}

      {active === 1 && run && (
        <Card><CardContent>
          <Typography variant="subtitle1" gutterBottom>Upload ZIP (grouped by student folders)</Typography>
          <input type="file" accept=".zip" onChange={onUpload} />
        </CardContent></Card>
      )}

      {active === 2 && run && (
        <Card><CardContent>
          <Stack spacing={2}>
            <Typography>Run #{run.id} — status: {run.status}</Typography>
            <Stack direction="row" spacing={2}>
              <Button variant="contained" onClick={onStart}>Start Evaluation</Button>
              <Button onClick={()=>router.push(`/assessments/runs/${run.id}`)}>Open Run</Button>
            </Stack>
          </Stack>
        </CardContent></Card>
      )}
    </Stack>
  );
}

