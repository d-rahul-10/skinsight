import { beforeEach, describe, expect, it } from 'vitest';
import {
  readSkinDiary, readSkinReminders, saveSkinDiary, saveSkinReminders,
  type SkinDiaryEntry, type SkinReminder,
} from './skinDiary';

describe('local skin diary and reminders', () => {
  beforeEach(() => localStorage.clear());

  it('round-trips diary entries and reminders independently', () => {
    const entry: SkinDiaryEntry = {
      id: 'diary-1', date: '2026-11-03', notes: 'Dryness after a shower', createdAt: '2026-11-03T08:00:00.000Z',
    };
    const reminder: SkinReminder = {
      id: 'reminder-1', title: 'Follow-up appointment', dueAt: '2026-11-04T09:00:00.000Z',
      completed: false, notified: false,
    };

    saveSkinDiary([entry]);
    saveSkinReminders([reminder]);

    expect(readSkinDiary()).toEqual([entry]);
    expect(readSkinReminders()).toEqual([reminder]);
  });

  it('reports malformed saved data instead of silently discarding it', () => {
    localStorage.setItem('skinsight.skin-diary.v1', '{');
    expect(() => readSkinDiary()).toThrow('Saved diary or reminder data is unreadable');
  });

  it('reports entries with an unexpected shape', () => {
    localStorage.setItem('skinsight.reminders.v1', JSON.stringify([{ title: 'Missing required fields' }]));
    expect(() => readSkinReminders()).toThrow('unexpected format');
  });
});
