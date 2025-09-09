export function parseServerDate(value: string | Date | undefined | null): Date | null {
  if (!value) return null;
  const raw = typeof value === 'string' ? value : (value as Date).toISOString();
  // If string has no timezone suffix, assume UTC (append Z)
  const hasTZ = /[zZ]|[+-]\d{2}:?\d{2}$/.test(raw);
  const iso = hasTZ ? raw : `${raw}Z`;
  const d = new Date(iso);
  return isNaN(d.getTime()) ? null : d;
}

export function formatLocalDateTime(value: string | Date | undefined | null): string {
  const d = parseServerDate(value);
  if (!d) return '';
  return new Intl.DateTimeFormat(undefined, {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit'
  }).format(d);
}

export function formatLocalTime(value: string | Date | undefined | null): string {
  const d = parseServerDate(value);
  if (!d) return '';
  return new Intl.DateTimeFormat(undefined, {
    hour: '2-digit', minute: '2-digit', second: '2-digit'
  }).format(d);
}


