"use client";
import { Card, CardContent, Stack, Typography, Box, Chip, LinearProgress } from '@mui/material';
import { useTheme, alpha } from '@mui/material/styles';

export interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  color? : 'default' | 'primary' | 'secondary' | 'success' | 'warning' | 'error' | 'info';
  chipLabel?: string;
  percent?: number;
}

export function StatCard({ title, value, subtitle, color = 'default', chipLabel, percent }: StatCardProps) {
  const theme = useTheme();
  const mainColor = color === 'default' 
    ? theme.palette.text.primary 
    : (theme.palette as any)[color]?.main || theme.palette.primary.main;
  const trackColor = alpha(mainColor, 0.12);
  return (
    <Card variant="outlined" sx={{ flex: '1 1 220px' }}>
      <CardContent>
        <Stack spacing={1}>
          <Stack direction="row" spacing={1} alignItems="center" justifyContent="space-between">
            <Typography variant="subtitle2" color="text.secondary">{title}</Typography>
            {chipLabel && <Chip size="small" color={color === 'default' ? 'default' : color} label={chipLabel} />}
          </Stack>
          <Box>
            <Typography variant="h4" color={color === 'default' ? undefined : `${color}.main`}>{value}</Typography>
          </Box>
          {subtitle && (
            <Typography variant="caption" color="text.secondary">{subtitle}</Typography>
          )}
          {typeof percent === 'number' && (
            <LinearProgress 
              variant="determinate" 
              value={Math.max(0, Math.min(100, percent))} 
              sx={{ height: 6, borderRadius: 3, bgcolor: trackColor, '& .MuiLinearProgress-bar': { bgcolor: mainColor, borderRadius: 3 } }}
            />
          )}
        </Stack>
      </CardContent>
    </Card>
  );
}

export default StatCard;


