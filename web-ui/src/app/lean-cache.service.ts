import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { LeanPhoto } from './models';

/** Session-memory mirror of the server's lean metadata. Nothing is persisted. */
@Injectable({ providedIn: 'root' })
export class LeanCacheService {
  private photos: LeanPhoto[] = [];

  constructor(private readonly api: ApiService) {}

  async sync(): Promise<number> {
    const byUuid = new Map<string, LeanPhoto>();
    let cursor: number | string | null = null;
    for (;;) {
      const page = await this.api.sync(cursor);
      page.photos.forEach((photo) => byUuid.set(photo.uuid, photo));
      cursor = page.next_since;
      if (page.photos.length < 1000 || cursor === null) break;
    }
    this.photos = [...byUuid.values()].sort((a, b) => b.date - a.date);
    return this.photos.length;
  }

  all(): LeanPhoto[] {
    return [...this.photos];
  }

  clear(): void {
    this.photos = [];
  }
}
