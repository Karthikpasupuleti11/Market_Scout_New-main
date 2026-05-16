export function formatDateTime(dateInput) {
  if (!dateInput) return '—';
  
  let d = dateInput;
  // If date string doesn't have a timezone indicator (Z or +/-00:00), force UTC
  // so it correctly converts to the user's local timezone.
  if (typeof d === 'string' && !d.endsWith('Z') && !d.match(/[+-]\d{2}:?\d{2}$/)) {
    d += 'Z';
  }
  
  const date = d instanceof Date ? d : new Date(d);
  if (isNaN(date.getTime())) return 'Invalid Date';

  return date.toLocaleString([], {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}
