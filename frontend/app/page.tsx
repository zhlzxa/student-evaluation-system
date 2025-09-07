"use client";
import { Button, Card, CardContent, Box, Stack, Typography, Alert } from '@mui/material';
import { useRouter } from 'next/navigation';
import { useApiQuery } from '../lib/useApiQuery';
import { Loading } from '../components/ui/Loading';

export default function Home() {
  const router = useRouter();
  
  const runs = useApiQuery(['runs'], '/assessments/runs?visible_only=true', {
    retry: 2,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  return (
    <Stack spacing={2}>
      <Typography variant="h5">Dashboard</Typography>
      <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
        <Card sx={{ flex: '1 1 320px' }}>
          <CardContent>
            <Typography variant="h6">Quick Actions</Typography>
            <Button 
              variant="contained" 
              sx={{ mt: 1 }} 
              onClick={() => router.push('/assessments/new')}
            >
              New Assessment
            </Button>
          </CardContent>
        </Card>
        <Card sx={{ flex: '1 1 320px' }}>
          <CardContent>
            <Typography variant="h6">Recent Evaluations</Typography>
            {runs.isLoading ? (
              <Loading message="Loading runs..." size={24} />
            ) : runs.isError ? (
              <Alert severity="error" sx={{ mt: 1 }}>
                Failed to load runs
              </Alert>
            ) : (
              <>
                <Typography variant="body2" sx={{ mt: 1 }}>
                  Count: {Array.isArray(runs.data) ? runs.data.length : 0}
                </Typography>
                <Button 
                  sx={{ mt: 1 }} 
                  onClick={() => router.push('/assessments')}
                >
                  View all
                </Button>
              </>
            )}
          </CardContent>
        </Card>
      </Box>
    </Stack>
  );
}
