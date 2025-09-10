"use client";

import { 
  Box, 
  Paper, 
  Typography, 
  Avatar, 
  Stack,
  Chip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Card,
  CardContent
} from '@mui/material';
import { ExpandMore, SmartToy, Person, Build } from '@mui/icons-material';
import { formatLocalTime } from '../lib/date';

interface LogMessage {
  id: number;
  agent: string;
  phase: 'request' | 'response' | 'tool';
  message: string;
  created_at: string;
  applicant_id?: number;
}

interface ConversationProps {
  logs: LogMessage[];
  applicants: Array<{ id: number; folder_name: string }>;
}

// Convert technical agent names to user-friendly display names
function getAgentDisplayName(agentName: string): string {
  const agentNameMap: Record<string, string> = {
    'english': 'English Proficiency',
    'degree': 'Degree Qualification',
    'experience': 'Experience', 
    'ps_rl': 'Personal Statement & References',
    'academic': 'Academic Publications',
    'compare': 'Comparison Analysis',
    'classifier': 'Classification',
    'detector': 'Detection Analysis'
  };
  
  return agentNameMap[agentName] || agentName;
}

function MessageBubble({ message, isAgent = false }: { message: LogMessage; isAgent?: boolean }) {
  const getPhaseColor = (phase: string) => {
    switch (phase) {
      case 'request': return '#e3f2fd';
      case 'response': return '#f3e5f5';
      case 'tool': return '#fff3e0';
      default: return '#f5f5f5';
    }
  };

  const getPhaseIcon = (phase: string) => {
    switch (phase) {
      case 'request': return <Person fontSize="small" />;
      case 'response': return <SmartToy fontSize="small" />;
      case 'tool': return <Build fontSize="small" />;
      default: return <SmartToy fontSize="small" />;
    }
  };

  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: isAgent ? 'flex-start' : 'flex-end',
        mb: 2,
      }}
    >
      <Paper
        elevation={1}
        sx={{
          maxWidth: '80%',
          p: 2,
          backgroundColor: getPhaseColor(message.phase),
          borderRadius: 2,
        }}
      >
        <Stack direction="row" spacing={1} alignItems="center" mb={1}>
          <Avatar sx={{ width: 24, height: 24, bgcolor: 'transparent' }}>
            {getPhaseIcon(message.phase)}
          </Avatar>
          <Typography variant="caption" color="text.secondary">
            {message.agent}
          </Typography>
          <Chip
            label={message.phase}
            size="small"
            variant="outlined"
            sx={{ height: 20, fontSize: '0.7rem' }}
          />
          <Typography variant="caption" color="text.secondary">
            {formatLocalTime(message.created_at)}
          </Typography>
        </Stack>
        <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
          {message.message}
        </Typography>
      </Paper>
    </Box>
  );
}

function ApplicantConversation({ 
  applicant, 
  messages 
}: { 
  applicant: { id: number; folder_name: string };
  messages: LogMessage[];
}) {
  const agentGroups = messages.reduce((acc, msg) => {
    if (!acc[msg.agent]) {
      acc[msg.agent] = [];
    }
    acc[msg.agent].push(msg);
    return acc;
  }, {} as Record<string, LogMessage[]>);

  return (
    <Card sx={{ mb: 3 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          <Person sx={{ mr: 1, verticalAlign: 'middle' }} />
          {applicant.folder_name}
        </Typography>
        
        {Object.entries(agentGroups).map(([agentName, agentMessages]) => (
          <Accordion key={agentName} sx={{ mb: 2 }}>
            <AccordionSummary expandIcon={<ExpandMore />}>
              <Stack direction="row" alignItems="center" spacing={1}>
                <SmartToy />
                <Typography variant="subtitle1">{getAgentDisplayName(agentName)}</Typography>
                <Chip 
                  label={`${agentMessages.length} messages`} 
                  size="small" 
                  variant="outlined" 
                />
              </Stack>
            </AccordionSummary>
            <AccordionDetails>
              <Box sx={{ maxHeight: 400, overflowY: 'auto' }}>
                {agentMessages
                  .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
                  .map((msg) => (
                    <MessageBubble 
                      key={msg.id} 
                      message={msg} 
                      isAgent={msg.phase === 'response'} 
                    />
                  ))}
              </Box>
            </AccordionDetails>
          </Accordion>
        ))}
      </CardContent>
    </Card>
  );
}

export default function ConversationView({ logs, applicants }: ConversationProps) {
  // Group logs by applicant
  const applicantLogs = logs.reduce((acc, log) => {
    const applicantId = log.applicant_id || 0;
    if (!acc[applicantId]) {
      acc[applicantId] = [];
    }
    acc[applicantId].push(log);
    return acc;
  }, {} as Record<number, LogMessage[]>);

  // Handle global/gating logs (applicant_id is null)
  const globalLogs = applicantLogs[0] || [];
  
  return (
    <Box>
      {/* Global/Gating Logs */}
      {globalLogs.length > 0 && (
        <Card sx={{ mb: 3, backgroundColor: '#fafafa' }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              <SmartToy sx={{ mr: 1, verticalAlign: 'middle' }} />
              System & Gating Agents
            </Typography>
            <Box sx={{ maxHeight: 400, overflowY: 'auto' }}>
              {globalLogs
                .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
                .map((msg) => (
                  <MessageBubble 
                    key={msg.id} 
                    message={msg} 
                    isAgent={msg.phase === 'response'} 
                  />
                ))}
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Applicant-specific conversations */}
      {applicants.map((applicant) => {
        const messages = applicantLogs[applicant.id] || [];
        if (messages.length === 0) return null;
        
        return (
          <ApplicantConversation
            key={applicant.id}
            applicant={applicant}
            messages={messages}
          />
        );
      })}
    </Box>
  );
}