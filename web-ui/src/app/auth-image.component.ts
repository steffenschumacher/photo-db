import {
  AfterViewInit,
  Component,
  ElementRef,
  Input,
  OnChanges,
  OnDestroy,
  ViewChild,
  signal,
} from '@angular/core';
import { ThumbnailLoaderService, ThumbnailRequest } from './thumbnail-loader.service';

@Component({
  selector: 'app-auth-image',
  standalone: true,
  template: `<div #host class="frame">
    <span>Loading…</span>
    @if (url()) {
      <img [src]="url()" [alt]="alt" />
    }
  </div>`,
  styles: [
    `
      .frame {
        height: 100%;
        display: grid;
        place-items: center;
        background: #e9ece8;
        color: #68706a;
      }
      .frame > * {
        grid-area: 1/1;
      }
      img {
        width: 100%;
        height: 100%;
        object-fit: cover;
      }
    `,
  ],
})
export class AuthImageComponent implements OnChanges, AfterViewInit, OnDestroy {
  @Input({ required: true }) uuid!: string;
  @Input() alt = '';
  @ViewChild('host', { static: true }) host!: ElementRef<HTMLElement>;
  readonly url = signal<string | null>(null);
  private observer?: IntersectionObserver;
  private request?: ThumbnailRequest;
  private loadingUuid?: string;
  constructor(private readonly loader: ThumbnailLoaderService) {}
  ngOnChanges(): void {
    if (this.host) this.observe();
  }
  ngAfterViewInit(): void {
    this.observe();
  }
  ngOnDestroy(): void {
    this.observer?.disconnect();
    this.cancel();
    this.release();
  }
  private observe(): void {
    this.release();
    this.observer?.disconnect();
    this.observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.find((entry) => entry.isIntersecting);
        if (visible) this.load(visible.boundingClientRect);
        else if (!this.url()) this.cancel();
      },
      { rootMargin: '0px', threshold: 0.01 },
    );
    this.observer.observe(this.host.nativeElement);
  }
  private async load(rect: DOMRectReadOnly): Promise<void> {
    if (this.url() || this.loadingUuid === this.uuid) return;
    this.cancel();
    const uuid = this.uuid;
    this.loadingUuid = uuid;
    const priority = Math.abs(rect.top + rect.height / 2 - window.innerHeight / 2);
    const request = this.loader.request(uuid, priority);
    this.request = request;
    try {
      const blob = await request.promise;
      if (this.uuid === uuid) this.url.set(URL.createObjectURL(blob));
    } catch {
      /* placeholder remains */
    } finally {
      if (this.request === request) {
        this.loadingUuid = undefined;
        this.request = undefined;
      }
    }
  }
  private cancel(): void {
    this.request?.cancel();
    this.request = undefined;
    this.loadingUuid = undefined;
  }
  private release(): void {
    const url = this.url();
    if (url) URL.revokeObjectURL(url);
    this.url.set(null);
  }
}
