import { ApiConflictError, ApiService } from './api.service';

describe('ApiService', () => {
  it('preserves duplicate UUIDs returned by upload conflicts', async () => {
    const auth = { authorization: 'Basic test', logout: vi.fn() };
    const service = new ApiService(auth as never);
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ pdb_code: 1001, uuid: 'existing-id', msg: 'duplicate' }), {
        status: 409,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    const error = await service.upload(new File(['image'], 'photo.jpeg')).catch((reason) => reason);
    expect(error).toBeInstanceOf(ApiConflictError);
    expect(error).toMatchObject({ message: 'duplicate', uuid: 'existing-id', code: 1001 });
  });
});
