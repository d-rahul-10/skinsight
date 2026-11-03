export interface SkinDiaryEntry {
  id: string;
  date: string;
  notes: string;
  createdAt: string;
}

export interface SkinReminder {
  id: string;
  title: string;
  dueAt: string;
  completed: boolean;
  notified: boolean;
}

const DIARY_STORAGE_KEY = 'skinsight.skin-diary.v1';
const REMINDER_STORAGE_KEY = 'skinsight.reminders.v1';

function readEntries<T>(key: string, isEntry: (value: unknown) => value is T): T[] {
  let serialized: string | null;
  try {
    serialized = window.localStorage.getItem(key);
  } catch {
    throw new Error('Local browser storage is unavailable. Check your browser privacy settings.');
  }
  if (serialized === null) return [];

  let values: unknown;
  try {
    values = JSON.parse(serialized);
  } catch {
    throw new Error('Saved diary or reminder data is unreadable. Clear this site’s browser storage to reset it.');
  }
  if (!Array.isArray(values) || !values.every(isEntry)) {
    throw new Error('Saved diary or reminder data has an unexpected format. Clear this site’s browser storage to reset it.');
  }
  return values;
}

function writeEntries<T>(key: string, entries: T[]): void {
  try {
    window.localStorage.setItem(key, JSON.stringify(entries));
  } catch {
    throw new Error('Could not save this entry in browser storage. Check available storage space and privacy settings.');
  }
}

function isDiaryEntry(value: unknown): value is SkinDiaryEntry {
  if (typeof value !== 'object' || value === null) return false;
  const entry = value as Record<string, unknown>;
  return typeof entry.id === 'string' && typeof entry.date === 'string'
    && typeof entry.notes === 'string' && typeof entry.createdAt === 'string';
}

function isReminder(value: unknown): value is SkinReminder {
  if (typeof value !== 'object' || value === null) return false;
  const reminder = value as Record<string, unknown>;
  return typeof reminder.id === 'string' && typeof reminder.title === 'string'
    && typeof reminder.dueAt === 'string' && typeof reminder.completed === 'boolean'
    && typeof reminder.notified === 'boolean';
}

export function readSkinDiary(): SkinDiaryEntry[] {
  return readEntries(DIARY_STORAGE_KEY, isDiaryEntry);
}

export function saveSkinDiary(entries: SkinDiaryEntry[]): void {
  writeEntries(DIARY_STORAGE_KEY, entries);
}

export function readSkinReminders(): SkinReminder[] {
  return readEntries(REMINDER_STORAGE_KEY, isReminder);
}

export function saveSkinReminders(reminders: SkinReminder[]): void {
  writeEntries(REMINDER_STORAGE_KEY, reminders);
}
