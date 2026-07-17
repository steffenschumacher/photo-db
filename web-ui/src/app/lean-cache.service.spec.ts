import { LeanCacheService } from './lean-cache.service';

describe('LeanCacheService', () => {
  it('rebuilds its in-memory snapshot from the beginning on every sync', async () => {
    let generation = 0;
    const api = {
      sync: vi.fn(async () => ({
        photos: [
          {
            uuid: `photo-${generation}`,
            hash: 'hash',
            date: generation,
            width: 1,
            height: 1,
            camera: 'camera',
            latitude: 1,
            longitude: 1,
            extension: 'jpeg',
            scanned: generation,
            rotation: 0,
          },
        ],
        next_since: null,
      })),
    };
    const cache = new LeanCacheService(api as never);

    await cache.sync();
    generation = 1;
    await cache.sync();

    expect(api.sync).toHaveBeenNthCalledWith(1, null);
    expect(api.sync).toHaveBeenNthCalledWith(2, null);
    expect(cache.all().map((photo) => photo.uuid)).toEqual(['photo-1']);
  });

  it('drops all metadata when cleared', async () => {
    const api = { sync: async () => ({ photos: [], next_since: null }) };
    const cache = new LeanCacheService(api as never);
    await cache.sync();
    cache.clear();
    expect(cache.all()).toEqual([]);
  });
});
