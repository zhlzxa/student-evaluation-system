"use client";

import { useEffect, useMemo, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Container, Stack, Typography, Paper, Button, Breadcrumbs, Link as MUILink, Skeleton } from '@mui/material';
import { ArrowBack } from '@mui/icons-material';
import ConversationView from '../../../../../../components/ConversationView';
import { useApi } from '../../../../../../lib/api';

export default function ApplicantDetailNestedPage() {
  const params = useParams<{ id: string; applicantId: string }>();
  const runId = Number(params.id);
  const applicantId = Number(params.applicantId);
  const api = useApi();
  const router = useRouter();

  const [run, setRun] = useState<any>(null);
  const [logs, setLogs] = useState<any[]>([]);

  useEffect(() => {
    async function load() {
      const r = await api(`/assessments/runs/${runId}`);
      if (r.ok) setRun(await r.json());
      const lg = await api(`/assessments/runs/${runId}/logs?limit=200`);
      if (lg.ok) setLogs(await lg.json());
    }
    load();
  }, [runId]);

  const applicants = useMemo(() => {
    const list = run?.applicants || [];
    return list.filter((a: any) => a.id === applicantId);
  }, [run, applicantId]);

  const filteredLogs = useMemo(() => {
    return logs.filter((l) => l.applicant_id === applicantId);
  }, [logs, applicantId]);

  const runName = run?.name;
  const applicantName = applicants && applicants[0]?.folder_name;

  return (
    <Container maxWidth="lg" sx={{ py: 3 }}>
      <Stack spacing={2}>
        <Stack direction="row" alignItems="center" spacing={1}>
          <Button 
            variant="text" 
            startIcon={<ArrowBack />}
            onClick={() => router.push(`/assessments/runs/${runId}`)}
          >
            Back
          </Button>
          <Breadcrumbs 
            aria-label="breadcrumb"
            sx={{ '& .MuiBreadcrumbs-separator': { color: 'text.disabled' } }}
          >
            {runName ? (
              <MUILink
                underline="hover"
                color="text.secondary"
                onClick={() => router.push(`/assessments/runs/${runId}`)}
                sx={{ cursor: 'pointer', fontSize: '1.1rem', fontWeight: 500 }}
              >
                {runName}
              </MUILink>
            ) : (
              <Skeleton variant="text" width={260} height={28} />
            )}
            {applicantName ? (
              <MUILink
                underline="hover"
                color="text.primary"
                onClick={() => router.push(`/assessments/runs/${runId}/applicants/${applicantId}`)}
                sx={{ cursor: 'pointer', fontSize: '1.25rem', fontWeight: 700 }}
              >
                {applicantName}
              </MUILink>
            ) : (
              <Skeleton variant="text" width={240} height={28} />
            )}
          </Breadcrumbs>
        </Stack>

        <Paper sx={{ p: 2 }}>
          <Typography variant="h6" sx={{ mb: 2 }}>Agent Conversations</Typography>
          <ConversationView logs={filteredLogs} applicants={applicants} />
        </Paper>
      </Stack>
    </Container>
  );
}


