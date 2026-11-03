import type { AnalysisResponse, HealthResponse, HistoryItem, OptionalMetadata } from './types/api';

function errorMessage(payload: unknown, fallback: string): string {
  if (payload && typeof payload === 'object' && 'detail' in payload) {
    const detail = (payload as { detail?: unknown }).detail;
    if (typeof detail === 'string') return detail;
  }
  return fallback;
}

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch('/api/health');
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) throw new Error(errorMessage(data, 'Could not connect to the analysis service.'));
  return data as HealthResponse;
}

export function analyzeImage(
  file: File,
  metadata: OptionalMetadata,
  retainImage: boolean,
  onProgress: (percent: number) => void,
): Promise<AnalysisResponse> {
  return new Promise((resolve, reject) => {
    const body = new FormData();
    body.append('file', file);
    if (metadata.age) body.append('age', metadata.age);
    if (metadata.bodyLocation) body.append('body_location', metadata.bodyLocation);
    if (metadata.duration) body.append('symptom_duration', metadata.duration);
    if (metadata.symptoms) body.append('symptoms', metadata.symptoms);
    if (retainImage) body.append('retain_image', 'true');

    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/analyze');
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100));
    };
    xhr.onerror = () => reject(new Error('Network error while uploading. Check that the API server is running.'));
    xhr.onabort = () => reject(new Error('Upload was cancelled.'));
    xhr.onload = () => {
      let parsed: unknown = null;
      try { parsed = JSON.parse(xhr.responseText); } catch { /* handled below */ }
      if (xhr.status < 200 || xhr.status >= 300) {
        reject(new Error(errorMessage(parsed, `Analysis request failed (HTTP ${xhr.status}).`)));
        return;
      }
      if (!parsed || typeof parsed !== 'object' || !('analysis_id' in parsed)) {
        reject(new Error('The analysis service returned an unexpected response.'));
        return;
      }
      resolve(parsed as AnalysisResponse);
    };
    xhr.send(body);
  });
}

export async function getHistory(): Promise<HistoryItem[]> {
  const response = await fetch('/api/history');
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) throw new Error(errorMessage(data, 'Could not load analysis history.'));
  if (!Array.isArray(data)) throw new Error('The history response was invalid.');
  return data as HistoryItem[];
}

export async function deleteHistory(id?: number): Promise<void> {
  const response = await fetch(id === undefined ? '/api/history' : `/api/history/${id}`, { method: 'DELETE' });
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) throw new Error(errorMessage(data, 'Could not delete history.'));
}
