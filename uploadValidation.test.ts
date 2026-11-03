import { describe, expect, it, vi } from 'vitest';
import { validateImageFile } from './uploadValidation';

describe('validateImageFile', () => {
  it('accepts supported JPEG, PNG, and WEBP images', () => {
    expect(validateImageFile(new File(['pixels'], 'spot.jpg', { type: 'image/jpeg' }))).toBeNull();
    expect(validateImageFile(new File(['pixels'], 'spot.jpe', { type: 'image/jpeg' }))).toBeNull();
    expect(validateImageFile(new File(['pixels'], 'spot.png', { type: 'image/png' }))).toBeNull();
    expect(validateImageFile(new File(['pixels'], 'spot.webp', { type: 'image/webp' }))).toBeNull();
  });

  it('rejects unsupported file types', () => {
    expect(validateImageFile(new File(['text'], 'notes.txt', { type: 'text/plain' }))).toMatch(/JPG, JPEG, PNG, or WEBP/i);
  });

  it('rejects empty files and files above the size limit', () => {
    expect(validateImageFile(new File([], 'empty.jpg', { type: 'image/jpeg' }))).toMatch(/empty/i);
    const oversized = new File([new Uint8Array(8 * 1024 * 1024 + 1)], 'large.jpg', { type: 'image/jpeg' });
    expect(validateImageFile(oversized)).toMatch(/8 MB/i);
  });
});

describe('API errors', () => {
  it('surfaces a safe FastAPI upload validation message', async () => {
    vi.stubGlobal('XMLHttpRequest', class {
      upload = { onprogress: null as ((event: ProgressEvent) => void) | null };
      onerror: (() => void) | null = null;
      onabort: (() => void) | null = null;
      onload: (() => void) | null = null;
      status = 415;
      responseText = JSON.stringify({ detail: 'Unsupported image format.' });
      open() {}
      send() { this.onload?.(); }
    });
    const { analyzeImage } = await import('./client');
    await expect(analyzeImage(new File(['x'], 'x.gif'), {}, false, () => undefined)).rejects.toThrow('Unsupported image format.');
    vi.unstubAllGlobals();
  });
});
