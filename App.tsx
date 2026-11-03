import { useEffect, useRef, useState } from 'react';
import {
  Activity, ArrowDown, ArrowRight, Bell, BookOpen, CalendarDays, Check, CheckCircle2, ChevronDown,
  CircleAlert, Clock3, ExternalLink, FileImage, HeartPulse, Info, Leaf, LoaderCircle,
  LockKeyhole, MapPin, Microscope, RotateCcw, ShieldCheck, Sparkles, Trash2, Upload, X,
} from 'lucide-react';
import { analyzeImage, deleteHistory, getHealth, getHistory } from './client';
import { readSkinDiary, readSkinReminders, saveSkinDiary, saveSkinReminders } from './skinDiary';
import type { SkinDiaryEntry, SkinReminder } from './skinDiary';
import { validateImageFile } from './uploadValidation';
import type { AnalysisResponse, HealthResponse, HistoryItem, OptionalMetadata } from './types/api';

const lowConfidenceCopy = 'The model is uncertain about this image. Please upload a clearer image or consult a qualified dermatologist.';
const emptyMetadata: OptionalMetadata = {};
const HYDERABAD_CARE_OPTIONS = ['Apollo Hospitals', 'Yashoda Hospitals', 'CARE Hospitals', 'KIMS Hospitals'] as const;
const localDateInputValue = () => {
  const date = new Date();
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
};

function Logo() {
  return <a href="#top" className="brand-mark" aria-label="SkinSight home"><span className="brand-icon"><Activity size={21} strokeWidth={2.5} /></span><span>skin<span className="brand-name-light">sight</span><sup>AI</sup></span></a>;
}

function ProbabilityList({ items }: { items: AnalysisResponse['probabilities'] }) {
  if (!items.length) return null;
  return <div className="probability-list" aria-label="Class probability chart">
    {items.slice(0, 5).map((item) => <div className="probability-row" key={item.category}>
      <div className="probability-label"><span>{item.category}</span><span>{(item.probability * 100).toFixed(1)}%</span></div>
      <div className="probability-track"><div className="probability-fill" style={{ width: `${Math.max(2, item.probability * 100)}%` }} /></div>
    </div>)}
  </div>;
}

function QualityBadge({ status }: { status: string }) {
  const label = status === 'good' ? 'Image looks clear' : status === 'warning' ? 'Image quality note' : 'Image needs attention';
  return <span className={`quality-badge quality-${status}`}><span className="quality-dot" />{label}</span>;
}

