import { Injectable } from '@angular/core';
import { ApiService } from './api.service';

interface QueuedThumbnail {
  uuid: string;
  priority: number;
  controller: AbortController;
  cancelled: boolean;
  resolve: (blob: Blob) => void;
  reject: (reason: unknown) => void;
}

export interface ThumbnailRequest {
  promise: Promise<Blob>;
  cancel: () => void;
}

@Injectable({ providedIn: 'root' })
export class ThumbnailLoaderService {
  private readonly queue: QueuedThumbnail[] = [];
  private readonly cache = new Map<string, Blob>();
  private active = 0;
  private pumpScheduled = false;
  private readonly concurrency = 6;
  private readonly cacheLimit = 250;

  constructor(private readonly api: ApiService) {}

  request(uuid: string, priority: number): ThumbnailRequest {
    const cached = this.cache.get(uuid);
    if (cached) return { promise: Promise.resolve(cached), cancel: () => undefined };

    const controller = new AbortController();
    let task!: QueuedThumbnail;
    const promise = new Promise<Blob>((resolve, reject) => {
      task = { uuid, priority, controller, cancelled: false, resolve, reject };
      this.queue.push(task);
      this.schedulePump();
    });
    return {
      promise,
      cancel: () => {
        if (task.cancelled) return;
        task.cancelled = true;
        controller.abort();
      },
    };
  }

  private schedulePump(): void {
    if (this.pumpScheduled) return;
    this.pumpScheduled = true;
    queueMicrotask(() => {
      this.pumpScheduled = false;
      this.pump();
    });
  }

  private pump(): void {
    this.queue.sort((left, right) => left.priority - right.priority);
    while (this.active < this.concurrency && this.queue.length) {
      const task = this.queue.shift()!;
      if (task.cancelled) {
        task.reject(new DOMException('Thumbnail left viewport', 'AbortError'));
        continue;
      }
      this.active++;
      void this.load(task);
    }
  }

  private async load(task: QueuedThumbnail): Promise<void> {
    try {
      const blob = await this.api.thumbnail(task.uuid, task.controller.signal);
      if (task.cancelled) throw new DOMException('Thumbnail left viewport', 'AbortError');
      this.cache.set(task.uuid, blob);
      if (this.cache.size > this.cacheLimit) this.cache.delete(this.cache.keys().next().value!);
      task.resolve(blob);
    } catch (error) {
      task.reject(error);
    } finally {
      this.active--;
      this.pump();
    }
  }
}
