"use client";

import React from 'react';
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
  TableContainer,
  TableSortLabel,
  Stack,
  Card,
  CardContent,
  IconButton,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Menu
} from '@mui/material';
import { CheckCircle, Cancel, Compare, EmojiEvents, Gavel, Visibility, MoreVert } from '@mui/icons-material';
import { useRouter } from 'next/navigation';

interface EvaluationData {
  items: Array<{
    applicant_id: number;
    display_name?: string | null;
    folder: string;
    gating?: {
      decision: string;
      reasons: string[];
    };
    ranking?: {
      weighted_score: number;
      final_rank: number;
      notes?: string;
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

export default function EvaluationProcess({ data, runId }: { data: EvaluationData; runId: number }) {
  if (!data) return null;

  const { items = [], pairwise = [] } = data;
  const router = useRouter();
  const [orderBy, setOrderBy] = React.useState<'score' | 'decision' | null>(null);
  const [order, setOrder] = React.useState<'asc' | 'desc'>('asc');
  const [decisionFilter, setDecisionFilter] = React.useState<'all' | 'accept' | 'middle' | 'reject'>('all');
  const [decisionMenuAnchor, setDecisionMenuAnchor] = React.useState<null | HTMLElement>(null);
  const [scoreFrom, setScoreFrom] = React.useState<string>('');
  const [scoreTo, setScoreTo] = React.useState<string>('');

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

  const decisionKey = (d: string) => {
    const s = (d || '').toLowerCase();
    if (s === 'pass' || s === 'accept') return 'accept';
    if (s === 'fail' || s === 'reject') return 'reject';
    if (s === 'middle') return 'middle';
    return s;
  };

  const handleRequestSort = (key: 'score' | 'decision') => {
    if (orderBy === key) setOrder(order === 'asc' ? 'desc' : 'asc'); else { setOrderBy(key); setOrder('asc'); }
  };

  const filteredAndSorted = items
    .filter((item) => {
      const d = decisionKey(item.gating?.decision || '');
      if (decisionFilter !== 'all' && d !== decisionFilter) return false;
      const s = item.ranking?.weighted_score ?? null;
      if (scoreFrom !== '' && s !== null && s < Number(scoreFrom)) return false;
      if (scoreTo !== '' && s !== null && s > Number(scoreTo)) return false;
      return true;
    })
    .sort((a, b) => {
      if (!orderBy) return 0;
      const dir = order === 'asc' ? 1 : -1;
      if (orderBy === 'score') {
        const av = a.ranking?.weighted_score ?? -Infinity;
        const bv = b.ranking?.weighted_score ?? -Infinity;
        return (av - bv) * dir;
      }
      const av = decisionKey(a.gating?.decision || '');
      const bv = decisionKey(b.gating?.decision || '');
      return av.localeCompare(bv) * dir;
    });

  return (
    <Stack spacing={3}>
      {/* Combined Results Table: Rank, Applicant, Weighted Score, Notes, AI Decision, Actions */}
      <Card elevation={2}>
        <CardContent>
          <Stack direction="row" alignItems="center" spacing={1} mb={2}>
            <Gavel color="primary" />
            <Typography variant="h6">
              Evaluation Results
            </Typography>
          </Stack>
          <Typography variant="body2" color="text.secondary" mb={2}>
            Hint: ACCEPT and REJECT candidates are excluded from scoring and ranking. MIDDLE candidates' ranks may be adjusted based on pairwise comparison results.
          </Typography>

          {/* Filters */}
          <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 1 }} />

          <TableContainer component={Paper} elevation={2}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 'bold' }}>Rank</TableCell>
                  <TableCell sx={{ fontWeight: 'bold' }}>Applicant</TableCell>
                  <TableCell sx={{ fontWeight: 'bold' }}>
                    <TableSortLabel
                      active={orderBy === 'score'}
                      direction={orderBy === 'score' ? order : 'asc'}
                      onClick={() => handleRequestSort('score')}
                    >
                      Weighted Score
                    </TableSortLabel>
                  </TableCell>
                  <TableCell sx={{ fontWeight: 'bold' }}>Notes</TableCell>
                  <TableCell sx={{ fontWeight: 'bold', position: 'relative', pr: 6, '&:hover .decision-menu-btn': { opacity: 1, pointerEvents: 'auto' } }}>
                    <TableSortLabel
                      active={orderBy === 'decision'}
                      direction={orderBy === 'decision' ? order : 'asc'}
                      onClick={() => handleRequestSort('decision')}
                    >
                      AI Decision
                    </TableSortLabel>
                    <IconButton size="small" className="decision-menu-btn" onClick={(e) => setDecisionMenuAnchor(e.currentTarget)} sx={{ position: 'absolute', right: 8, top: '50%', transform: 'translateY(-50%)', opacity: 0, pointerEvents: 'none', transition: 'opacity 0.2s' }}>
                      <MoreVert fontSize="small" />
                    </IconButton>
                  </TableCell>
                  <TableCell align="center" sx={{ fontWeight: 'bold' }}>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
              {filteredAndSorted
                .sort((a, b) => {
                  const aDecision = a.gating?.decision?.toLowerCase();
                  const bDecision = b.gating?.decision?.toLowerCase();

                  const aIsAccept = aDecision === 'accept' || aDecision === 'pass';
                  const bIsAccept = bDecision === 'accept' || bDecision === 'pass';
                  if (aIsAccept && !bIsAccept) return -1;
                  if (!aIsAccept && bIsAccept) return 1;

                  const aIsReject = aDecision === 'reject';
                  const bIsReject = bDecision === 'reject';
                  if (aIsReject && !bIsReject) return 1;
                  if (!aIsReject && bIsReject) return -1;

                  const aIsMiddle = aDecision === 'middle';
                  const bIsMiddle = bDecision === 'middle';
                  if (aIsMiddle && bIsMiddle && a.ranking && b.ranking) {
                    return (a.ranking?.final_rank || 999) - (b.ranking?.final_rank || 999);
                  }

                  return 0;
                })
                .map((item) => {
                  const finalRank = item.ranking?.final_rank ?? null;
                  const weightedScore = item.ranking?.weighted_score;
                  const notes = item.ranking?.notes;
                  const decisionRaw = item.gating?.decision || '';
                  const decision = decisionRaw.toLowerCase();
                  const isReject = decision === 'reject';
                  const isAccept = decision === 'accept' || decision === 'pass';

                  return (
                    <TableRow key={item.applicant_id} sx={{ '&:hover': { backgroundColor: 'action.hover' } }}>
                      <TableCell sx={{ py: 2 }}>
                        {isAccept ? (
                          <Chip label="—" color="success" size="small" variant="outlined" />
                        ) : isReject ? (
                          <Chip label="—" color="error" size="small" variant="outlined" />
                        ) : (
                          <Chip
                            label={finalRank ? `#${finalRank}` : '—'}
                            color={finalRank && finalRank <= 3 ? 'primary' : 'default'}
                            size="small"
                          />
                        )}
                      </TableCell>
                      <TableCell sx={{ py: 2 }}>
                        <Typography variant="body2" fontWeight="medium">
                          {item.display_name || item.folder}
                        </Typography>
                      </TableCell>
                      <TableCell sx={{ py: 2 }}>
                        <Typography variant="body2">
                          {isAccept || isReject ? '—' : (weightedScore?.toFixed(2) || '—')}
                        </Typography>
                      </TableCell>
                      <TableCell sx={{ py: 2 }}>
                        {isAccept || isReject ? (
                          <Typography variant="body2" color="text.secondary">—</Typography>
                        ) : notes ? (
                          <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.75rem', maxWidth: 250, wordBreak: 'break-word' }}>
                            {notes}
                          </Typography>
                        ) : (
                          <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                            No adjustments
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell sx={{ py: 2 }}>
                        <Chip
                          icon={getGatingIcon(decisionRaw)}
                          label={decisionRaw || 'Pending'}
                          color={getGatingColor(decisionRaw)}
                          size="small"
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell align="center" sx={{ py: 2 }}>
                        <IconButton 
                          color="primary" 
                          onClick={() => router.push(`/assessments/runs/${runId}/applicants/${item.applicant_id}`)}
                          title="View"
                        >
                          <Visibility />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      <Menu
        anchorEl={decisionMenuAnchor}
        open={Boolean(decisionMenuAnchor)}
        onClose={() => setDecisionMenuAnchor(null)}
      >
        <MenuItem selected={decisionFilter === 'all'} onClick={() => { setDecisionFilter('all'); setDecisionMenuAnchor(null); }}>All</MenuItem>
        <MenuItem selected={decisionFilter === 'accept'} onClick={() => { setDecisionFilter('accept'); setDecisionMenuAnchor(null); }}>Accept</MenuItem>
        <MenuItem selected={decisionFilter === 'middle'} onClick={() => { setDecisionFilter('middle'); setDecisionMenuAnchor(null); }}>Middle</MenuItem>
        <MenuItem selected={decisionFilter === 'reject'} onClick={() => { setDecisionFilter('reject'); setDecisionMenuAnchor(null); }}>Reject</MenuItem>
      </Menu>

      {/* Pairwise Comparisons */}
      {pairwise.length > 0 && (
        <Card elevation={2}>
          <CardContent>
            <Stack direction="row" alignItems="center" spacing={1} mb={2}>
              <Compare color="primary" />
              <Typography variant="h6">
                Pairwise Comparisons
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