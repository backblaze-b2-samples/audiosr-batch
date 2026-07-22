/**
 * Client-side allow-list for the dropzone, mirroring the backend's
 * `ALLOWED_TYPES` / `MIME_EXTENSION_MAP` in
 * `services/api/app/service/upload.py`. This app ingests low-quality AUDIO to
 * super-resolve, so the allow-list is audio-only. The server re-validates every
 * upload — this only gives instant feedback and filters the OS file picker.
 * Keep the two in sync when adding or removing a type.
 *
 * Shape matches react-dropzone's `accept`: MIME type → matching extensions.
 */
export const ACCEPTED_FILE_TYPES: Record<string, string[]> = {
  "audio/mpeg": [".mp3", ".mpeg"],
  "audio/wav": [".wav"],
  "audio/x-wav": [".wav"],
  "audio/ogg": [".ogg", ".oga"],
};