export default function App() {
  const inputRef = useRef<HTMLInputElement>(null);
  const shownReminderIdsRef = useRef(new Set<string>());
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [error, setError] = useState('');
  const [progress, setProgress] = useState(0);
  const [busy, setBusy] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [metadata, setMetadata] = useState<OptionalMetadata>(emptyMetadata);
  const [retainImage, setRetainImage] = useState(false);
  const [historyError, setHistoryError] = useState('');
  const [diary, setDiary] = useState<SkinDiaryEntry[]>([]);
  const [reminders, setReminders] = useState<SkinReminder[]>([]);
  const [diaryDate, setDiaryDate] = useState(localDateInputValue);
  const [diaryNotes, setDiaryNotes] = useState('');
  const [reminderTitle, setReminderTitle] = useState('');
  const [reminderDate, setReminderDate] = useState('');
  const [journalError, setJournalError] = useState('');
  const [reminderNotice, setReminderNotice] = useState('');
  const [notificationPermissionGranted, setNotificationPermissionGranted] = useState(false);
  const [, setReminderClock] = useState(Date.now());

  useEffect(() => {
    void getHealth().then(setHealth).catch(() => setHealth(null));
    void refreshHistory();
    try {
      setDiary(readSkinDiary());
      setReminders(readSkinReminders());
    } catch (cause) {
      setJournalError(cause instanceof Error ? cause.message : 'Could not load diary and reminder data.');
    }
  }, []);

  useEffect(() => {
    const notifyDueReminders = () => {
      setReminderClock(Date.now());
      if (!('Notification' in window) || (!notificationPermissionGranted && Notification.permission !== 'granted')) return;
      const dueReminders = reminders.filter((reminder) => !reminder.completed && !reminder.notified
        && !shownReminderIdsRef.current.has(reminder.id)
        && new Date(reminder.dueAt).getTime() <= Date.now());
      if (!dueReminders.length) return;
      try {
        for (const reminder of dueReminders) {
          shownReminderIdsRef.current.add(reminder.id);
          new Notification('SkinSight reminder', { body: reminder.title });
        }
        const dueIds = new Set(dueReminders.map((reminder) => reminder.id));
        const updated = reminders.map((reminder) => dueIds.has(reminder.id) ? { ...reminder, notified: true } : reminder);
        saveSkinReminders(updated);
        setReminders(updated);
      } catch (cause) {
        dueReminders.forEach((reminder) => shownReminderIdsRef.current.delete(reminder.id));
        setJournalError(cause instanceof Error ? cause.message : 'Could not show a browser reminder.');
      }
    };
    notifyDueReminders();
    const intervalId = window.setInterval(notifyDueReminders, 30_000);
    return () => window.clearInterval(intervalId);
  }, [reminders, notificationPermissionGranted]);

  function addDiaryEntry(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const notes = diaryNotes.trim();
    if (!notes) return;
    const next = [{ id: crypto.randomUUID(), date: diaryDate, notes, createdAt: new Date().toISOString() }, ...diary];
    try {
      saveSkinDiary(next);
      setDiary(next);
      setDiaryNotes('');
      setJournalError('');
    } catch (cause) {
      setJournalError(cause instanceof Error ? cause.message : 'Could not save this diary entry.');
    }
  }

  function addReminder(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const title = reminderTitle.trim();
    const dueAt = new Date(reminderDate);
    if (!title || !reminderDate || Number.isNaN(dueAt.getTime())) return;
    const next = [{ id: crypto.randomUUID(), title, dueAt: dueAt.toISOString(), completed: false, notified: false }, ...reminders];
    try {
      saveSkinReminders(next);
      setReminders(next);
      setReminderTitle('');
      setReminderDate('');
      setJournalError('');
    } catch (cause) {
      setJournalError(cause instanceof Error ? cause.message : 'Could not save this reminder.');
    }
  }

  function updateReminder(id: string, patch: Partial<SkinReminder>) {
    const next = reminders.map((reminder) => reminder.id === id ? { ...reminder, ...patch } : reminder);
    try {
      saveSkinReminders(next);
      setReminders(next);
      setJournalError('');
    } catch (cause) {
      setJournalError(cause instanceof Error ? cause.message : 'Could not update this reminder.');
    }
  }

  function removeReminder(id: string) {
    const next = reminders.filter((reminder) => reminder.id !== id);
    try {
      saveSkinReminders(next);
      setReminders(next);
      shownReminderIdsRef.current.delete(id);
      setJournalError('');
    } catch (cause) {
      setJournalError(cause instanceof Error ? cause.message : 'Could not delete this reminder.');
    }
  }

  async function enableBrowserReminders() {
    if (!('Notification' in window)) {
      setReminderNotice('Browser notifications are not supported here. Reminders still appear in this page.');
      return;
    }
    setReminderNotice('Waiting for browser notification permission…');
    try {
      const permission = await Notification.requestPermission();
      setNotificationPermissionGranted(permission === 'granted');
      setReminderNotice(permission === 'granted'
        ? 'Browser alerts enabled while this app is open.'
        : 'Notifications were not enabled. Due reminders will still appear in this page.');
    } catch {
      setReminderNotice('Could not enable browser notifications. Due reminders will still appear in this page.');
    }
  }

  async function refreshHistory() {
    try { setHistory(await getHistory()); setHistoryError(''); }
    catch (cause) { setHistoryError(cause instanceof Error ? cause.message : 'History is unavailable.'); }
  }

  function selectFile(nextFile: File | undefined) {
    if (!nextFile) return;
    const issue = validateImageFile(nextFile);
    if (issue) { setError(issue); return; }
    setError('');
    setResult(null);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setFile(nextFile);
    setPreviewUrl(URL.createObjectURL(nextFile));
  }

  function clearSelection() {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);
    setFile(null);
    setResult(null);
    setError('');
    if (inputRef.current) inputRef.current.value = '';
  }

  async function submitAnalysis() {
    if (!file) { setError('Choose an image before starting the analysis.'); return; }
    setBusy(true); setError(''); setProgress(0); setResult(null);
    try {
      const response = await analyzeImage(file, metadata, retainImage && Boolean(health?.image_retention_allowed), setProgress);
      setResult(response);
      await refreshHistory();
      requestAnimationFrame(() => document.querySelector('#analysis-result')?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Analysis could not be completed. Please try again.');
    } finally { setBusy(false); }
  }

  async function removeHistory(id?: number) {
    try { await deleteHistory(id); await refreshHistory(); }
    catch (cause) { setHistoryError(cause instanceof Error ? cause.message : 'Could not delete history.'); }
  }

  const uncertain = result?.uncertainty_status === 'low_confidence';
  const unavailable = result?.uncertainty_status === 'model_unavailable';
  const unsuitable = result?.uncertainty_status === 'image_unsuitable';
  const demoCheckpoint = health?.model_version === 'smoke-1000-images';

  return <div id="top" className="app-shell">
    <header className="site-header">
      <div className="header-inner"><Logo /><nav aria-label="Main navigation" className="main-nav"><a href="#how-it-works">How it works</a><a href="#self-care">Daily care</a><a href="#journal-title">Skin diary</a><a href="#responsible-use">Responsible use</a><a href="#privacy">Privacy</a></nav>
        <a className="header-cta" href="#analyze">Try the prototype <ArrowRight size={15} /></a>
      </div>
    </header>

    <main>
      <section className="hero-section">
        <div className="hero-wash" aria-hidden="true" />
        <div className="hero-inner">
          <div className="hero-copy">
            <div className="eyebrow"><span className="eyebrow-dot" />ACADEMIC SCREENING PROTOTYPE</div>
            <h1>A closer look.<br /><span>With clarity.</span></h1>
            <p className="hero-lede">Explore an image-screening prototype built to make its process transparent—and its limitations clear.</p>
            <div className="hero-actions"><a href="#analyze" className="button-primary">Analyze a skin image <ArrowRight size={17} /></a><a href="#how-it-works" className="button-quiet">See how it works <ArrowDown size={16} /></a></div>
            <div className="hero-assurance"><ShieldCheck size={16} /><span>Your image isn’t saved by default. No diagnosis is made.</span></div>
          </div>
          <div className="hero-visual" aria-label="Illustration of an image being reviewed by an academic analysis tool">
            <div className="orbit orbit-one" /><div className="orbit orbit-two" />
            <div className="visual-card visual-card-main"><div className="scan-image"><div className="scan-glow" /><div className="scan-texture" /><span className="scan-corner corner-tl" /><span className="scan-corner corner-tr" /><span className="scan-corner corner-bl" /><span className="scan-corner corner-br" /><span className="scan-label"><span /> SAMPLE IMAGE · ILLUSTRATION</span></div><div className="visual-caption"><div><span className="caption-kicker">IMAGE REVIEW</span><strong>One step at a time</strong></div><span className="caption-icon"><Microscope size={19} /></span></div></div>
            <div className="float-chip chip-top"><span className="chip-pulse" /><span>Quality check</span><Check size={14} /></div><div className="float-chip chip-bottom"><span className="chip-icon"><LockKeyhole size={15} /></span><span>Private by default</span></div>
          </div>
        </div>
        <div className="hero-bottom"><span>BUILT FOR LEARNING, NOT DIAGNOSIS</span><span>Image quality · Model transparency · Educational context</span></div>
      </section>

      <section className="trust-strip" aria-label="Prototype safeguards"><div><span className="trust-icon"><LockKeyhole size={17} /></span><span><strong>Private by default</strong><small>Retention requires opt-in</small></span></div><div><span className="trust-icon"><Microscope size={17} /></span><span><strong>Research-led design</strong><small>Transparent process</small></span></div><div><span className="trust-icon"><HeartPulse size={17} /></span><span><strong>Education first</strong><small>Not medical advice</small></span></div><p>For academic exploration only</p></section>

      <section id="how-it-works" className="section how-section"><div className="section-heading"><div><span className="section-kicker">A THOUGHTFUL PROCESS</span><h2>Understand the steps.<br /><em>Keep the context.</em></h2></div><p>Each part of the prototype is designed to show what it can—and cannot—tell you.</p></div>
        <div className="steps-row"><article className="step-card"><span className="step-num">01</span><span className="step-icon step-violet"><Upload size={20} /></span><h3>Share an image</h3><p>Choose a clear JPG, PNG, or WEBP image. A quality check looks for common capture issues before processing.</p></article><article className="step-card"><span className="step-num">02</span><span className="step-icon step-blue"><Activity size={20} /></span><h3>Review the output</h3><p>If trained weights are installed, the prototype shows a visual class, uncertainty context, and a model-attention view.</p></article><article className="step-card"><span className="step-num">03</span><span className="step-icon step-lilac"><Info size={20} /></span><h3>Keep perspective</h3><p>Explore general educational information, understand the limits, and speak with a professional about concerns.</p></article></div>
      </section>

      <section id="analyze" className="analysis-section"><div className="analysis-shell"><div className="analysis-heading"><div><span className="section-kicker">IMAGE EXPLORER</span><h2>Start with a clear image.</h2><p>A small, private academic prototype—not a medical assessment.</p></div><span className="local-badge"><span /> SESSION ONLY</span></div>
        <div className="analysis-card"><div className="upload-column"><div className="upload-title"><span className="upload-step">01</span><div><h3>Choose a skin image</h3><p>JPG, PNG or WEBP · Up to 8 MB</p></div></div>
          {!file ? <label className={`drop-zone ${dragActive ? 'drop-zone-active' : ''}`} onDragOver={(event) => { event.preventDefault(); setDragActive(true); }} onDragLeave={() => setDragActive(false)} onDrop={(event) => { event.preventDefault(); setDragActive(false); selectFile(event.dataTransfer.files[0]); }}>
            <input ref={inputRef} className="sr-only" type="file" accept="image/jpeg,image/png,image/webp,.jpg,.jpeg,.jpe,.png,.webp" onChange={(event) => selectFile(event.currentTarget.files?.[0])} aria-label="Choose or drop a skin image" />
            <span className="upload-symbol"><Upload size={21} /></span><strong>Drop your image here</strong><span className="drop-small">or <span className="browse-link">browse files</span></span><span className="drop-formats"><FileImage size={14} /> JPEG · PNG · WEBP</span>
          </label> : <div className="preview-box"><img src={previewUrl ?? ''} alt="Selected skin image preview" /><button type="button" className="remove-image" onClick={clearSelection} aria-label="Remove selected image"><X size={16} /></button><div className="preview-file"><FileImage size={14} /><span>{file.name}</span><Check size={15} /></div></div>}
          <button type="button" className="optional-toggle" aria-expanded={showDetails} onClick={() => setShowDetails((value) => !value)}><span>Optional context</span><span>Not saved to history <ChevronDown size={15} className={showDetails ? 'rotate-icon' : ''} /></span></button>
          {showDetails && <div className="metadata-grid"><label>Age (optional)<input type="number" min="1" max="120" placeholder="e.g. 35" value={metadata.age ?? ''} onChange={(event) => setMetadata((v) => ({ ...v, age: event.target.value }))} /></label><label>Body location<input type="text" maxLength={80} placeholder="e.g. forearm" value={metadata.bodyLocation ?? ''} onChange={(event) => setMetadata((v) => ({ ...v, bodyLocation: event.target.value }))} /></label><label>How long have you noticed it?<input type="text" maxLength={80} placeholder="Optional" value={metadata.duration ?? ''} onChange={(event) => setMetadata((v) => ({ ...v, duration: event.target.value }))} /></label><label>Anything else to note?<input type="text" maxLength={160} placeholder="Optional" value={metadata.symptoms ?? ''} onChange={(event) => setMetadata((v) => ({ ...v, symptoms: event.target.value }))} /></label><p className="metadata-note">Optional context is sent with this request and discarded; it is not stored in analysis history.</p></div>}
          {error && <div className="inline-error" role="alert"><CircleAlert size={16} />{error}</div>}
          {busy && <div className="upload-progress" aria-live="polite"><div className="progress-copy"><span><LoaderCircle size={15} className="spin" /> Preparing your image</span><span>{progress}%</span></div><div className="progress-track"><span style={{ width: `${Math.max(progress, 5)}%` }} /></div><small>Image checks and model availability may take a moment.</small></div>}
          <button type="button" className="button-primary analyze-button" onClick={() => void submitAnalysis()} disabled={!file || busy}>{busy ? <><LoaderCircle className="spin" size={17} /> Checking image…</> : <>Begin image review <ArrowRight size={17} /></>}</button>
          {health?.image_retention_allowed && <label className="retention-option"><input type="checkbox" checked={retainImage} onChange={(event) => setRetainImage(event.target.checked)} /><span><strong>Save this image with local history</strong><small>Optional, off by default. It will be deleted when its history entry is deleted.</small></span></label>}
          <p className="upload-privacy"><LockKeyhole size={13} /> {retainImage && health?.image_retention_allowed ? 'This image will be saved locally only because you opted in.' : 'Images are processed in memory and not retained by default.'}</p>
        </div>
        <div className="analysis-aside"><div className="aside-icon"><Sparkles size={19} /></div><span className="aside-label">BEFORE YOU CONTINUE</span><h3>Designed to be honest about uncertainty.</h3><p>Image quality checks are simple heuristics, not a way to detect a lesion. Results depend on a real trained model being available.</p><div className={`model-status-card ${health?.model_available ? 'model-ready' : ''}`}><span className="status-indicator" /><div><strong>{health?.model_available ? 'Trained model available' : health ? 'Model weights not installed' : 'Checking model status'}</strong><small>{health?.model_message ?? 'Connecting to the local API service…'}</small></div></div><div className="aside-divider" /><p className="aside-safety"><Info size={15} /> If a spot is changing, bleeding, painful, persistent, or concerning, seek professional assessment.</p></div></div>
      </div></section>

      {result && <section id="analysis-result" className="result-section"><div className="result-heading"><div><span className="section-kicker">IMAGE REVIEW · #{result.analysis_id}</span><h2>Your review, with context.</h2></div><button className="button-outline" onClick={clearSelection}><RotateCcw size={15} /> Analyze another</button></div>
        <div className="result-grid"><article className="result-card image-result-card"><div className="card-title"><span>IMAGE QUALITY</span><QualityBadge status={result.quality.status} /></div><img src={previewUrl ?? ''} alt="Uploaded skin image" className="result-image" /><ul className="quality-notes">{result.quality.warnings.map((warning) => <li key={warning}><Info size={14} />{warning}</li>)}{result.quality.reasons.map((reason) => <li key={reason}><CircleAlert size={14} />{reason}</li>)}{!result.quality.warnings.length && !result.quality.reasons.length && <li><Check size={14} />No common capture issues detected by these basic heuristics.</li>}</ul><p className="micro-disclaimer">Image quality checks do not determine whether an image contains a lesion.</p></article>
          <article className="result-card prediction-card"><div className="card-title"><span>MODEL REVIEW</span><span className="model-tag">{demoCheckpoint ? 'DEMO ONLY · LOW ACCURACY' : result.model_status === 'available' ? 'EXPERIMENTAL MODEL' : 'NO MODEL LOADED'}</span></div>
            {demoCheckpoint && <div className="demo-model-warning" role="note"><CircleAlert size={17} /><p><strong>Smoke-test checkpoint only.</strong> It scored 49% on its held-out test split. Predictions are unreliable and must not guide healthcare decisions.</p></div>}
            {result.prediction && <><div className="prediction-label"><span>Visual category</span><strong>{result.prediction.visual_category}</strong></div><div className="confidence-wrap"><div className="confidence-head"><span>Model confidence</span><strong>{(result.prediction.confidence * 100).toFixed(1)}%</strong></div><div className="confidence-track"><span style={{ width: `${result.prediction.confidence * 100}%` }} /></div><small>Softmax confidence is not necessarily a calibrated probability of diagnostic correctness.</small></div><ProbabilityList items={result.probabilities} /></>}
            {!result.prediction && <div className="empty-model-state"><span className="empty-model-icon"><Microscope size={22} /></span><h3>{unsuitable ? 'A clearer image is needed' : unavailable ? 'Model weights aren’t installed' : 'No reliable prediction is available'}</h3><p>{result.model_message ?? (unsuitable ? 'Please provide a clearer, higher-resolution image.' : 'No prediction was generated for this image.')}</p><span className="no-fabrication"><ShieldCheck size={14} /> No prediction or confidence has been invented.</span></div>}
            {uncertain && <div className="uncertainty-callout"><CircleAlert size={17} /><p>{lowConfidenceCopy}</p></div>}
          </article>
          {result.gradcam_data_url && <article className="result-card gradcam-card"><div className="card-title"><span>MODEL-ATTENTION VIEW</span><a className="download-link" href={result.gradcam_data_url} download={`skinsight-gradcam-${result.analysis_id}.png`}>Download <ArrowRight size={14} /></a></div><div className="compare-images"><figure><img src={previewUrl ?? ''} alt="Original uploaded image" /><figcaption>Original image</figcaption></figure><figure><img src={result.gradcam_data_url} alt="Grad-CAM model attention overlay" /><figcaption>Model attention overlay</figcaption></figure></div><p className="micro-disclaimer">Grad-CAM visualizes model attention. It is not proof of medical reasoning or lesion localization.</p></article>}
          {result.gradcam_message && <article className="result-card info-result"><Info size={17} />{result.gradcam_message}</article>}
          <article className="result-card education-card"><div className="education-icon"><HeartPulse size={19} /></div><div><span className="section-kicker">GENERAL EDUCATIONAL INFORMATION · NOT A TREATMENT PLAN</span><h3>{result.recommendation.title}</h3><p>{result.recommendation.information}</p><div className="care-guidance"><strong>General skin-care basics</strong><ul>{result.recommendation.general_guidance.map((text) => <li key={text}>{text}</li>)}</ul></div><div className="professional-notice"><CircleAlert size={17} /><p>{result.recommendation.care_notice}</p></div><p className="micro-disclaimer">{result.recommendation.limitation}</p></div></article>
          <article className="result-card provider-card">
            <div className="provider-heading"><span className="provider-icon"><MapPin size={18} /></span><div><span className="section-kicker">LOCAL CARE · HYDERABAD</span><h3>Find a dermatologist</h3></div></div>
            <p>Search current listings at these Hyderabad hospital groups. Check the doctor’s qualifications, location, availability, and booking details directly before visiting.</p>
            <div className="provider-links">{HYDERABAD_CARE_OPTIONS.map((provider) => {
              const query = encodeURIComponent(`dermatologist ${provider} Hyderabad`);
              return <a key={provider} href={`https://www.google.com/maps/search/?api=1&query=${query}`} target="_blank" rel="noopener noreferrer">{provider}<ExternalLink size={14} /></a>;
            })}</div>
            <p className="micro-disclaimer">These are search links, not vetted or endorsed doctor recommendations. SkinSight does not verify provider details or appointment availability.</p>
          </article>
        </div><p className="result-disclaimer"><ShieldCheck size={16} />{result.image_retained ? 'This image was saved locally because you opted in. Deleting this history entry removes the saved copy. ' : 'This image was not retained. '}{result.disclaimer}</p></section>}

      <section id="responsible-use" className="responsible-section"><div className="responsible-inner"><div className="responsible-mark"><ShieldCheck size={24} /></div><div><span className="section-kicker">IMPORTANT CONTEXT</span><h2>A screening prototype<br /><em>isn’t a diagnosis.</em></h2></div><div className="responsible-copy"><p>This academic project explores image-processing and explainability techniques. Image quality heuristics can miss important issues; visual categories and softmax scores can be wrong or uncalibrated.</p><p>Do not use this tool to decide whether to seek care or delay an appointment. For a spot that is changing, bleeding, painful, persistent, or concerning, talk with a qualified dermatologist or other healthcare professional.</p></div></div></section>

      <section id="privacy" className="privacy-section"><div className="privacy-card"><div className="privacy-icon"><LockKeyhole size={20} /></div><div><span className="section-kicker">PRIVACY, BY DESIGN</span><h2>Your image stays yours.</h2><p>Images are not saved by default. Retention is available only when enabled by the local operator and explicitly selected for an upload; deleting that history row also deletes its retained image. History stores a timestamp, quality status, model version, and a prediction/confidence only when available. Diary entries and reminders are stored only in this browser’s local storage; avoid entering identifying or highly sensitive details. Optional analysis context is discarded after the request. Use a local deployment you control for sensitive health images.</p></div><a href="#analyze" className="privacy-link">Explore the prototype <ArrowRight size={15} /></a></div></section>

      <section id="self-care" className="self-care-section">
        <div className="self-care-heading"><span className="section-kicker">EVERYDAY WELLNESS · GENERAL INFORMATION</span><h2>Simple habits for your skin.</h2><p>Keep routines gentle and consistent. These basics are not a treatment for any specific condition.</p></div>
        <div className="self-care-grid">
          <article className="self-care-card"><span className="self-care-icon"><HeartPulse size={19} /></span><h3>A gentle daily routine</h3><ul><li><strong>Morning:</strong> Wash gently, moisturize if needed, and use broad-spectrum SPF 30+ on exposed skin.</li><li><strong>During the day:</strong> Reapply sunscreen as directed on its label when outdoors; seek shade and wear protective clothing.</li><li><strong>Evening:</strong> Gently remove sunscreen and dirt, then moisturize if your skin feels dry.</li><li>Introduce new products one at a time and stop if a product causes persistent irritation.</li></ul></article>
          <article className="self-care-card"><span className="self-care-icon food-icon"><Leaf size={19} /></span><h3>Food and hydration</h3><ul><li>A varied, balanced diet with vegetables, fruit, whole grains, protein, and healthy fats supports general health.</li><li>Drink fluids according to thirst, activity, and your clinician’s advice; needs vary between people.</li><li>No single food or diet is proven to clear every skin condition. Avoid restrictive diets or supplements as a skin treatment without medical advice.</li><li>If you notice a repeatable food-related reaction, keep notes and discuss them with a clinician rather than removing major food groups on your own.</li></ul></article>
        </div>
        <p className="self-care-note"><Info size={15} /> Follow clinician advice for your own health needs. Seek care for a changing, bleeding, painful, persistent, or concerning spot.</p>
      </section>

      <section className="journal-section" aria-labelledby="journal-title">
        <div className="journal-heading"><div><span className="section-kicker">PRIVATE · THIS BROWSER ONLY</span><h2 id="journal-title">Skin diary &amp; reminders</h2><p>Track how your skin feels and remember follow-ups. Photos are not stored in this diary.</p></div><button type="button" className="button-outline" onClick={() => void enableBrowserReminders()}><Bell size={15} /> Enable browser alerts</button></div>
        {journalError && <p className="journal-error" role="alert">{journalError}</p>}
        {reminderNotice && <p className="journal-status" role="status">{reminderNotice}</p>}
        <div className="journal-grid">
          <article className="journal-card"><div className="journal-card-title"><BookOpen size={18} /><h3>Daily skin check-in</h3></div><form className="journal-form" onSubmit={addDiaryEntry}><label>Date<input type="date" value={diaryDate} onChange={(event) => setDiaryDate(event.target.value)} required /></label><label>Notes<textarea value={diaryNotes} onChange={(event) => setDiaryNotes(event.target.value)} maxLength={1000} placeholder="How does your skin feel? Note changes or products used." required /></label><button className="button-primary" type="submit">Save check-in <ArrowRight size={15} /></button></form>
            {diary.length > 0 && <div className="journal-list" aria-label="Skin diary entries">{diary.map((entry) => <article className="journal-entry" key={entry.id}><div><strong>{new Date(`${entry.date}T12:00:00`).toLocaleDateString()}</strong><p>{entry.notes}</p></div><button type="button" className="icon-button" aria-label={`Delete diary entry from ${entry.date}`} onClick={() => {
              const next = diary.filter((item) => item.id !== entry.id);
              try { saveSkinDiary(next); setDiary(next); setJournalError(''); }
              catch (cause) { setJournalError(cause instanceof Error ? cause.message : 'Could not delete this diary entry.'); }
            }}><Trash2 size={15} /></button></article>)}</div>}
          </article>
          <article className="journal-card"><div className="journal-card-title"><CalendarDays size={18} /><h3>Follow-up reminders</h3></div><form className="journal-form" onSubmit={addReminder}><label>Reminder<input type="text" value={reminderTitle} onChange={(event) => setReminderTitle(event.target.value)} maxLength={120} placeholder="e.g. Dermatology appointment" required /></label><label>Date and time<input type="datetime-local" value={reminderDate} onChange={(event) => setReminderDate(event.target.value)} required /></label><button className="button-primary" type="submit">Add reminder <ArrowRight size={15} /></button></form>
            {reminders.length > 0 ? <div className="journal-list" aria-label="Follow-up reminders">{reminders.map((reminder) => {
              const overdue = !reminder.completed && new Date(reminder.dueAt).getTime() <= Date.now();
              return <article className={`journal-entry ${reminder.completed ? 'journal-entry-complete' : ''}`} key={reminder.id}><div><strong>{reminder.title}</strong><p>{new Date(reminder.dueAt).toLocaleString()} {overdue && <span className="reminder-due">Due</span>}</p></div><div className="journal-entry-actions">{!reminder.completed && <button type="button" className="icon-button" aria-label={`Mark ${reminder.title} complete`} onClick={() => updateReminder(reminder.id, { completed: true })}><CheckCircle2 size={15} /></button>}<button type="button" className="icon-button" aria-label={`Delete reminder ${reminder.title}`} onClick={() => removeReminder(reminder.id)}><Trash2 size={15} /></button></div></article>;
            })}</div> : <p className="journal-empty">No reminders yet.</p>}
            <p className="micro-disclaimer">Browser alerts are optional and only work while this app is open. Due reminders remain visible here.</p>
          </article>
        </div>
      </section>

      <section className="history-section"><div className="history-heading"><div><span className="section-kicker">LOCAL SESSION HISTORY</span><h2>Recent image reviews</h2><p>Only minimal results metadata is stored in the local SQLite database.</p></div>{history.length > 0 && <button className="text-button danger-text" onClick={() => void removeHistory()}>Clear history</button>}</div>
        {historyError ? <p className="history-error" role="status">{historyError}</p> : history.length === 0 ? <div className="history-empty"><Clock3 size={18} /><span>No saved reviews yet. Only minimal result metadata is stored unless image retention is enabled and explicitly selected.</span></div> : <div className="history-list">{history.map((item) => <article className="history-item" key={item.id}><span className="history-icon"><FileImage size={17} /></span><div className="history-main"><strong>{item.predicted_category ?? 'No prediction available'}</strong><small>{new Date(item.created_at).toLocaleString()}</small></div>{item.image_retained && <span className="retained-tag">IMAGE SAVED</span>}<span className={`history-quality quality-${item.quality_status}`}>{item.quality_status}</span><span className="history-confidence">{item.confidence === null ? '—' : `${(item.confidence * 100).toFixed(1)}%`}</span><button className="icon-button" aria-label={`Delete history item ${item.id}`} onClick={() => void removeHistory(item.id)}><X size={16} /></button></article>)}</div>}
      </section>
    </main>

    <footer className="site-footer"><div className="footer-main"><Logo /><p>An academic exploration of skin-image screening, built with transparency at its core.</p><a href="#top" className="back-top">Back to top <ArrowDown size={14} /></a></div><div className="footer-bottom"><span>© 2026 SkinSight Academic Prototype</span><span>Educational use only · Not a medical device</span><span>Built for research &amp; learning</span></div></footer>
  </div>;
}
