import { describe, expect, it, vi } from 'vitest';
import { ApiService } from './api.service';
import { ThumbnailLoaderService } from './thumbnail-loader.service';

describe('ThumbnailLoaderService', () => {
  it('runs no more than six thumbnail requests at once', async () => {
    const resolvers: Array<(blob: Blob) => void> = [];
    const api = {
      thumbnail: vi.fn(() => new Promise<Blob>((resolve) => resolvers.push(resolve))),
    } as unknown as ApiService;
    const loader = new ThumbnailLoaderService(api);
    const requests = Array.from({ length: 7 }, (_, index) =>
      loader.request(`photo-${index}`, index),
    );

    await Promise.resolve();
    expect(api.thumbnail).toHaveBeenCalledTimes(6);

    resolvers[0](new Blob(['first']));
    await Promise.resolve();
    await Promise.resolve();
    expect(api.thumbnail).toHaveBeenCalledTimes(7);

    for (const resolve of resolvers.slice(1)) resolve(new Blob(['remaining']));
    await Promise.all(requests.map((request) => request.promise));
  });
});
