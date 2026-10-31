// ============================================================
// Upload & Analyse Page — Primary entry point
// ============================================================

import { useState, useRef, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Upload,
  FileText,
  X,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  Loader2,
  Video,
  Image as ImageIcon,
  FilePlus,
  Type,
  Paperclip,
} from 'lucide-react';
import * as Tabs from '@radix-ui/react-tabs';
import type { SourceType, BrandProfile } from '@/types/domain';
import { analysisService, historyService, demoBrandService } from '@/services/demo';
import { useApp } from '@/context/AppContext';
import { DemoAlert } from '@/components/ui/DemoBanner';
import {
  formatFileSize,
  getFileExtension,
  isSupportedTextFile,
  isSupportedDocFile,
  isSupportedImageFile,
  isSupportedVideoFile,
  countWords,
  countChars,
} from '@/lib/utils';
import { cn } from '@/lib/utils';

const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB

const CONTENT_TYPES = [
  'Blog post', 'Press release', 'Marketing copy', 'Email',
  'Product description', 'Social media post', 'Documentation',
  'Technical report', 'Newsletter', 'Website copy', 'Other',
];

const LANGUAGES = [
  'English (US)', 'English (UK)', 'English (AU)', 'Spanish',
  'French', 'German', 'Italian', 'Portuguese', 'Dutch', 'Other',
];

const AUDIENCES = [
  'General public', 'Business professionals', 'Technical experts',
  'Decision makers', 'Consumers', 'Investors', 'Media', 'Internal team',
];

// -----------------------------------------------------------
// SAMPLE TEXT — for easy demo
// -----------------------------------------------------------

const SAMPLE_TEXT = `BrandProof AI helps companies recieve consistent, high-quality content across all their communications. Our platform utilizes advanced AI technology to leverage insights from your brand guidelines.

In order to maintain brand consistency, their is no substitute for systematic content review. Alot of organizations struggle with this challenge.

We beleive that every piece of content should reflect your brand's voice. Our system can help you identify and correct issues before they occured in published materials.

Due to the fact that content quality matters, we've built a comprehensive solution that covers grammar, spelling, style, and brand voice alignment. E-mail us to learn more.`;

// -----------------------------------------------------------
// Main Page Component
// -----------------------------------------------------------

