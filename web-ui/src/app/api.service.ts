import { Injectable } from '@angular/core';
import { AuthService } from './auth.service';
import { LeanPhoto, WebConfig } from './models';

interface SyncPage {
  photos: LeanPhoto[];
  next_since: number | string | null;
}

export class ApiConflictError extends Error {
  constructor(
    message: string,
    readonly uuid: string,
    readonly code: number,
  ) {
    super(message);
  }
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  constructor(private readonly auth: AuthService) {}

  async config(): Promise<WebConfig> {
    return this.json('/web-config');
  }
  async sync(since: number | string | null, limit = 1000): Promise<SyncPage> {
    const query = new URLSearchParams({ limit: String(limit) });
    if (since !== null) query.set('since', String(since));
    return this.json(`/sync?${query}`);
  }
  async thumbnail(uuid: string, signal?: AbortSignal): Promise<Blob> {
    return this.request(`/thumb/${uuid}`, { signal }).then((r) => r.blob());
  }
  async image(uuid: string): Promise<Blob> {
    return this.request(`/image/${uuid}`).then((r) => r.blob());
  }
  async upload(file: File): Promise<string> {
    return this.request('/upload', { method: 'POST', body: file }).then((r) => r.text());
  }

  private async json<T>(url: string): Promise<T> {
    return this.request(url).then((r) => r.json());
  }
  private async request(url: string, init: RequestInit = {}): Promise<Response> {
    const authorization = this.auth.authorization;
    if (!authorization) throw new Error('Not authenticated');
    const response = await fetch(url, {
      ...init,
      headers: { ...init.headers, Authorization: authorization },
    });
    if (response.status === 401) this.auth.logout();
    if (!response.ok) {
      let detail = `${response.status} ${response.statusText}`;
      let error: { msg?: string; uuid?: string; pdb_code?: number } = {};
      try {
        error = await response.json();
        detail = error.msg ?? detail;
      } catch {
        /* non-JSON response */
      }
      if (response.status === 409 && error.uuid)
        throw new ApiConflictError(detail, error.uuid, error.pdb_code ?? 0);
      throw new Error(detail);
    }
    return response;
  }
}
