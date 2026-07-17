import {
  AfterViewInit,
  Component,
  ElementRef,
  Input,
  OnChanges,
  OnDestroy,
  ViewChild,
} from '@angular/core';
import { ApiService } from './api.service';

@Component({
  selector: 'app-auth-image',
  standalone: true,
  template: `<div #host class="frame">
    <span>Loading…</span>
    @if (url) {
      <img [src]="url" [alt]="alt" />
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
  url: string | null = null;
  private observer?: IntersectionObserver;
  constructor(private readonly api: ApiService) {}
  ngOnChanges(): void {
    if (this.host) this.observe();
  }
  ngAfterViewInit(): void {
    this.observe();
  }
  ngOnDestroy(): void {
    this.observer?.disconnect();
    this.release();
  }
  private observe(): void {
    this.release();
    this.observer?.disconnect();
    this.observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          this.load();
          this.observer?.disconnect();
        }
      },
      { rootMargin: '300px' },
    );
    this.observer.observe(this.host.nativeElement);
  }
  private async load(): Promise<void> {
    try {
      this.url = URL.createObjectURL(await this.api.thumbnail(this.uuid));
    } catch {
      /* placeholder remains */
    }
  }
  private release(): void {
    if (this.url) URL.revokeObjectURL(this.url);
    this.url = null;
  }
}
