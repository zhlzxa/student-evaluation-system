"use client";

import React from "react";
import {
  Box,
  Card,
  CardContent,
  CardHeader,
  Chip,
  Divider,
  Stack,
  Typography,
  Avatar,
  List,
  ListItem,
  ListItemText,
  alpha,
  useTheme,
  Fade,
  Zoom,
  Badge,
  Button,
  ButtonGroup,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from "@mui/material";
import { 
  CheckCircle, 
  Cancel, 
  Gavel, 
  Person,
  TrendingUp,
  TrendingDown,
  School,
  Work,
  Language,
  AssignmentTurnedIn,
  Analytics,
  Star,
  Warning,
  Psychology,
  Assessment,
} from "@mui/icons-material";
import { useApi } from "@/lib/api";
import { useToast } from "@/components/providers/ToastProvider";

type EvaluationItem = {
  agent: string;
  score: number | null;
  details?: Record<string, unknown> | null;
};

type ApplicantItem = {
  applicant_id: number;
  display_name?: string | null;
  folder: string;
  evaluations?: EvaluationItem[];
  gating?: {
    decision?: string | null;
    reasons?: string[] | null;
    manual_decision?: string | null;
    manual_set_at?: string | null;
  } | null;
  ranking?: {
    weighted_score?: number | null;
    final_rank?: number | null;
    notes?: string | null;
  } | null;
};

function mapAgentName(agent: string): string {
  const map: Record<string, string> = {
    english: "English Proficiency",
    degree: "Degree Qualification",
    experience: "Experience",
    ps_rl: "Personal Statement & References",
    academic: "Academic Publications",
    compare: "Comparison Analysis",
    classifier: "Classification",
    detector: "Detection Analysis",
  };
  return map[agent] || agent;
}

function getAgentIcon(agent: string) {
  const map: Record<string, React.ReactNode> = {
    english: <Language fontSize="inherit" />,
    degree: <School fontSize="inherit" />,
    experience: <Work fontSize="inherit" />,
    ps_rl: <AssignmentTurnedIn fontSize="inherit" />,
    academic: <Psychology fontSize="inherit" />,
    compare: <Assessment fontSize="inherit" />,
    classifier: <Star fontSize="inherit" />,
    detector: <Warning fontSize="inherit" />,
  };
  return map[agent] || <Person fontSize="inherit" />;
}

function getScoreColor(score: number | null): 'success' | 'warning' | 'error' | 'default' {
  if (score === null || score === undefined) return 'default';
  if (score >= 8) return 'success';
  if (score >= 5) return 'warning';
  return 'error';
}

function decisionColor(decision?: string | null):
  | "default"
  | "success"
  | "error"
  | "warning" {
  const d = (decision || "").toLowerCase();
  if (d === "accept" || d === "pass") return "success";
  if (d === "reject" || d === "fail") return "error";
  if (d === "middle" || d === "maybe" || d === "borderline") return "warning";
  return "default";
}

function decisionIcon(decision?: string | null) {
  const d = (decision || "").toLowerCase();
  if (d === "accept" || d === "pass") return <CheckCircle />;
  if (d === "reject" || d === "fail") return <Cancel />;
  return <Gavel />;
}

// (Removed unused isPrimitive helper)

function defaultLabel(key: string): string {
  const s = key.replace(/_/g, " ");
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function normalizeAgent(agent: string): string {
  const a = agent.toLowerCase();
  const map: Record<string, string> = {
    "english proficiency": "english",
    "degree qualification": "degree",
    "work experience": "experience",
    "personal statement & references": "ps_rl",
    "personal statement and references": "ps_rl",
    "academic background": "academic",
    "comparison analysis": "compare",
    "classification": "classifier",
    "detection analysis": "detector",
  };
  return map[a] || a;
}

function getFieldLabel(agent: string, key: string): string {
  const a = normalizeAgent(agent);
  const k = key.toLowerCase();
  if (a === "english") {
    const map: Record<string, string> = {
      exemption: "Exempt from English requirement",
      test_type: "Test type",
      test_overall: "Overall test score",
      level: "Required level",
      evidence: "Evidence",
    };
    return map[k] || defaultLabel(key);
  }
  if (a === "degree") {
    const map: Record<string, string> = {
      country: "Degree-awarding country",
      institution: "Institution",
      meets_requirement: "Meets minimum requirement",
      qs_rank: "QS world rank",
      subject_fit: "Subject relevance",
      missing_prerequisites: "Missing prerequisites",
      policy_source: "Policy source",
      evidence: "Evidence",
    };
    return map[k] || defaultLabel(key);
  }
  if (a === "experience") {
    const map: Record<string, string> = {
      highlights: "Experience highlights",
      evidence: "Evidence",
    };
    return map[k] || defaultLabel(key);
  }
  if (a === "ps_rl") {
    const map: Record<string, string> = {
      strengths: "Strengths (with evidence)",
      weaknesses: "Weaknesses (with evidence)",
      evidence: "Evidence",
    };
    return map[k] || defaultLabel(key);
  }
  if (a === "academic") {
    const map: Record<string, string> = {
      papers: "Publications",
      evidence: "Evidence",
    };
    return map[k] || defaultLabel(key);
  }
  // Fallback for other agents (classifier, detector, compare)
  return defaultLabel(key);
}

function KeyValueRows({ data, agent }: { data: Record<string, unknown>; agent: string }) {
  const formatPrimitive = (v: unknown): string => {
    if (v === null || v === undefined) return "N/A";
    if (typeof v === "boolean") return v ? "Yes" : "No";
    if (typeof v === "string" && agent.toLowerCase() === "english" && v.toLowerCase().startsWith("level")) {
      const n = v.replace(/[^0-9]/g, "");
      return n ? `Level ${n}` : v;
    }
    return String(v);
  };

  const SECTION_KEYS = new Set(["missing_prerequisites", "evidence", "papers", "policy_source"]);
  const entries = Object.entries(data);
  const baseEntries = entries.filter(([k]) => !SECTION_KEYS.has(k.toLowerCase()));

  const toList = (val: unknown): string[] => {
    if (Array.isArray(val)) return (val as unknown[]).map((x) => String(x)).filter(Boolean);
    if (typeof val === "string") return val.split(/\n|\u2022|\-|\;/).map((s) => s.trim()).filter(Boolean);
    return [];
  };
  const missingList = toList((data as any).missing_prerequisites);
  const evidenceList = toList((data as any).evidence);
  const policySource = (data as any).policy_source as string | undefined;

  const hasBase = baseEntries.length > 0;
  const hasSections = (missingList.length > 0 || evidenceList.length > 0 || policySource);
  return (
    <Box sx={{ mt: hasBase ? 1 : 0.5 }}>
      {hasBase && (
        <Stack spacing={1.25}>
        {baseEntries.map(([key, value]) => (
          <Box key={key} sx={{ display: 'flex', gap: 2, my: 0.25, alignItems: 'flex-start' }}>
            <Box sx={{ flex: '0 0 140px' }}>
              <Typography color="text.secondary" sx={{ fontSize: '0.75rem', fontWeight: 500, lineHeight: 1.4, mt: 0.25 }}>{getFieldLabel(agent, key)}</Typography>
            </Box>
            <Box sx={{ flex: 1, minWidth: 0 }}>
              {Array.isArray(value) ? (
                (() => {
                  const arr = value as unknown[];
                  const hasObject = arr.some(v => typeof v === 'object' && v !== null && !Array.isArray(v));
                  if (!hasObject) {
                    return <Typography variant="body2" sx={{ wordBreak: 'break-word' }}>{arr.map(v => String(v)).join(', ')}</Typography>;
                  }
                  const keyLower = key.toLowerCase();
                  const isPs = normalizeAgent(agent) === 'ps_rl';
                  const isStrengthWeakness = isPs && (keyLower === 'strengths' || keyLower === 'weaknesses');
                  if (isStrengthWeakness) {
                    const pickText = (o: any): string => {
                      if (!o) return '';
                      if (typeof o === 'string') return o;
                      const candidates = ['text','statement','summary','value','highlight','reason','point'];
                      for (const c of candidates) if (typeof o[c] === 'string' && o[c].trim()) return o[c];
                      return JSON.stringify(o).slice(0,140);
                    };
                    const extractEvidence = (o: any): string[] => {
                      if (!o || typeof o !== 'object') return [];
                      const evKeys = ['evidence','support','details','examples','citations'];
                      let collected: string[] = [];
                      for (const k of evKeys) {
                        const v = (o as any)[k];
                        if (!v) continue;
                        if (Array.isArray(v)) collected = collected.concat(v.map(x=>String(x)).filter(Boolean));
                        else if (typeof v === 'string') {
                          const parts = v.split(/\n|\r|\u2022|\-/).map(s=>s.trim()).filter(Boolean);
                          collected = collected.concat(parts.length?parts:[v]);
                        }
                      }
                      return collected.slice(0,5); // cap for layout
                    };
                    return (
                      <Stack spacing={1} sx={{ mt: 0.25 }}>
                        {arr.map((obj, i) => {
                          const text = pickText(obj as any);
                          const evList = extractEvidence(obj as any);
                          return (
                            <Box key={i}>
                              <Typography variant="body2" sx={{ lineHeight: 1.4, fontWeight: 500 }}>{text}</Typography>
                              {evList.length > 0 && (
                                <Box component="ul" sx={{ pl: 2, m: 0.25, mt: 0.5 }}>
                                  {evList.map((e, ei) => (
                                    <Typography key={ei} component="li" variant="caption" color="text.secondary" sx={{ lineHeight: 1.3 }}>
                                      {e}
                                    </Typography>
                                  ))}
                                </Box>
                              )}
                            </Box>
                          );
                        })}
                      </Stack>
                    );
                  }
                  // Array of objects -> render list
                  const pickText = (o: any): string => {
                    if (o == null) return '';
                    if (typeof o === 'string') return o;
                    const textKeys = ['text','description','summary','value','statement','content','highlight','reason'];
                    for (const k of textKeys) {
                      if (typeof o[k] === 'string' && o[k].trim()) return o[k];
                    }
                    // fallback: first primitive string value
                    for (const k of Object.keys(o)) {
                      const val = o[k];
                      if (typeof val === 'string' && val.trim()) return val;
                    }
                    const json = JSON.stringify(o);
                    return json.length > 140 ? json.slice(0,137)+'…' : json;
                  };
                  return (
                    <Stack spacing={0.75} sx={{ mt: 0.25 }}>
                      {arr.map((obj, i) => (
                        <Typography key={i} variant="body2" sx={{ lineHeight: 1.4 }}>
                          {pickText(obj as any)}
                        </Typography>
                      ))}
                    </Stack>
                  );
                })()
              ) : (
                typeof value === 'object' && value !== null ? (
                  <Box component="pre" sx={{ m: 0, p: 1, bgcolor: 'grey.50', borderRadius: 1, whiteSpace: 'pre-wrap', overflow: 'auto', fontSize: '0.7rem', lineHeight: 1.4 }}>{JSON.stringify(value, null, 2)}</Box>
                ) : (
                  <Typography sx={{ fontWeight: 500, wordBreak: 'break-word' }}>{formatPrimitive(value)}</Typography>
                )
              )}
            </Box>
          </Box>
        ))}
        </Stack>
      )}

      {hasSections && (
        <Divider sx={{ my: hasBase ? 2 : 1 }} />
      )}

      {missingList.length > 0 && (
        <Box sx={{ mb: 1.5 }}>
          <Typography variant="subtitle2" color="text.secondary">Missing prerequisites</Typography>
          <List dense>
            {missingList.map((t, i) => (
              <ListItem key={i} sx={{ py: 0.25 }}>
                <ListItemText primaryTypographyProps={{ variant: 'body2' }} primary={t} />
              </ListItem>
            ))}
          </List>
        </Box>
      )}

      {evidenceList.length > 0 && (
        <Box sx={{ mb: 1.5 }}>
          <Typography variant="subtitle2" color="text.secondary">Evidence from documents</Typography>
          <List dense>
            {evidenceList.map((t, i) => (
              <ListItem key={i} sx={{ py: 0.25 }}>
                <ListItemText primaryTypographyProps={{ variant: 'body2' }} primary={t} />
              </ListItem>
            ))}
          </List>
        </Box>
      )}

      {policySource && (
        <>
          <Divider sx={{ my: 2 }} />
          <Typography variant="body2" color="text.secondary">{policySource}</Typography>
        </>
                          )}
                        </Box>
                      );
                    }

function ScoreChip({ score }: { score: number | null | undefined }) {
  const getColor = (s: number | null | undefined): 'success' | 'warning' | 'error' | 'default' => {
    if (s === null || s === undefined) return 'default';
    if (s >= 8) return 'success';
    if (s >= 5) return 'warning';
    return 'error';
  };
  return <Chip label={`Score: ${score ?? 'N/A'}`} color={getColor(score)} size="small" />;
}

function EvaluationCard({ item }: { item: EvaluationItem }) {
  const theme = useTheme();
  const rawDetails = item.details || {};
  const details = { ...(rawDetails as Record<string, unknown>) };
  // Remove score field from details if present so it's not duplicated
  if ('score' in details) { delete (details as any).score; }
  const hasDetails = Object.keys(details).length > 0;
  const scoreColor = getScoreColor(item.score);
  
  return (
    // Zoom applies inline-block to the child; wrap with a full-width Box
    <Zoom in={true} timeout={300}>
      <Box sx={{ width: '100%', display: 'block' }}>
    <Card 
        elevation={0}
        sx={{ 
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          '&:hover': {
            transform: 'translateY(-4px)',
            boxShadow: theme.shadows[8],
          },
          borderRadius: 3,
          background: theme.palette.background.paper,
          backdropFilter: 'blur(20px)',
          border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
          position: 'relative',
          overflow: 'hidden',
          borderLeft: `4px solid ${(theme.palette as any)[scoreColor === 'default' ? 'grey' : scoreColor].main}`,
          width: '100%',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <CardHeader
          avatar={
            <Avatar sx={{ bgcolor: alpha((theme.palette as any)[scoreColor === 'default' ? 'grey' : scoreColor].main, 0.15), color: (theme.palette as any)[scoreColor === 'default' ? 'grey' : scoreColor].main }}>
              {getAgentIcon(item.agent)}
                  </Avatar>
                }
          action={<ScoreChip score={item.score ?? null} />}
          title={mapAgentName(item.agent)}
          titleTypographyProps={{ variant: 'h6' }}
          sx={{ pb: 0, pr: 2, pl: 2 }}
        />
        <CardContent sx={{ p: 2, pt: 1, height: '100%', display: 'flex', flexDirection: 'column' }}>
          <Stack spacing={2} sx={{ flex: 1 }}>
            {/* Removed progress bar section to reduce clutter */}

            {hasDetails && (
              <Box sx={{ mt: 1, flex: 1 }}>
                <Box sx={{ p: 1 }}>
                    <KeyValueRows agent={item.agent} data={details as Record<string, unknown>} />
                  </Box>
              </Box>
            )}
          </Stack>
        </CardContent>
      </Card>
      </Box>
    </Zoom>
  );
}

export default function ApplicantResultView({ item, onChanged }: { item: ApplicantItem, onChanged?: () => void | Promise<void> }) {
  const theme = useTheme();
  const name = item.display_name || item.folder;
  const decision = item.gating?.decision || "Pending";
  const reasons = item.gating?.reasons || [];
  const manualDecision = item.gating?.manual_decision || null;
  const weighted = item.ranking?.weighted_score ?? null;
  const rank = item.ranking?.final_rank ?? null;
  const notes = item.ranking?.notes || "";
  const decisionNorm = (decision || "").toLowerCase();
  const isTerminal = decisionNorm === "accept" || decisionNorm === "pass" || decisionNorm === "reject" || decisionNorm === "fail";
  const api = useApi();
  const { addToast } = useToast();
  const [confirmClearOpen, setConfirmClearOpen] = React.useState(false);

  async function setManualDecision(decision: 'ACCEPT' | 'MIDDLE' | 'REJECT' | null) {
    try {
      const res = await api(`/assessments/applicants/${item.applicant_id}/manual-decision`, {
        method: 'PUT',
        body: JSON.stringify({ decision })
      });
      if (!res.ok) throw new Error(`API error ${res.status}`);
      addToast({ message: decision ? `Set ${decision}` : 'Cleared teacher decision', severity: 'success' });
      await onChanged?.();
    } catch (e: any) {
      addToast({ message: e?.message || 'Operation failed', severity: 'error' });
    }
  }

  // Compute highlights from evaluations (if scores exist)
  const scored = (item.evaluations || []).filter((e) => typeof e.score === "number") as Array<Required<Pick<EvaluationItem, "agent" | "score">>>;
  const top = scored.length > 0 ? scored.reduce((a, b) => (b.score! > a.score! ? b : a)) : null;
  const bottom = scored.length > 0 ? scored.reduce((a, b) => (b.score! < a.score! ? b : a)) : null;

  // Sort evaluations for a clear, consistent order
  const order: Record<string, number> = {
    english: 1,
    degree: 2,
    academic: 3,
    experience: 4,
    ps_rl: 5,
    classifier: 6,
    detector: 7,
    compare: 8,
  };
  const evals = (item.evaluations || []).slice().sort((a, b) => {
    const oa = order[a.agent] ?? 99;
    const ob = order[b.agent] ?? 99;
    if (oa !== ob) return oa - ob;
    return a.agent.localeCompare(b.agent);
  });

  const decisionColorValue = decisionColor(decision);
  const getMainColor = (c: "default" | "success" | "error" | "warning") => {
    if (c === 'success') return theme.palette.success.main;
    if (c === 'error') return theme.palette.error.main;
    if (c === 'warning') return theme.palette.warning.main;
    return theme.palette.grey[500];
  };
  const headerBackground = (() => {
    const main = getMainColor(decisionColorValue);
    return alpha(main, 0.1);
  })();

  return (
    <>
    <Fade in={true} timeout={500}>
  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
        {/* Header Section */}
  <Box>
        <Card 
          elevation={0}
          sx={{ 
            borderRadius: 3,
            background: `linear-gradient(135deg, ${headerBackground} 0%, ${alpha(theme.palette.background.paper, 0.95)} 100%)`,
            backdropFilter: 'blur(20px)',
            border: `1px solid ${alpha(getMainColor(decisionColorValue), 0.2)}`,
            position: 'relative',
            overflow: 'hidden',
            '&::before': {
              content: '""',
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              height: 3,
              background: `linear-gradient(90deg, ${getMainColor(decisionColorValue)}, ${alpha(getMainColor(decisionColorValue), 0.6)})`,
            },
            width: '100%'
          }}
        >
          <CardContent sx={{ p: 2 }}>
            <Stack spacing={2}>
              {/* Name and Decision */}
              <Stack direction="row" alignItems="center" justifyContent="space-between" flexWrap="wrap" gap={1.5}>
                <Stack direction="row" alignItems="center" spacing={2}>
                  <Badge
                    overlap="circular"
                    anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
                    badgeContent={
                      <Avatar
                        sx={{
                          width: 18,
                          height: 18,
                          bgcolor: getMainColor(decisionColorValue),
                          boxShadow: `0 2px 8px ${alpha(getMainColor(decisionColorValue), 0.4)}`,
                        }}
                      >
                        {decisionIcon(decision)}
                      </Avatar>
                    }
                  >
                    <Avatar 
                      sx={{ 
                        width: 44, 
                        height: 44,
                        bgcolor: alpha(getMainColor(decisionColorValue), 0.15),
                        color: getMainColor(decisionColorValue),
                        fontSize: '1.25rem',
                        boxShadow: `0 4px 12px ${alpha(getMainColor(decisionColorValue), 0.15)}`,
                        border: `2px solid ${alpha(getMainColor(decisionColorValue), 0.25)}`,
                      }}
                    >
                      <Person fontSize="large" />
                    </Avatar>
                  </Badge>
                  <Stack>
                    <Typography variant="h5" fontWeight={800} color="text.primary" sx={{ mb: 0.25, letterSpacing: '-0.02em' }}>
                      {name}
                    </Typography>
                    <Stack direction="row" alignItems="center" spacing={1.5}>
                      <Typography variant="subtitle1" color="text.secondary" fontWeight={500}>
                        Application Status
                      </Typography>
                      <Chip
                        color={decisionColorValue}
                        icon={decisionIcon(decision)}
                        label={decision?.toUpperCase() || "PENDING"}
                        size="small"
                        variant="filled"
                        sx={{ 
                          fontWeight: 700,
                          fontSize: '0.75rem',
                          height: 26,
                          px: 1,
                          '& .MuiChip-icon': {
                            fontSize: '0.9rem',
                          },
                        }}
                      />
                    </Stack>
                  </Stack>
                </Stack>
                {/* Teacher Decision Controls */}
                <Stack direction="row" spacing={1.5} alignItems="center">
                  {manualDecision ? (
                    <>
                      <Chip
                        label={`Teacher Decision: ${manualDecision}`}
                        color={(() => {
                          const md = (manualDecision || '').toLowerCase();
                          if (md === 'accept') return 'success';
                          if (md === 'reject') return 'error';
                          if (md === 'middle') return 'warning';
                          return 'default';
                        })()}
                        size="small"
                      />
                      <Tooltip title="Clear teacher decision">
                        <Button color="secondary" size="small" onClick={() => setConfirmClearOpen(true)}>Undo</Button>
                      </Tooltip>
                    </>
                  ) : (
                    <ButtonGroup variant="contained" size="medium">
                      <Tooltip title="Mark Accept"><Button color="success" onClick={() => setManualDecision('ACCEPT')}>ACCEPT</Button></Tooltip>
                      <Tooltip title="Mark Middle"><Button color="warning" onClick={() => setManualDecision('MIDDLE')}>MIDDLE</Button></Tooltip>
                      <Tooltip title="Mark Reject"><Button color="error" onClick={() => setManualDecision('REJECT')}>REJECT</Button></Tooltip>
                    </ButtonGroup>
                  )}
                </Stack>
              </Stack>

            {/* Highlights or Metrics */}
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              {isTerminal ? (
                <Box>
                  <Card 
                    variant="outlined" 
                    sx={{ 
                      borderRadius: 2,
                      background: alpha(theme.palette.background.paper, 0.6),
                      backdropFilter: 'blur(5px)',
                      width: '100%'
                    }}
                  >
                    <CardContent sx={{ p: 1.5 }}>
                      <Stack direction="row" alignItems="center" spacing={1.5} sx={{ mb: 1.5 }}>
                        <Star color="primary" />
                        <Typography variant="subtitle1" fontWeight={600} color="text.primary">
                          Performance Highlights
                        </Typography>
                      </Stack>
                      <Stack direction="row" spacing={1} flexWrap="wrap">
                        {top && (
                          <Chip 
                            icon={<TrendingUp />}
                            color="success" 
                            variant="filled" 
                            size="small" 
                            label={`Top Strength: ${mapAgentName(top.agent)}`}
                            sx={{ fontWeight: 600 }}
                          />
                        )}
                        {bottom && (
                          <Chip 
                            icon={<TrendingDown />}
                            color="warning" 
                            variant="filled" 
                            size="small" 
                            label={`Area of Concern: ${mapAgentName(bottom.agent)}`}
                            sx={{ fontWeight: 600 }}
                          />
                        )}
                        {!top && !bottom && (
                          <Typography variant="body1" color="text.secondary">
                            No performance highlights available.
                          </Typography>
                        )}
                      </Stack>
                    </CardContent>
                  </Card>
                </Box>
              ) : (
                <>
                  <Box>
                    <Card 
                      variant="outlined"
                      sx={{ 
                        textAlign: 'center',
                        borderRadius: 2,
                        background: alpha(theme.palette.primary.main, 0.05),
                        border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`,
                        width: '100%'
                      }}
                    >
                      <CardContent sx={{ p: 1.5 }}>
                        <Typography variant="overline" color="primary" fontWeight={600} gutterBottom>
                          Weighted Score
                        </Typography>
                        <Typography variant="h5" fontWeight={700} color="primary">
                          {weighted !== null ? weighted.toFixed(1) : "N/A"}
                        </Typography>
                      </CardContent>
                    </Card>
                  </Box>
                  <Box>
                    <Card 
                      variant="outlined"
                      sx={{ 
                        textAlign: 'center',
                        borderRadius: 2,
                        background: alpha(theme.palette.secondary.main, 0.05),
                        border: `1px solid ${alpha(theme.palette.secondary.main, 0.2)}`,
                        width: '100%'
                      }}
                    >
                      <CardContent sx={{ p: 1.5 }}>
                        <Typography variant="overline" color="secondary" fontWeight={600} gutterBottom>
                          Final Rank
                        </Typography>
                        <Typography variant="h5" fontWeight={700} color="secondary">
                          {rank !== null ? `#${rank}` : "N/A"}
                        </Typography>
                      </CardContent>
                    </Card>
                  </Box>
                  <Box>
                    <Card 
                      variant="outlined"
                      sx={{ 
                        textAlign: 'center',
                        borderRadius: 2,
                        background: alpha(theme.palette.info.main, 0.05),
                        border: `1px solid ${alpha(theme.palette.info.main, 0.2)}`,
                        width: '100%'
                      }}
                    >
                      <CardContent sx={{ p: 1.5 }}>
                        <Typography variant="overline" color="info.main" fontWeight={600} gutterBottom>
                          Notes
                        </Typography>
                        <Typography variant="body1" color="text.primary" sx={{ minHeight: 24 }}>
                          {notes || "No adjustments"}
                        </Typography>
                      </CardContent>
                    </Card>
                  </Box>
                </>
              )}
            </Box>

            {/* Decision Reasons */}
            {reasons && reasons.length > 0 && (
              <Card 
                variant="outlined"
                sx={{ 
                  borderRadius: 2,
                  background: 'transparent',
                  border: 'none',
                  width: '100%'
                }}
              >
                <CardContent sx={{ p: 0 }}>
                  <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
                    <Gavel color="warning" />
                    <Typography variant="subtitle1" fontWeight={600} color="text.primary">
                      Decision Reasons
                    </Typography>
                  </Stack>
                  <Stack direction="row" spacing={0.75} flexWrap="wrap">
                    {reasons.map((r, i) => (
                      <Chip 
                        key={i} 
                        label={r} 
                        size="small" 
                        variant="outlined"
                        color="warning"
                        sx={{ fontWeight: 500 }}
                      />
                    ))}
                  </Stack>
                </CardContent>
              </Card>
            )}
          </Stack>
        </CardContent>
      </Card>
  </Box>

  {/* Evaluations Section */}
  <Box mt={1}>
      <Box>
        <Stack direction="row" alignItems="center" spacing={2} sx={{ mb: 3 }}>
          <Analytics color="primary" fontSize="large" />
          <Typography variant="h5" fontWeight={700} color="text.primary">
            Detailed Evaluations
          </Typography>
        </Stack>
        {/* Masonry-style two column layout: fills vertical gaps by using CSS columns */}
        <Box
          sx={{
            columnCount: { xs: 1, sm: 2 },
            columnGap: { xs: 2, sm: 3 },
            width: '100%',
            '& .masonry-item': {
              breakInside: 'avoid',
              WebkitColumnBreakInside: 'avoid',
              pageBreakInside: 'avoid',
              mb: 3,
              display: 'inline-block',
              width: '100%',
            }
          }}
        >
          {evals.map((ev, idx) => (
            <Box className="masonry-item" key={`${ev.agent}-${idx}`}>
              <EvaluationCard item={ev} />
            </Box>
          ))}
          {evals.length === 0 && (
            <Box className="masonry-item">
              <Card 
                variant="outlined"
                sx={{ 
                  textAlign: 'center',
                  py: 6,
                  borderRadius: 2,
                  background: alpha(theme.palette.grey[500], 0.05),
                  width: '100%'
                }}
              >
                <CardContent>
                  <Analytics sx={{ fontSize: 64, color: 'text.disabled', mb: 2 }} />
                  <Typography variant="h6" color="text.secondary" gutterBottom>
                    No Evaluations Available
                  </Typography>
                  <Typography variant="body2" color="text.disabled">
                    This applicant hasn&apos;t been evaluated yet.
                  </Typography>
                </CardContent>
              </Card>
            </Box>
          )}
        </Box>
      </Box>
      </Box>
  </Box>
    </Fade>
    <Dialog open={confirmClearOpen} onClose={() => setConfirmClearOpen(false)}>
      <DialogTitle>Confirm Undo</DialogTitle>
      <DialogContent>
        <Typography variant="body2">Are you sure you want to clear teacher decision?</Typography>
      </DialogContent>
      <DialogActions>
        <Button onClick={() => setConfirmClearOpen(false)}>Cancel</Button>
        <Button color="error" variant="contained" onClick={async () => { await setManualDecision(null); setConfirmClearOpen(false); }}>Clear</Button>
      </DialogActions>
    </Dialog>
    </>
  );
}
