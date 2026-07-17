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
    const config = this.config();
    if (!config) return;
    this.scanning.set(true);
    this.scanController = new AbortController();
    this.scanProgress.set({ processed: 0, total: 0 });
    this.scanResults.set([]);
    this.message.set('Scanning locally — no image bytes are being uploaded');
    const current = new Map<number, ScanResult>();
    try {
      await this.scanner.selectAndScan(
        config,
        (result, processed, total) => {
          current.set(result.id, result);
          this.scanResults.set([...current.values()].sort((a, b) => a.id - b.id));
          this.scanProgress.set({ processed, total });
        },
        this.scanController.signal,
      );
      this.photos.set(this.cache.all());
      this.message.set('Local scan complete');
    } catch (error) {
      if ((error as DOMException).name !== 'AbortError')
        this.message.set(error instanceof Error ? error.message : String(error));
    } finally {
      this.scanning.set(false);
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
    for (const row of this.scanResults().filter((item) => item.selected && item.status === 'new')) {
      try {
        await this.scanner.upload(row);
        this.replaceScan(row.id, { status: 'uploaded', selected: false, detail: 'Uploaded' });
      } catch (error) {
        if (error instanceof ApiConflictError)
          this.replaceScan(row.id, {
            status: 'duplicate',
            selected: false,
            duplicateUuid: error.uuid,
            detail: error.message,
          });
        else
          this.replaceScan(row.id, {
            status: 'error',
            selected: false,
            detail: error instanceof Error ? error.message : String(error),
          });
      }
    }
    await this.refresh();
    this.busy.set(false);
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
}
