"use client";

import { 
  Box, 
  Paper, 
  Typography, 
  Chip,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Stack,
  Divider,
  Card,
  CardContent,
  LinearProgress
} from '@mui/material';
import { CheckCircle, Cancel, Compare, EmojiEvents, Gavel } from '@mui/icons-material';

interface EvaluationData {
  items: Array<{
    applicant_id: number;
    folder: string;
    gating?: {
      decision: string;
      reasons: string[];
    };
    ranking?: {
      weighted_score: number;
      final_rank: number;
    };
  }>;
  pairwise: Array<{
    pass: number;
    a: string;
    b: string;
    winner: string;
    reason: string;
  }>;
}

export default function EvaluationProcess({ data }: { data: EvaluationData }) {
  if (!data) return null;

  const { items = [], pairwise = [] } = data;

  const getGatingColor = (decision: string) => {
    switch (decision?.toLowerCase()) {
      case 'pass': case 'accept': return 'success';
      case 'fail': case 'reject': return 'error';
      case 'maybe': case 'borderline': return 'warning';
      default: return 'default';
    }
  };

  const getGatingIcon = (decision: string) => {
    switch (decision?.toLowerCase()) {
      case 'pass': case 'accept': return <CheckCircle />;
      case 'fail': case 'reject': return <Cancel />;
      default: return <Gavel />;
    }
  };

  return (
    <Stack spacing={3}>
      {/* Gating Results */}
      <Card elevation={2}>
        <CardContent>
          <Stack direction="row" alignItems="center" spacing={1} mb={2}>
            <Gavel color="primary" />
            <Typography variant="h6">
              Step 1: Gating Results
            </Typography>
          </Stack>
          <Typography variant="body2" color="text.secondary" mb={2}>
            Initial screening to filter candidates who meet minimum requirements
          </Typography>
          
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Applicant</TableCell>
                <TableCell>Decision</TableCell>
                <TableCell>Reasons</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {items.map((item) => (
                <TableRow key={item.applicant_id}>
                  <TableCell>
                    <Typography variant="body2" fontWeight="medium">
                      {item.folder}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      icon={getGatingIcon(item.gating?.decision || '')}
                      label={item.gating?.decision || 'Pending'}
                      color={getGatingColor(item.gating?.decision || '')}
                      size="small"
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {item.gating?.reasons?.join('; ') || 'No reasons provided'}
                    </Typography>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Ranking Results */}
      <Card elevation={2}>
        <CardContent>
          <Stack direction="row" alignItems="center" spacing={1} mb={2}>
            <EmojiEvents color="primary" />
            <Typography variant="h6">
              Step 2: Weighted Ranking
            </Typography>
          </Stack>
          <Typography variant="body2" color="text.secondary" mb={2}>
            Candidates ranked by weighted evaluation scores
          </Typography>

          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Rank</TableCell>
                <TableCell>Applicant</TableCell>
                <TableCell>Weighted Score</TableCell>
                <TableCell>Progress</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {items
                .filter(item => item.ranking)
                .sort((a, b) => (a.ranking?.final_rank || 999) - (b.ranking?.final_rank || 999))
                .map((item) => (
                  <TableRow key={item.applicant_id}>
                    <TableCell>
                      <Chip
                        label={`#${item.ranking?.final_rank}`}
                        color={item.ranking?.final_rank <= 3 ? 'primary' : 'default'}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" fontWeight="medium">
                        {item.folder}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {item.ranking?.weighted_score?.toFixed(2) || 'N/A'}
                      </Typography>
                    </TableCell>
                    <TableCell width="120px">
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <LinearProgress
                          variant="determinate"
                          value={((item.ranking?.weighted_score || 0) / 100) * 100}
                          sx={{ flexGrow: 1, mr: 1, height: 6, borderRadius: 1 }}
                          color={item.ranking?.final_rank <= 3 ? 'primary' : 'inherit'}
                        />
                        <Typography variant="caption">
                          {((item.ranking?.weighted_score || 0) * 100).toFixed(0)}%
                        </Typography>
                      </Box>
                    </TableCell>
                  </TableRow>
                ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Pairwise Comparisons */}
      {pairwise.length > 0 && (
        <Card elevation={2}>
          <CardContent>
            <Stack direction="row" alignItems="center" spacing={1} mb={2}>
              <Compare color="primary" />
              <Typography variant="h6">
                Step 3: Pairwise Comparisons
              </Typography>
            </Stack>
            <Typography variant="body2" color="text.secondary" mb={2}>
              Head-to-head comparisons for final ranking refinement
            </Typography>

            <Stack spacing={2}>
              {pairwise.map((comparison, index) => (
                <Paper key={index} variant="outlined" sx={{ p: 2 }}>
                  <Stack direction="row" alignItems="center" spacing={2}>
                    <Chip label={`Pass ${comparison.pass}`} size="small" variant="outlined" />
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="body2" fontWeight="medium">
                        {comparison.a}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">vs</Typography>
                      <Typography variant="body2" fontWeight="medium">
                        {comparison.b}
                      </Typography>
                    </Box>
                    <Typography variant="body2" color="text.secondary">→</Typography>
                    <Chip 
                      label={comparison.winner} 
                      color="success" 
                      size="small" 
                    />
                  </Stack>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1, ml: 4 }}>
                    {comparison.reason}
                  </Typography>
                </Paper>
              ))}
            </Stack>
          </CardContent>
        </Card>
      )}
    </Stack>
  );
}