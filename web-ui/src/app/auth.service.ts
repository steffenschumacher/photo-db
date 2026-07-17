import { Injectable, computed, signal } from '@angular/core';
import { WebConfig } from './models';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly storageKey = 'photodb-basic-auth';
  private readonly encoded = signal(sessionStorage.getItem(this.storageKey));
  readonly authenticated = computed(() => this.encoded() !== null);

  get authorization(): string | null {
    const value = this.encoded();
    return value ? `Basic ${value}` : null;
  }

  async login(username: string, password: string): Promise<WebConfig> {
    const encoded = btoa(unescape(encodeURIComponent(`${username}:${password}`)));
    const response = await fetch('/web-config', { headers: { Authorization: `Basic ${encoded}` } });
    if (!response.ok)
      throw new Error(
        response.status === 401
          ? 'Invalid username or password'
          : `Login failed (${response.status})`,
      );
    this.encoded.set(encoded);
    sessionStorage.setItem(this.storageKey, encoded);
    return response.json();
  }

  logout(): void {
    this.encoded.set(null);
    sessionStorage.removeItem(this.storageKey);
  }
}
