import { CommonModule, DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiConflictError, ApiService } from './api.service';
import { AuthImageComponent } from './auth-image.component';
import { AuthService } from './auth.service';
import { LeanCacheService } from './lean-cache.service';
import { LeanPhoto, ScanResult, WebConfig } from './models';
import { ScannerService } from './scanner.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule, DatePipe, AuthImageComponent],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App implements OnInit {
  public readonly auth = inject(AuthService);
  private readonly api = inject(ApiService);
  private readonly cache = inject(LeanCacheService);
  private readonly scanner = inject(ScannerService);
  username = '';
  password = '';
  loginError = '';
  readonly busy = signal(false);
  readonly message = signal('');
  readonly photos = signal<LeanPhoto[]>([]);
  readonly scanResults = signal<ScanResult[]>([]);
  readonly scanning = signal(false);
  readonly previewUrl = signal<string | null>(null);
  readonly previewPhoto = signal<LeanPhoto | null>(null);
  readonly config = signal<WebConfig | null>(null);
  readonly month = signal('all');
  readonly visibleLimit = signal(200);
  readonly scanProgress = signal({ processed: 0, total: 0 });
  readonly uploadProgress = signal({ processed: 0, total: 0, active: false });
  readonly autoUpload = signal(false);
  private scanController?: AbortController;
  readonly authenticated = this.auth.authenticated;
  readonly months = computed(() => [
    ...new Set(this.photos().map((p) => new Date(p.date * 1000).toISOString().slice(0, 7))),
  ]);
  readonly visiblePhotos = computed(() =>
    this.month() === 'all'
      ? this.photos()
      : this.photos().filter((p) => new Date(p.date * 1000).toISOString().startsWith(this.month())),
  );
  readonly displayedPhotos = computed(() => this.visiblePhotos().slice(0, this.visibleLimit()));
  readonly selectedCount = computed(
    () => this.scanResults().filter((r) => r.selected && r.status === 'new').length,
  );
  readonly scanSummary = computed(() => {
    const progress = this.scanProgress();
    const results = this.scanResults();
    return {
      ...progress,
      unscanned: Math.max(0, progress.total - progress.processed),
      duplicates: results.filter((row) => row.status === 'duplicate').length,
      eligible: results.filter((row) => row.status === 'new' || row.status === 'uploaded').length,
      percent: progress.total ? Math.round((progress.processed / progress.total) * 100) : 0,
    };
  });
  readonly uploadPercent = computed(() => {
    const progress = this.uploadProgress();
    return progress.total ? Math.round((progress.processed / progress.total) * 100) : 0;
  });
  readonly scanSupported = this.scanner.supported();

  async ngOnInit(): Promise<void> {
    if (this.auth.authenticated()) await this.initialize();
  }
  async login(): Promise<void> {
    this.busy.set(true);
    this.loginError = '';
    try {
      this.config.set(await this.auth.login(this.username, this.password));
      await this.refresh();
      this.password = '';
    } catch (error) {
      this.loginError = error instanceof Error ? error.message : String(error);
    } finally {
      this.busy.set(false);
    }
  }
  logout(): void {
    this.closePreview();
    this.auth.logout();
    this.cache.clear();
    this.photos.set([]);
    this.scanResults.set([]);
  }
  async initialize(): Promise<void> {
    try {
      this.config.set(await this.api.config());
      await this.refresh();
    } catch (error) {
      this.message.set(String(error));
    }
  }
  async refresh(): Promise<void> {
    this.busy.set(true);
    this.message.set('Syncing library…');
    try {
      const count = await this.cache.sync();
      this.photos.set(this.cache.all());
      this.visibleLimit.set(200);
      this.message.set(`Loaded ${count} photo${count === 1 ? '' : 's'} into session memory`);
    } catch (error) {
      this.message.set(error instanceof Error ? error.message : String(error));
    } finally {
      this.busy.set(false);
    }
  }
  setMonth(value: string): void {
    this.month.set(value);
    this.visibleLimit.set(200);
  }
  showMore(): void {
    this.visibleLimit.update((limit) => limit + 200);
  }
  async scan(): Promise<void> {
    await this.runScan((config, progress, signal) =>
      this.scanner.selectAndScan(config, progress, signal),
    );
  }
  async scanSelected(event: Event): Promise<void> {
    const input = event.target as HTMLInputElement;
    const files = Array.from(input.files ?? []);
    input.value = '';
    if (!files.length) return;
    await this.runScan(
      (config, progress, signal) =>
        this.scanner.scanFiles(
          files.map((file) => ({ file, path: file.name })),
          config,
          progress,
          signal,
        ),
      files.length,
    );
  }
  private async runScan(
    operation: (
      config: WebConfig,
      progress: (result: ScanResult, processed: number, total: number) => void,
      signal: AbortSignal,
    ) => Promise<ScanResult[]>,
    initialTotal = 0,
  ): Promise<void> {
    const config = this.config();
    if (!config) return;
    this.scanning.set(true);
    this.scanController = new AbortController();
    this.scanProgress.set({ processed: 0, total: initialTotal });
    this.uploadProgress.set({ processed: 0, total: 0, active: false });
    this.scanResults.set([]);
    this.message.set(
      this.autoUpload()
        ? 'Scanning locally — eligible photos upload one at a time'
        : 'Scanning locally — no image bytes are being uploaded',
    );
    const current = new Map<number, ScanResult>();
    let autoUploadQueue = Promise.resolve();
    let autoUploadCount = 0;
    try {
      // Safari needs a paint opportunity after dismissing its camera roll
      // before metadata decoding and canvas hashing start.
      await new Promise<void>((resolve) => requestAnimationFrame(() => setTimeout(resolve, 0)));
      await operation(
        config,
        (result, processed, total) => {
          current.set(result.id, result);
          this.scanResults.set([...current.values()].sort((a, b) => a.id - b.id));
          this.scanProgress.set({ processed, total });
          if (this.autoUpload() && result.status === 'new') {
            autoUploadCount++;
            this.uploadProgress.update((upload) => ({
              ...upload,
              total: upload.total + 1,
              active: true,
            }));
            autoUploadQueue = autoUploadQueue.then(async () => {
              const uploaded = { ...result, ...(await this.uploadPatch(result)) };
              current.set(result.id, uploaded);
              this.scanResults.set([...current.values()].sort((a, b) => a.id - b.id));
              this.uploadProgress.update((upload) => ({
                ...upload,
                processed: upload.processed + 1,
              }));
            });
          }
        },
        this.scanController.signal,
      );
      await autoUploadQueue;
      if (autoUploadCount) await this.cache.sync();
      this.photos.set(this.cache.all());
      this.message.set(
        autoUploadCount ? 'Scan and automatic upload complete' : 'Local scan complete',
      );
    } catch (error) {
      if ((error as DOMException).name !== 'AbortError')
        this.message.set(error instanceof Error ? error.message : String(error));
    } finally {
      // Uploads already accepted by the queue are allowed to finish even when
      // the remaining scan is cancelled.
      await autoUploadQueue;
      this.scanning.set(false);
      this.uploadProgress.update((progress) => ({ ...progress, active: false }));
      this.scanController = undefined;
    }
  }
  cancelScan(): void {
    this.scanController?.abort();
  }
  toggle(result: ScanResult): void {
    this.scanResults.update((rows) =>
      rows.map((row) => (row.id === result.id ? { ...row, selected: !row.selected } : row)),
    );
  }
  async uploadSelected(): Promise<void> {
    this.busy.set(true);
    const selected = this.scanResults().filter((item) => item.selected && item.status === 'new');
    this.uploadProgress.set({ processed: 0, total: selected.length, active: true });
    for (const row of selected) {
      this.replaceScan(row.id, await this.uploadPatch(row));
      this.uploadProgress.update((progress) => ({
        ...progress,
        processed: progress.processed + 1,
      }));
    }
    try {
      await this.refresh();
    } finally {
      this.uploadProgress.update((progress) => ({ ...progress, active: false }));
      this.busy.set(false);
    }
  }
  async preview(photo: LeanPhoto): Promise<void> {
    this.closePreview();
    this.previewPhoto.set(photo);
    try {
      this.previewUrl.set(URL.createObjectURL(await this.api.image(photo.uuid)));
    } catch (error) {
      this.message.set(error instanceof Error ? error.message : String(error));
      this.previewPhoto.set(null);
    }
  }
  previewDuplicate(result: ScanResult): void {
    const photo = this.photos().find((candidate) => candidate.uuid === result.duplicateUuid);
    if (photo) this.preview(photo);
  }
  closePreview(): void {
    const url = this.previewUrl();
    if (url) URL.revokeObjectURL(url);
    this.previewUrl.set(null);
    this.previewPhoto.set(null);
  }
  private replaceScan(id: number, patch: Partial<ScanResult>): void {
    this.scanResults.update((rows) =>
      rows.map((row) => (row.id === id ? { ...row, ...patch } : row)),
    );
  }
  private async uploadPatch(row: ScanResult): Promise<Partial<ScanResult>> {
    try {
      await this.scanner.upload(row);
      return { status: 'uploaded', selected: false, detail: 'Uploaded' };
    } catch (error) {
      if (error instanceof ApiConflictError)
        return {
          status: 'duplicate',
          selected: false,
          duplicateUuid: error.uuid,
          detail: error.message,
        };
      return {
        status: 'error',
        selected: false,
        detail: error instanceof Error ? error.message : String(error),
      };
    }
  }
}
