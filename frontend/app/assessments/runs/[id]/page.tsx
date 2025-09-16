"use client";
import { useParams, useRouter } from 'next/navigation';
import { useApi } from '../../../../lib/api';
import { useEffect, useState, useCallback } from 'react';
import { Alert, Box, Button, Stack, Typography, Container, Skeleton } from '@mui/material';
import { ArrowBack } from '@mui/icons-material';
import EvaluationProcess from '../../../../components/EvaluationProcess';
import StatCard from '../../../../components/ui/StatCard';

export default function RunDetailPage() {
  const params = useParams<{ id: string }>();
  const runId = Number(params.id);
  const api = useApi();
  const router = useRouter();
  const [run, setRun] = useState<any>(null);
  const [evaluationData, setEvaluationData] = useState<any>(null);
  const [error, setError] = useState<string| null>(null);

  const load = useCallback(async () => {
    setError(null);
    const r = await api(`/assessments/runs/${runId}`);
    if (r.ok) setRun(await r.json()); else setError('Failed to load run');
    const evalData = await api(`/reports/runs/${runId}`);
    if (evalData.ok) setEvaluationData(await evalData.json());
  }, [api, runId]);

  useEffect(() => { void load(); }, [load]);

  const items = evaluationData?.items || [];
  const accepted = items.filter((item: any) => {
    const d = item.gating?.decision?.toLowerCase();
    return d === 'pass' || d === 'accept';
  });
  const rejected = items.filter((item: any) => {
    const d = item.gating?.decision?.toLowerCase();
    return d === 'fail' || d === 'reject';
  });
  const middle = items.filter((item: any) => item.gating?.decision?.toLowerCase() === 'middle');
  const total = items.length || 0;
  const pct = (n: number) => (total > 0 ? Math.round((n / total) * 100) : 0);
  const statusRaw = (run?.status || 'unknown') as string;
  const statusDisplay = statusRaw ? statusRaw.charAt(0).toUpperCase() + statusRaw.slice(1) : 'Unknown';

  return (
    <Container maxWidth="lg" sx={{ py: 3 }}>
      <Stack spacing={3}>
      <Stack direction="row" alignItems="center" spacing={1}>
        <Button 
          variant="text" 
          startIcon={<ArrowBack />} 
          onClick={()=>router.push('/assessments')}
        >
          Back
        </Button>
        {run ? (
          <Typography variant="h5">{run.name || `Admission Review #${runId}`}</Typography>
        ) : (
          <Skeleton variant="text" width={320} height={36} />
        )}
      </Stack>
      {error && <Alert severity="error">{error}</Alert>}
      <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
        <StatCard 
          title="Status" 
          value={statusDisplay}
          color={(statusRaw || '').toLowerCase() === 'completed' ? 'success' : (statusRaw || '').toLowerCase() === 'failed' ? 'error' : 'info'}
        />
        <StatCard title="Accepted" value={accepted.length} subtitle={`of ${total} total`} color="success" percent={pct(accepted.length)} chipLabel={`${pct(accepted.length)}%`} />
        <StatCard title="Middle" value={middle.length} subtitle={`of ${total} total`} color="warning" percent={pct(middle.length)} chipLabel={`${pct(middle.length)}%`} />
        <StatCard title="Rejected" value={rejected.length} subtitle={`of ${total} total`} color="error" percent={pct(rejected.length)} chipLabel={`${pct(rejected.length)}%`} />
      </Box>
      <Box>
        {evaluationData ? (
          <EvaluationProcess data={evaluationData} runId={runId} onChanged={() => { void load(); }} />
        ) : null}
      </Box>
      </Stack>
    </Container>
  );
}
