export type FileStatus = "uploading" | "complete" | "error";

export interface FileMetadata {
  key: string;
  filename: string;
  folder: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
}

export interface FileMetadataDetail {
  filename: string;
  size_bytes: number;
  size_human: string;
  mime_type: string;
  extension: string;
  md5: string;
  sha256: string;
  uploaded_at: string;
  // Image-specific
  image_width: number | null;
  image_height: number | null;
  exif: Record<string, string> | null;
  // PDF-specific
  pdf_pages: number | null;
  pdf_author: string | null;
  pdf_title: string | null;
  // Audio/Video
  duration_seconds: number | null;
  codec: string | null;
  bitrate: number | null;
}

export interface FileUploadResponse {
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
  metadata: FileMetadataDetail | null;
}

export interface DailyUploadCount {
  date: string;
  uploads: number;
}

export interface UploadStats {
  total_files: number;
  total_size_bytes: number;
  total_size_human: string;
  uploads_today: number;
  total_downloads: number;
}

// --- Audio super-resolution (enhancement jobs) ---

export type JobStatus = "queued" | "processing" | "completed" | "failed";
export type QualityPreset = "fast" | "balanced" | "high";

export interface EnhancementParams {
  ddim_steps: number;
  guidance_scale: number;
  seed: number;
  model_name: string;
}

export interface EnhancementJob {
  id: string;
  input_key: string;
  output_key: string;
  sidecar_key: string;
  collection: string;
  status: JobStatus;
  quality_preset: QualityPreset;
  params: EnhancementParams;
  input_sample_rate: number | null;
  output_sample_rate: number | null;
  input_duration_sec: number | null;
  model_version: string | null;
  device_used: string | null;
  input_size_bytes: number | null;
  output_size_bytes: number | null;
  amplification_ratio: number | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateJobRequest {
  input_key: string;
  quality_preset: QualityPreset;
  seed?: number | null;
}

export interface EnhancementStats {
  files_enhanced: number;
  jobs_total: number;
  total_original_bytes: number;
  total_enhanced_bytes: number;
  total_original_human: string;
  total_enhanced_human: string;
  amplification_ratio: number;
  avg_input_sample_rate: number;
  avg_output_sample_rate: number;
  jobs_by_status: Record<string, number>;
}

export interface EnhancementActivityPoint {
  date: string;
  bytes: number;
}

export interface LibraryTrack {
  collection: string;
  original_key: string;
  original_filename: string;
  original_size_bytes: number;
  original_size_human: string;
  content_type: string;
  uploaded_at: string;
  enhanced_key: string | null;
  enhanced_size_bytes: number | null;
  enhanced_size_human: string | null;
  amplification_ratio: number | null;
}
