"use client";
import { useParams } from 'next/navigation';
import { useApi } from '../../../lib/api';
import { useEffect, useState } from 'react';
import { Alert, Paper, Stack, Typography, Container, Card, CardContent, List, ListItem, ListItemIcon, ListItemText, Divider, Box, Chip } from '@mui/material';
import { CheckCircle, Cancel, Star, Group, Assignment } from '@mui/icons-material';

export default function ReportPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const api = useApi();
  const [report, setReport] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(()=> { (async () => {
    const r = await api(`/reports/runs/${id}`);
    if (r.ok) setReport(await r.json()); else setError('Failed to load report');
  })(); }, [id]);

  const items = report?.items || [];
  
  // 分析数据生成录取建议
  const acceptedCandidates = items.filter(item => 
    item.gating?.decision?.toLowerCase() === 'pass' || 
    item.gating?.decision?.toLowerCase() === 'accept'
  ).sort((a, b) => (a.ranking?.final_rank || 999) - (b.ranking?.final_rank || 999));
  
  const rejectedCandidates = items.filter(item => 
    item.gating?.decision?.toLowerCase() === 'fail' || 
    item.gating?.decision?.toLowerCase() === 'reject'
  );
  
  const borderlineCandidates = items
    .filter(item => item.gating?.decision?.toLowerCase() === 'middle')
    .sort((a, b) => (a.ranking?.final_rank || 999) - (b.ranking?.final_rank || 999));
  
  const topCandidates = acceptedCandidates.slice(0, 3);
  const middleTierCandidates = acceptedCandidates.slice(3);

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Stack spacing={4}>
      <Box textAlign="center">
        <Typography variant="h4" gutterBottom>
          📊 Evaluation Report
        </Typography>
        <Typography variant="h6" color="text.secondary">
          Run #{id} - Final Admission Recommendations
        </Typography>
      </Box>
      {error && <Alert severity="error">{error}</Alert>}
      
      {!report ? (
        <Typography>Loading...</Typography>
      ) : (
        <>
          {/* 录取建议总结 */}
          <Card elevation={3}>
            <CardContent>
              <Typography variant="h5" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Assignment color="primary" />
                Final Admission Recommendations
              </Typography>
              
              <Typography variant="body1" color="text.secondary" paragraph>
                Based on comprehensive evaluation including document screening, weighted scoring, and comparative analysis, 
                here are our admission recommendations:
              </Typography>
              
              <Stack spacing={3}>
                {/* 强烈推荐录取 */}
                {topCandidates.length > 0 && (
                  <Box>
                    <Typography variant="h6" sx={{ color: 'success.main', mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Star /> Strongly Recommended for Admission
                    </Typography>
                    <List>
                      {topCandidates.map((candidate, index) => (
                        <ListItem key={candidate.applicant_id}>
                          <ListItemIcon>
                            <CheckCircle color="success" />
                          </ListItemIcon>
                          <ListItemText
                            primary={`${candidate.folder} (Rank #${candidate.ranking?.final_rank})`}
                            secondary={`Weighted Score: ${candidate.ranking?.weighted_score?.toFixed(2)} | ${candidate.gating?.reasons?.join(', ')}`}
                          />
                        </ListItem>
                      ))}
                    </List>
                  </Box>
                )}
                
                {/* 中等优先级 */}
                {middleTierCandidates.length > 0 && (
                  <Box>
                    <Typography variant="h6" sx={{ color: 'info.main', mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Group /> Middle Tier - Consider Based on Capacity
                    </Typography>
                    <Typography variant="body2" color="text.secondary" paragraph>
                      These candidates meet requirements but should be considered based on available spots:
                    </Typography>
                    <List>
                      {middleTierCandidates.map((candidate) => (
                        <ListItem key={candidate.applicant_id}>
                          <ListItemIcon>
                            <CheckCircle color="info" />
                          </ListItemIcon>
                          <ListItemText
                            primary={`${candidate.folder} (Rank #${candidate.ranking?.final_rank})`}
                            secondary={`Weighted Score: ${candidate.ranking?.weighted_score?.toFixed(2)}`}
                          />
                        </ListItem>
                      ))}
                    </List>
                  </Box>
                )}
                
                {/* 中等案例 */}
                {borderlineCandidates.length > 0 && (
                  <Box>
                    <List>
                      {borderlineCandidates.map((candidate) => (
                        <ListItem key={candidate.applicant_id}>
                          <ListItemIcon>
                            <Chip label="?" size="small" color="warning" />
                          </ListItemIcon>
                          <ListItemText
                            primary={candidate.folder}
                            secondary={candidate.gating?.reasons?.join(', ')}
                          />
                        </ListItem>
                      ))}
                    </List>
                  </Box>
                )}
                
                {/* 不建议录取 */}
                {rejectedCandidates.length > 0 && (
                  <Box>
                    <Typography variant="h6" sx={{ color: 'error.main', mb: 2 }}>
                      ❌ Not Recommended for Admission
                    </Typography>
                    <List>
                      {rejectedCandidates.map((candidate) => (
                        <ListItem key={candidate.applicant_id}>
                          <ListItemIcon>
                            <Cancel color="error" />
                          </ListItemIcon>
                          <ListItemText
                            primary={candidate.folder}
                            secondary={candidate.gating?.reasons?.join(', ')}
                          />
                        </ListItem>
                      ))}
                    </List>
                  </Box>
                )}
              </Stack>
            </CardContent>
          </Card>
          
          {/* 总结统计 */}
          <Card elevation={2}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                📈 Summary Statistics
              </Typography>
              <Stack direction="row" spacing={4} justifyContent="center">
                <Box textAlign="center">
                  <Typography variant="h4" color="success.main">{acceptedCandidates.length}</Typography>
                  <Typography variant="body2">Qualified</Typography>
                </Box>
                <Box textAlign="center">
                  <Typography variant="h4" color="warning.main">{borderlineCandidates.length}</Typography>
                  <Typography variant="body2">Middle</Typography>
                </Box>
                <Box textAlign="center">
                  <Typography variant="h4" color="error.main">{rejectedCandidates.length}</Typography>
                  <Typography variant="body2">Rejected</Typography>
                </Box>
                <Box textAlign="center">
                  <Typography variant="h4" color="primary.main">{items.length}</Typography>
                  <Typography variant="body2">Total</Typography>
                </Box>
              </Stack>
            </CardContent>
          </Card>
        </>
      )}
      </Stack>
    </Container>
  );
}