export function AnalysePage() {
  const navigate = useNavigate();
  const { setCurrentAnalysis, addToast } = useApp();

  // Input mode
  const [activeTab, setActiveTab] = useState<'text' | 'file'>('text');

  // Text input
  const [text, setText] = useState('');

  // File input
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [fileTextContent, setFileTextContent] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Context fields
  const [showContext, setShowContext] = useState(false);
  const [contentType, setContentType] = useState('');
  const [targetAudience, setTargetAudience] = useState('');
  const [language, setLanguage] = useState('English (UK)');
  const [writingInstructions, setWritingInstructions] = useState('');
  const [brandProfile, setBrandProfile] = useState<BrandProfile | null>(null);
  const [useBrandProfile, setUseBrandProfile] = useState(false);

  // Submission state
  const [isAnalysing, setIsAnalysing] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  // Load brand profile
  useEffect(() => {
    demoBrandService.get().then(profile => setBrandProfile(profile));
  }, []);

  // -----------------------------------------------------------
  // Validation
  // -----------------------------------------------------------

  function getContent(): { content: string; sourceType: SourceType; valid: boolean; error: string | null } {
    if (activeTab === 'text') {
      if (!text.trim()) return { content: '', sourceType: 'text', valid: false, error: 'Please enter some content to analyse.' };
      if (text.trim().length < 10) return { content: '', sourceType: 'text', valid: false, error: 'Content is too short. Please provide at least 10 characters.' };
      return { content: text, sourceType: 'text', valid: true, error: null };
    }
    if (!file) return { content: '', sourceType: 'file_text', valid: false, error: 'Please select a file to analyse.' };

    const ext = getFileExtension(file.name);
    if (isSupportedTextFile(file.name)) {
      if (!fileTextContent) return { content: '', sourceType: 'file_text', valid: false, error: 'File content is still loading.' };
      return { content: fileTextContent, sourceType: 'file_text', valid: true, error: null };
    }
    if (isSupportedDocFile(file.name)) {
      return { content: `[File: ${file.name}] Document content analysis requires backend integration. This demo records the file upload and demonstrates the workflow.`, sourceType: ext === 'pdf' ? 'file_pdf' : 'file_word', valid: true, error: null };
    }
    if (isSupportedImageFile(file.name)) {
      return { content: file.name, sourceType: 'file_image', valid: true, error: null };
    }
    if (isSupportedVideoFile(file.name)) {
      return { content: `[File: ${file.name}] Video transcription analysis requires backend integration.`, sourceType: 'file_video', valid: true, error: null };
    }

    return { content: '', sourceType: 'file_text', valid: false, error: `Unsupported file type: .${ext}` };
  }

  // -----------------------------------------------------------
  // File handling
  // -----------------------------------------------------------

  function handleFile(selectedFile: File) {
    setFileError(null);
    setFileTextContent(null);

    if (selectedFile.size > MAX_FILE_SIZE) {
      setFileError(`File too large (${formatFileSize(selectedFile.size)}). Maximum size is 50 MB.`);
      return;
    }

    const ext = getFileExtension(selectedFile.name);
    const supported = isSupportedTextFile(selectedFile.name) ||
      isSupportedDocFile(selectedFile.name) ||
      isSupportedImageFile(selectedFile.name) ||
      isSupportedVideoFile(selectedFile.name);

    if (!supported) {
      setFileError(`Unsupported file type: .${ext}. Supported: .txt, .md, .csv, .pdf, .doc, .docx, .jpg, .png, .webp, .mp4, .mov, .webm`);
      return;
    }

    setFile(selectedFile);

    // Read text files
    if (isSupportedTextFile(selectedFile.name)) {
      const reader = new FileReader();
      reader.onload = (e) => setFileTextContent(e.target?.result as string ?? '');
      reader.onerror = () => setFileError('Failed to read file. Please try again.');
      reader.readAsText(selectedFile, 'UTF-8');
    }
  }

  function handleFileInput(e: React.ChangeEvent<HTMLInputElement>) {
    const selected = e.target.files?.[0];
    if (selected) handleFile(selected);
    e.target.value = '';
  }

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) handleFile(dropped);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => setIsDragOver(false), []);

  // -----------------------------------------------------------
  // Submit
  // -----------------------------------------------------------

  async function handleAnalyse() {
    setValidationError(null);
    const { content, sourceType, valid, error } = getContent();

    if (!valid) {
      setValidationError(error);
      return;
    }

    setIsAnalysing(true);

    try {
      const analysis = await analysisService.analyze({
        content,
        sourceType,
        fileName: file?.name,
        file: file || undefined,
        contentType: contentType || undefined,
        targetAudience: targetAudience || undefined,
        language: language || undefined,
        writingInstructions: writingInstructions || undefined,
        brandProfile: useBrandProfile && brandProfile ? brandProfile : undefined,
      });

      await historyService.save(analysis);
      setCurrentAnalysis(analysis);
      navigate('/review');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'An error occurred. Please try again.';
      addToast({
        title: 'Analysis failed',
        description: message,
        variant: 'error',
      });
    } finally {
      setIsAnalysing(false);
    }
  }

  function handleReset() {
    setText('');
    setFile(null);
    setFileError(null);
    setFileTextContent(null);
    setValidationError(null);
  }

  // -----------------------------------------------------------
  // Render
  // -----------------------------------------------------------

  const hasContent = activeTab === 'text' ? text.trim().length > 0 : file !== null;

  return (
    <div className="max-w-3xl mx-auto space-y-5">
      {/* Page header */}
      <div className="page-header">
        <h2 className="page-title">Upload & Analyse</h2>
        <p className="page-description">
          Submit text or a file for brand quality and language analysis.
        </p>
      </div>

      <DemoAlert />

      {/* Input tabs */}
      <div className="card overflow-hidden">
        <Tabs.Root
          value={activeTab}
          onValueChange={v => {
            setActiveTab(v as 'text' | 'file');
            setValidationError(null);
          }}
        >
          <Tabs.List className="flex border-b border-surface-200 bg-surface-50">
            <Tabs.Trigger
              value="text"
              className={cn(
                'flex items-center gap-2 px-5 py-3 text-sm font-medium border-b-2 transition-colors',
                activeTab === 'text'
                  ? 'border-brand-500 text-brand-600 bg-white'
                  : 'border-transparent text-surface-500 hover:text-surface-700'
              )}
            >
              <Type className="w-4 h-4" />
              Text Input
            </Tabs.Trigger>
            <Tabs.Trigger
              value="file"
              className={cn(
                'flex items-center gap-2 px-5 py-3 text-sm font-medium border-b-2 transition-colors',
                activeTab === 'file'
                  ? 'border-brand-500 text-brand-600 bg-white'
                  : 'border-transparent text-surface-500 hover:text-surface-700'
              )}
            >
              <Paperclip className="w-4 h-4" />
              File Upload
            </Tabs.Trigger>
          </Tabs.List>

          {/* Text input */}
          <Tabs.Content value="text" className="p-5">
            <div className="relative">
              <textarea
                className="textarea-field min-h-[280px] font-mono text-sm leading-relaxed"
                placeholder="Paste or type your content here…&#10;&#10;Enter marketing copy, blog posts, product documentation, or any text to check for grammar, style, and brand alignment."
                value={text}
                onChange={e => {
                  setText(e.target.value);
                  setValidationError(null);
                }}
                aria-label="Content for analysis"
                disabled={isAnalysing}
              />
              <div className="absolute bottom-3 right-3 flex items-center gap-3">
                {text && (
                  <button
                    onClick={() => setText('')}
                    className="btn-ghost px-2 py-1 text-xs"
                    aria-label="Clear text"
                  >
                    <X className="w-3.5 h-3.5" />
                    Clear
                  </button>
                )}
                <span className="text-xs text-surface-400 tabular-nums">
                  {countWords(text).toLocaleString()} words · {countChars(text).toLocaleString()} chars
                </span>
              </div>
            </div>

            {/* Sample text shortcut */}
            {!text && (
              <div className="mt-3 flex items-center gap-2">
                <button
                  onClick={() => setText(SAMPLE_TEXT)}
                  className="text-xs text-brand-600 hover:text-brand-700 font-medium underline underline-offset-2"
                >
                  Load sample text
                </button>
                <span className="text-xs text-surface-400">— includes common issues to trigger findings</span>
              </div>
            )}
          </Tabs.Content>

          {/* File upload */}
          <Tabs.Content value="file" className="p-5">
            {!file ? (
              <div
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onClick={() => fileInputRef.current?.click()}
                className={cn(
                  'border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors',
                  isDragOver
                    ? 'border-brand-400 bg-brand-50'
                    : 'border-surface-200 hover:border-brand-300 hover:bg-surface-50'
                )}
                role="button"
                tabIndex={0}
                aria-label="Upload file"
                onKeyDown={e => e.key === 'Enter' && fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  className="sr-only"
                  onChange={handleFileInput}
                  accept=".txt,.md,.csv,.pdf,.doc,.docx,.jpg,.jpeg,.png,.gif,.webp,.svg,.mp4,.mov,.avi,.webm,.mkv"
                  aria-label="Select file"
                />
                <Upload className="w-8 h-8 text-surface-400 mx-auto mb-3" />
                <p className="text-sm font-medium text-surface-700">
                  Drop a file here, or <span className="text-brand-600">browse</span>
                </p>
                <p className="text-xs text-surface-400 mt-1.5">
                  Supported: .txt, .md, .csv, .pdf, .doc, .docx · Images: .jpg, .png, .webp · Video: .mp4, .mov, .webm
                </p>
                <p className="text-xs text-surface-400 mt-1">
                  Maximum file size: 50 MB
                </p>
              </div>
            ) : (
              <FilePreview
                file={file}
                textContent={fileTextContent}
                onRemove={() => {
                  setFile(null);
                  setFileTextContent(null);
                  setFileError(null);
                }}
              />
            )}

            {fileError && (
              <div className="mt-3 flex items-start gap-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg p-3">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <span>{fileError}</span>
              </div>
            )}

            {/* Video limitation notice */}
            {file && isSupportedVideoFile(file.name) && (
              <div className="mt-3 flex items-start gap-2 text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg p-3">
                <Video className="w-4 h-4 shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium">Video analysis requires backend integration</p>
                  <p className="text-xs mt-0.5">Transcription, subtitle extraction and on-screen OCR will be available once the backend is connected. This demo records the upload and runs the workflow.</p>
                </div>
              </div>
            )}
          </Tabs.Content>
        </Tabs.Root>
      </div>

      {/* Optional context */}
      <div className="card overflow-hidden">
        <button
          onClick={() => setShowContext(s => !s)}
          className="w-full flex items-center justify-between px-5 py-4 text-sm font-medium text-surface-700 hover:bg-surface-50 transition-colors"
          aria-expanded={showContext}
          aria-controls="context-panel"
        >
          <span>Analysis Context <span className="text-surface-400 font-normal">(optional)</span></span>
          {showContext
            ? <ChevronUp className="w-4 h-4 text-surface-400" />
            : <ChevronDown className="w-4 h-4 text-surface-400" />
          }
        </button>

        {showContext && (
          <div id="context-panel" className="px-5 pb-5 border-t border-surface-100">
            <div className="grid sm:grid-cols-2 gap-4 mt-4">
              {/* Content type */}
              <div>
                <label htmlFor="content-type" className="label">Content Type</label>
                <select
                  id="content-type"
                  className="input-field"
                  value={contentType}
                  onChange={e => setContentType(e.target.value)}
                  disabled={isAnalysing}
                >
                  <option value="">Select type…</option>
                  {CONTENT_TYPES.map(t => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>

              {/* Target audience */}
              <div>
                <label htmlFor="audience" className="label">Target Audience</label>
                <select
                  id="audience"
                  className="input-field"
                  value={targetAudience}
                  onChange={e => setTargetAudience(e.target.value)}
                  disabled={isAnalysing}
                >
                  <option value="">Select audience…</option>
                  {AUDIENCES.map(a => (
                    <option key={a} value={a}>{a}</option>
                  ))}
                </select>
              </div>

              {/* Language */}
              <div>
                <label htmlFor="language" className="label">Language</label>
                <select
                  id="language"
                  className="input-field"
                  value={language}
                  onChange={e => setLanguage(e.target.value)}
                  disabled={isAnalysing}
                >
                  {LANGUAGES.map(l => (
                    <option key={l} value={l}>{l}</option>
                  ))}
                </select>
              </div>

              {/* Brand profile */}
              {brandProfile && (
                <div>
                  <label className="label">Brand Profile</label>
                  <div className="flex items-center gap-3 mt-1.5">
                    <input
                      type="checkbox"
                      id="use-brand"
                      checked={useBrandProfile}
                      onChange={e => setUseBrandProfile(e.target.checked)}
                      className="w-4 h-4 accent-brand-600"
                      disabled={isAnalysing}
                    />
                    <label htmlFor="use-brand" className="text-sm text-surface-700 cursor-pointer">
                      Apply <span className="font-medium">{brandProfile.name}</span> guidelines
                    </label>
                  </div>
                </div>
              )}
            </div>

            {/* Writing instructions */}
            <div className="mt-4">
              <label htmlFor="instructions" className="label">Writing Instructions</label>
              <textarea
                id="instructions"
                className="textarea-field h-20"
                placeholder="e.g. Use active voice. Keep sentences under 20 words. Avoid technical jargon."
                value={writingInstructions}
                onChange={e => setWritingInstructions(e.target.value)}
                disabled={isAnalysing}
              />
            </div>
          </div>
        )}
      </div>

      {/* Validation error */}
      {validationError && (
        <div className="flex items-start gap-2.5 px-4 py-3 rounded-lg bg-red-50 border border-red-200">
          <AlertCircle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
          <p className="text-sm text-red-700">{validationError}</p>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          {hasContent && !isAnalysing && (
            <button onClick={handleReset} className="btn-ghost text-sm">
              <X className="w-4 h-4" />
              Reset
            </button>
          )}
        </div>

        <button
          onClick={handleAnalyse}
          disabled={isAnalysing || (!hasContent)}
          className="btn-primary"
        >
          {isAnalysing ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Analysing…
            </>
          ) : (
            <>
              <FilePlus className="w-4 h-4" />
              Analyse Content
            </>
          )}
        </button>
      </div>

      {/* Processing message */}
      {isAnalysing && (
        <div className="flex items-center gap-3 px-4 py-3 rounded-lg bg-brand-50 border border-brand-200">
          <Loader2 className="w-4 h-4 text-brand-600 animate-spin shrink-0" />
          <div>
            <p className="text-sm font-medium text-brand-800">Analyzing content with BrandProof AI…</p>
            <p className="text-xs text-brand-600">Checking language quality, grammar, and brand alignment.</p>
          </div>
        </div>
      )}
    </div>
  );
}

// -----------------------------------------------------------
// File Preview Component
// -----------------------------------------------------------

interface FilePreviewProps {
  file: File;
  textContent: string | null;
  onRemove: () => void;
}

function FilePreview({ file, textContent, onRemove }: FilePreviewProps) {
  const ext = getFileExtension(file.name);
  const isImage = isSupportedImageFile(file.name);
  const [imageUrl] = useState(() => isImage ? URL.createObjectURL(file) : null);

  const getIcon = () => {
    if (isSupportedVideoFile(file.name)) return <Video className="w-5 h-5 text-purple-500" />;
    if (isSupportedImageFile(file.name)) return <ImageIcon className="w-5 h-5 text-green-500" />;
    if (isSupportedDocFile(file.name)) return <FileText className="w-5 h-5 text-red-500" />;
    return <FileText className="w-5 h-5 text-brand-500" />;
  };

  return (
    <div className="space-y-3">
      {/* File info bar */}
      <div className="flex items-center gap-3 px-4 py-3 rounded-lg bg-surface-50 border border-surface-200">
        <div className="w-9 h-9 rounded-lg bg-white border border-surface-200 flex items-center justify-center shrink-0">
          {getIcon()}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-surface-900 truncate">{file.name}</p>
          <p className="text-xs text-surface-400">{formatFileSize(file.size)} · .{ext.toUpperCase()}</p>
        </div>
        <button
          onClick={onRemove}
          className="btn-ghost p-1.5 text-surface-400 hover:text-surface-700"
          aria-label="Remove file"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Image preview */}
      {isImage && imageUrl && (
        <div className="rounded-lg overflow-hidden border border-surface-200 max-h-48 flex items-center justify-center bg-surface-50">
          <img
            src={imageUrl}
            alt={`Preview of ${file.name}`}
            className="max-h-48 max-w-full object-contain"
          />
        </div>
      )}

      {/* Text file preview */}
      {textContent !== null && (
        <div className="rounded-lg border border-surface-200 bg-surface-50 p-3">
          <p className="text-xs text-surface-400 mb-2">Preview ({countWords(textContent)} words)</p>
          <pre className="text-xs text-surface-700 font-mono whitespace-pre-wrap line-clamp-6 leading-relaxed">
            {textContent.slice(0, 600)}{textContent.length > 600 ? '…' : ''}
          </pre>
        </div>
      )}
    </div>
  );
}
