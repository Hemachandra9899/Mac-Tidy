// Pure formatting helpers. Everything interpolated into HTML goes through esc().

const ENTITIES = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };

const SIZE_UNITS = [
  [1e12, 'TB', 2],
  [1e9, 'GB', 2],
  [1e6, 'MB', 1],
  [1e3, 'KB', 0],
];

export const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ENTITIES[c]);

export function formatSize(bytes) {
  const unit = SIZE_UNITS.find(([threshold]) => bytes >= threshold);
  return unit ? `${(bytes / unit[0]).toFixed(unit[2])} ${unit[1]}` : `${bytes} B`;
}

export const formatTime = (iso) => new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

export const formatDateTime = (epochSeconds) => new Date(epochSeconds * 1000).toLocaleString();

export const sortBySize = (rows) => [...rows].sort((a, b) => b.size - a.size);

export const sumSizes = (rows) => rows.reduce((total, row) => total + row.size, 0);
