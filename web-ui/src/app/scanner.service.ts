import { Injectable } from '@angular/core';
import * as exifr from 'exifr';
import { ApiService } from './api.service';
import { LeanCacheService } from './lean-cache.service';
import { LeanPhoto, ScanResult, WebConfig } from './models';
import { hashSimilar, PerceptualHashService } from './perceptual-hash.service';

interface Candidate {
  uuid: string;
  hash: string;
  date: number;
  width: number;
  height: number;
  remote: boolean;
}

@Injectable({ providedIn: 'root' })
export class ScannerService {
  constructor(
    private readonly cache: LeanCacheService,
    private readonly hashing: PerceptualHashService,
    private readonly api: ApiService,
  ) {}

  supported(): boolean {
    return typeof window.showDirectoryPicker === 'function';
  }

  async selectAndScan(
    config: WebConfig,
    progress: (result: ScanResult, processed: number, total: number) => void,
    signal?: AbortSignal,
  ): Promise<ScanResult[]> {
    if (!window.showDirectoryPicker) throw new Error('Folder scanning requires Chrome or Edge');
    const root = await window.showDirectoryPicker();
    return this.scanFiles(await this.walk(root), config, progress, signal);
  }

  async scanFiles(
    files: Array<{ file: File; path: string }>,
    config: WebConfig,
    progress: (result: ScanResult, processed: number, total: number) => void,
    signal?: AbortSignal,
  ): Promise<ScanResult[]> {
    // Always start from an authoritative, freshly-synced in-memory snapshot.
    await this.cache.sync();
    const remote = this.cache.all().map((photo) => this.remoteCandidate(photo));
    const batch: Candidate[] = [];
    const results: ScanResult[] = [];
    let id = 0;
    for (const { file, path } of files) {
      if (signal?.aborted) throw new DOMException('Scan cancelled', 'AbortError');
      let result: ScanResult = {
        id: id++,
        file,
        relativePath: path,
        status: 'scanning',
        detail: 'Reading metadata…',
        selected: false,
      };
      progress(result, results.length, files.length);
      try {
        result = await this.classify(result, config, batch, remote);
      } catch (error) {
        result = {
          ...result,
          status: 'error',
          detail: error instanceof Error ? error.message : String(error),
        };
      }
      results.push(result);
      progress(result, results.length, files.length);
    }
    return results;
  }

  async upload(result: ScanResult): Promise<string> {
    return this.api.upload(result.file);
  }

  private async classify(
    result: ScanResult,
    config: WebConfig,
    batch: Candidate[],
    remote: Candidate[],
  ): Promise<ScanResult> {
    const file = result.file;
    if (/\.(arw|cr2|cr3|nef|dng|raw)$/i.test(file.name))
      return { ...result, status: 'desktop', detail: 'RAW files require the desktop client' };
    const supportedType = ['image/jpeg', 'image/heic', 'image/heif'].includes(
      file.type.toLowerCase(),
    );
    if (!/\.(jpe?g|heic|heif)$/i.test(file.name) && !supportedType)
      return { ...result, status: 'desktop', detail: 'Unsupported image format' };

    const metadata = await exifr.parse(file, ['Make', 'Model', 'DateTimeOriginal', 'CreateDate']);
    const captured = metadata?.DateTimeOriginal ?? metadata?.CreateDate;
    const missing: string[] = [];
    if (!metadata?.Model) missing.push('camera');
    if (!captured) missing.push('date');
    if (missing.length)
      return {
        ...result,
        status: 'incomplete',
        detail: `Incomplete EXIF data (${missing.join('+')})`,
      };

    const hashed = await this.hashing.variants(file, config.hash_size);
    const date = new Date(captured).getTime() / 1000;
    const camera = [metadata.Make, metadata.Model].filter(Boolean).join(' ');
    const enriched = {
      ...result,
      hashes: hashed.variants,
      date,
      camera,
      width: hashed.width,
      height: hashed.height,
    };
    const match = this.findMatch(enriched, [...batch, ...remote], config);
    if (match?.reject)
      return {
        ...enriched,
        status: match.exact ? 'duplicate' : 'duplicate',
        detail: match.rotated
          ? 'Already in library (rotated copy)'
          : match.exact
            ? 'Identical to an existing photo'
            : 'Too similar to a preferable existing photo',
        duplicateUuid: match.candidate.uuid,
      };

    const preferable = match ? ' — preferable version' : '';
    batch.push({
      uuid: `batch-${result.id}`,
      hash: hashed.variants[0],
      date,
      width: hashed.width,
      height: hashed.height,
      remote: false,
    });
    return {
      ...enriched,
      status: 'new',
      detail: `New${preferable} — ready to upload`,
      selected: true,
      duplicateUuid: match?.candidate.remote ? match.candidate.uuid : undefined,
    };
  }

  private findMatch(
    result: ScanResult,
    candidates: Candidate[],
    config: WebConfig,
  ): { candidate: Candidate; exact: boolean; rotated: boolean; reject: boolean } | undefined {
    const variants = result.hashes ?? [];
    for (const candidate of candidates) {
      const index = variants.findIndex((hash) =>
        hashSimilar(hash, candidate.hash, config.hash_size, config.similarity),
      );
      if (index < 0) continue;
      const exact = variants[index] === candidate.hash;
      const rotated = index > 0;
      const existingPreferable =
        candidate.date < (result.date ?? 0) ||
        (candidate.date === result.date &&
          candidate.width * candidate.height > (result.width ?? 0) * (result.height ?? 0));
      const sameCapture =
        candidate.date === result.date &&
        candidate.width * candidate.height === (result.width ?? 0) * (result.height ?? 0);
      // Browser canvas and Pillow Lanczos hashes are intentionally compared
      // by similarity, not byte equality. Equal capture metadata compensates
      // for that cross-decoder difference so the same bytes remain a duplicate.
      return {
        candidate,
        exact,
        rotated,
        reject: exact || rotated || sameCapture || existingPreferable,
      };
    }
    return undefined;
  }

  private remoteCandidate(photo: LeanPhoto): Candidate {
    return {
      uuid: photo.uuid,
      hash: photo.hash,
      date: photo.date,
      width: photo.width,
      height: photo.height,
      remote: true,
    };
  }

  private async walk(
    root: FileSystemDirectoryHandle,
  ): Promise<Array<{ file: File; path: string }>> {
    const found: Array<{ file: File; path: string }> = [];
    const visit = async (directory: FileSystemDirectoryHandle, prefix: string) => {
      for await (const handle of directory.values()) {
        const path = prefix ? `${prefix}/${handle.name}` : handle.name;
        if (handle.kind === 'directory') await visit(handle, path);
        else found.push({ file: await handle.getFile(), path });
      }
    };
    await visit(root, '');
    return found.sort((a, b) => a.path.localeCompare(b.path));
  }
}
