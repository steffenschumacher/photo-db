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
    let activeThumbnailRequests = 0;
    let maxActiveThumbnailRequests = 0;
    await page.route('**/sync?**', (route) =>
      route.fulfill({ json: { photos, next_since: null } }),
    );
    await page.route('**/thumb/**', async (route) => {
      thumbnailRequests++;
      activeThumbnailRequests++;
      maxActiveThumbnailRequests = Math.max(maxActiveThumbnailRequests, activeThumbnailRequests);
      await new Promise((resolve) => setTimeout(resolve, 75));
      await route.fulfill({ body: thumbnail, contentType: 'image/jpeg' });
      activeThumbnailRequests--;
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
    expect(maxActiveThumbnailRequests).toBeLessThanOrEqual(6);

    const initiallyLoaded = thumbnailRequests;
    await page.locator('.photo').nth(40).scrollIntoViewIfNeeded();
    await expect.poll(() => thumbnailRequests).toBeGreaterThan(initiallyLoaded);
    expect(thumbnailRequests).toBeLessThan(35);
  });

  test('selects, scans, and uploads a camera-roll photo', async ({ page }) => {
    await page.route('**/sync?**', (route) =>
      route.fulfill({ json: { photos: [], next_since: null } }),
    );
    await page.route('**/upload', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 250));
      await route.fulfill({ body: 'mobile-upload-id' });
    });
    await signIn(page);

    const picker = page.locator('input[type=file]');
    await expect(page.getByRole('button', { name: 'Select photos' })).toBeVisible();
    await picker.setInputFiles({
      name: 'IMG_0001.JPG',
      mimeType: 'image/jpeg',
      buffer: await readFile(resolve(staticDir, '08-190641-4631.jpeg')),
    });

    await expect(page.getByText('Local scan complete')).toBeVisible();
    await expect(page.getByLabel('Scanning progress')).toHaveAttribute('value', '1');
    await expect(page.getByText('1 upload eligible')).toBeVisible();
    const row = page.locator('.scan-row').filter({ hasText: 'IMG_0001.JPG' });
    await expect(row).toContainText('new');
    await page.getByRole('button', { name: 'Upload 1 new' }).click();
    await expect(page.getByLabel('Upload progress')).toBeVisible();
    await expect(row).toContainText('uploaded');
  });

  test('shows progress immediately for a larger camera-roll selection', async ({ page }) => {
    await page.route('**/sync?**', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 300));
      await route.fulfill({ json: { photos: [], next_since: null } });
    });
    await signIn(page);

    const buffer = await readFile(resolve(staticDir, '08-190641-4631.jpeg'));
    const files = Array.from({ length: 12 }, (_, index) => ({
      name: `IMG_${String(index).padStart(4, '0')}.JPG`,
      mimeType: 'image/jpeg',
      buffer,
    }));
    await page.locator('input[type=file]').setInputFiles(files);

    await expect(page.getByText('12 selected')).toBeVisible();
    await expect(page.getByText('12 unscanned')).toBeVisible();
    await expect(page.getByLabel('Scanning progress')).toBeVisible();
    await expect(page.getByText('Local scan complete')).toBeVisible({ timeout: 30_000 });
    await expect(page.getByText('0 unscanned')).toBeVisible();
    await expect(page.getByText('11 duplicates')).toBeVisible();
    await expect(page.getByText('1 upload eligible')).toBeVisible();
  });

  test('auto-uploads eligible photos one at a time while scanning continues', async ({ page }) => {
    let activeUploads = 0;
    let maximumActiveUploads = 0;
    let uploadRequests = 0;
    await page.route('**/sync?**', (route) =>
      route.fulfill({ json: { photos: [], next_since: null } }),
    );
    await page.route('**/upload', async (route) => {
      uploadRequests++;
      activeUploads++;
      maximumActiveUploads = Math.max(maximumActiveUploads, activeUploads);
      await new Promise((resolve) => setTimeout(resolve, 400));
      await route.fulfill({ body: `auto-upload-${uploadRequests}` });
      activeUploads--;
    });
    await signIn(page);
    await page.getByLabel('Auto-upload eligible').check();

    await page.locator('input[type=file]').setInputFiles([
      {
        name: 'FIRST.JPG',
        mimeType: 'image/jpeg',
        buffer: await readFile(resolve(staticDir, '08-190641-4631.jpeg')),
      },
      {
        name: 'SECOND.JPG',
        mimeType: 'image/jpeg',
        buffer: await readFile(resolve(staticDir, '25-121007-33d0.jpeg')),
      },
    ]);

    await expect(page.getByLabel('Upload progress')).toBeVisible();
    await expect(page.getByText('Scan and automatic upload complete')).toBeVisible();
    await expect(page.locator('.scan-row.uploaded')).toHaveCount(2);
    expect(uploadRequests).toBe(2);
    expect(maximumActiveUploads).toBe(1);
  });
});

async function signIn(page: import('@playwright/test').Page) {
  await page.goto('/');
  await page.getByLabel('Username').fill('webtest');
  await page.getByLabel('Password').fill('webtest-pass');
  await page.getByRole('button', { name: 'Sign in' }).click();
}
