export interface LeanPhoto {
  uuid: string;
  hash: string;
  date: number;
  width: number;
  height: number;
  camera: string;
  latitude: number | null;
  longitude: number | null;
  extension: string;
  scanned: number;
  rotation: number;
}

export interface WebConfig {
  hash_size: number;
  similarity: number;
}

export type ScanStatus =
  'scanning' | 'duplicate' | 'new' | 'incomplete' | 'desktop' | 'error' | 'uploaded';

export interface ScanResult {
  id: number;
  file: File;
  relativePath: string;
  status: ScanStatus;
  detail: string;
  selected: boolean;
  duplicateUuid?: string;
  hashes?: string[];
  date?: number;
  width?: number;
  height?: number;
  camera?: string;
}
