"use client";

import { useEffect, useMemo, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Container, Stack, Typography, Paper, Button, Breadcrumbs, Link as MUILink, Skeleton } from '@mui/material';
import { ArrowBack } from '@mui/icons-material';
import { useApi } from '../../../../../../lib/api';
import ApplicantResultView from '../../../../../../components/ApplicantResultView';

export default function ApplicantDetailNestedPage() {
  const params = useParams<{ id: string; applicantId: string }>();
  const runId = Number(params.id);
  const applicantId = Number(params.applicantId);
  const api = useApi();
  const router = useRouter();

  const [run, setRun] = useState<any>(null);
  const [report, setReport] = useState<any>(null);

  async function load() {
      const r = await api(`/assessments/runs/${runId}`);
      if (r.ok) setRun(await r.json());
      const rv = await api(`/reports/runs/${runId}`);
      if (rv.ok) setReport(await rv.json());
  }
  useEffect(() => { load(); }, [runId]);

  const item = useMemo(() => {
    const items = report?.items || [];
    return items.find((it: any) => it.applicant_id === applicantId) || null;
  }, [report, applicantId]);

  const runName = run?.name;
  const applicantName = item?.display_name || item?.folder;

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
          {item ? (
            <ApplicantResultView item={item} onChanged={load} />
          ) : (
            <Stack spacing={1}>
              <Skeleton variant="text" width={320} height={28} />
              <Skeleton variant="rectangular" height={120} />
              <Skeleton variant="rectangular" height={200} />
            </Stack>
          )}
        </Paper>
      </Stack>
    </Container>
  );
}


