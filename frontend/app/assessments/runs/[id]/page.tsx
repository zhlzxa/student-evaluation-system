"use client";
import { useParams, useRouter } from 'next/navigation';
import { useApi } from '../../../../lib/api';
import { useEffect, useState } from 'react';
import { Alert, Box, Button, Chip, Paper, Stack, Typography, Container, Tabs, Tab } from '@mui/material';
import ConversationView from '../../../../components/ConversationView';
import EvaluationProcess from '../../../../components/EvaluationProcess';

export default function RunDetailPage() {
  const params = useParams<{ id: string }>();
  const runId = Number(params.id);
  const api = useApi();
  const router = useRouter();
  const [run, setRun] = useState<any>(null);
  const [logs, setLogs] = useState<any[]>([]);
  const [evaluationData, setEvaluationData] = useState<any>(null);
  const [error, setError] = useState<string| null>(null);
  const [activeTab, setActiveTab] = useState(0);

  async function load() {
    setError(null);
    const r = await api(`/assessments/runs/${runId}`);
    if (r.ok) setRun(await r.json()); else setError('Failed to load run');
    const lg = await api(`/assessments/runs/${runId}/logs?limit=100`);
    if (lg.ok) setLogs(await lg.json());
    // Load evaluation results for process steps
    const evalData = await api(`/reports/runs/${runId}`);
    if (evalData.ok) setEvaluationData(await evalData.json());
  }

  useEffect(()=> { load(); const t = setInterval(load, 5000); return ()=> clearInterval(t); }, []);

  return (
    <Container maxWidth="lg" sx={{ py: 3 }}>
      <Stack spacing={3}>
      <Typography variant="h5">Run #{runId} Detail</Typography>
      {error && <Alert severity="error">{error}</Alert>}
      <Paper sx={{ p: 2 }}>
        <Stack direction="row" spacing={1} alignItems="center">
          <Typography>Status:</Typography>
          <Chip size="small" label={run?.status || 'unknown'} />
        </Stack>
        <Button 
          variant="contained" 
          color="primary" 
          sx={{ mt: 2, borderRadius: 2, textTransform: 'none' }} 
          onClick={()=>router.push(`/reports/${runId}`)}
        >
          📊 Open Report
        </Button>
      </Paper>
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={activeTab} onChange={(_, newValue) => setActiveTab(newValue)}>
          <Tab label="Evaluation Process" />
          <Tab label="Agent Conversations" />
        </Tabs>
      </Box>

      {activeTab === 0 && (
        <Box>
          <Typography variant="h6" sx={{ mb: 2 }}>Evaluation Steps & Results</Typography>
          <EvaluationProcess data={evaluationData} />
        </Box>
      )}

      {activeTab === 1 && (
        <Box>
          <Typography variant="h6" sx={{ mb: 2 }}>Agent Conversations</Typography>
          <ConversationView 
            logs={logs.reverse()}
            applicants={run?.applicants || []}
          />
        </Box>
      )}
      </Stack>
    </Container>
  );
}
