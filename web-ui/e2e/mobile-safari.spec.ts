import { expect, test } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const staticDir = resolve(process.cwd(), '../test/static');

test.describe('iPhone Safari companion', () => {
  test.skip(({ browserName }) => browserName !== 'webkit', 'Safari behavior requires WebKit');

  test('loads only viewport thumbnails and prioritizes newly visible cards', async ({ page }) => {
    const thumbnail = await readFile(resolve(staticDir, '08-190641-4631.jpeg'));
    const photos = Array.from({ length: 100 }, (_, index) => ({
      uuid: `mobile-photo-${index}`,
      hash: btoa(String.fromCharCode(...new Uint8Array(70 * 70))),
      date: 1_700_000_000 - index,
      width: 100,
      height: 100,
      camera: `Camera ${index}`,
      latitude: null,
      longitude: null,
      extension: 'jpeg',
      scanned: 1_700_000_000 - index,
      rotation: 0,
    }));
    let thumbnailRequests = 0;
    await page.route('**/sync?**', (route) =>
      route.fulfill({ json: { photos, next_since: null } }),
    );
    await page.route('**/thumb/**', async (route) => {
      thumbnailRequests++;
      await route.fulfill({ body: thumbnail, contentType: 'image/jpeg' });
    });

    await signIn(page);
    await expect(page.getByText('Loaded 100 photos into session memory')).toBeVisible();
    await expect.poll(() => thumbnailRequests).toBeGreaterThan(0);
    await expect
      .poll(() =>
        page
          .locator('.photo img')
          .first()
          .evaluate((image) => image.naturalWidth),
      )
      .toBeGreaterThan(0);
    expect(thumbnailRequests).toBeLessThan(20);

    const initiallyLoaded = thumbnailRequests;
    await page.locator('.photo').nth(40).scrollIntoViewIfNeeded();
    await expect.poll(() => thumbnailRequests).toBeGreaterThan(initiallyLoaded);
    expect(thumbnailRequests).toBeLessThan(35);
  });

  test('selects, scans, and uploads a camera-roll photo', async ({ page }) => {
    await page.route('**/sync?**', (route) =>
      route.fulfill({ json: { photos: [], next_since: null } }),
    );
    await page.route('**/upload', (route) => route.fulfill({ body: 'mobile-upload-id' }));
    await signIn(page);

    const picker = page.locator('input[type=file]');
    await expect(page.getByRole('button', { name: 'Select photos' })).toBeVisible();
    await picker.setInputFiles({
      name: 'IMG_0001.JPG',
      mimeType: 'image/jpeg',
      buffer: await readFile(resolve(staticDir, '08-190641-4631.jpeg')),
    });

    await expect(page.getByText('Local scan complete')).toBeVisible();
    const row = page.locator('.scan-row').filter({ hasText: 'IMG_0001.JPG' });
    await expect(row).toContainText('new');
    await page.getByRole('button', { name: 'Upload 1 new' }).click();
    await expect(row).toContainText('uploaded');
  });
});

async function signIn(page: import('@playwright/test').Page) {
  await page.goto('/');
  await page.getByLabel('Username').fill('webtest');
  await page.getByLabel('Password').fill('webtest-pass');
  await page.getByRole('button', { name: 'Sign in' }).click();
}
