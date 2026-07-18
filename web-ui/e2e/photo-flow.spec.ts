import { expect, test } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const credentials = Buffer.from('webtest:webtest-pass').toString('base64');
const staticDir = resolve(process.cwd(), '../test/static');

async function fixture(name: string, type: string) {
  return { name, type, base64: (await readFile(resolve(staticDir, name))).toString('base64') };
}

test('classifies real JPEG/HEIF fixtures locally and uploads eligible new files', async ({
  page,
  request,
  browserName,
}) => {
  test.skip(browserName !== 'chromium', 'directory picker flow is Chromium-specific');
  const jpeg = await fixture('08-190641-4631.jpeg', 'image/jpeg');
  const modified = await fixture('08-190641-4631-modified.jpeg', 'image/jpeg');
  const incomplete = await fixture('25-121007-33d0.jpeg', 'image/jpeg');
  const heif = await fixture('0A4E249E-E8B1-4BA8-8FBD-6D778B3DE99E.heif', 'image/heif');
  const headers = {
    Authorization: `Basic ${credentials}`,
    'Content-Type': 'application/octet-stream',
  };

  expect(
    (
      await request.post('http://127.0.0.1:5000/upload', {
        headers,
        data: await readFile(resolve(staticDir, jpeg.name)),
      })
    ).ok(),
  ).toBeTruthy();
  await page.addInitScript(
    ({ fixtures }) => {
      const decode = (value: string) => {
        const binary = atob(value);
        return Uint8Array.from(binary, (character) => character.charCodeAt(0));
      };
      Object.defineProperty(window, 'showDirectoryPicker', {
        configurable: true,
        value: async () => ({
          kind: 'directory',
          name: 'fixtures',
          async *values() {
            for (const item of fixtures) {
              yield {
                kind: 'file',
                name: item.name,
                getFile: async () =>
                  new File([decode(item.base64)], item.name, { type: item.type }),
              };
            }
            yield {
              kind: 'file',
              name: 'camera.ARW',
              getFile: async () => new File([new Uint8Array()], 'camera.ARW'),
            };
          },
        }),
      });
    },
    { fixtures: [jpeg, modified, incomplete, heif] },
  );

  await page.goto('/');
  await page.getByLabel('Username').fill('webtest');
  await page.getByLabel('Password').fill('webtest-pass');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByText('Loaded 1 photo into session memory')).toBeVisible();
  await page.getByRole('button', { name: 'Scan a folder' }).click();
  await expect(page.getByText('Local scan complete')).toBeVisible();

  const row = (name: string) => page.locator('.scan-row').filter({ hasText: name });
  await expect(row(jpeg.name)).toContainText('duplicate');
  await expect(row(heif.name)).toContainText('new');
  await expect(row(incomplete.name)).toContainText('new');
  await expect(row('camera.ARW')).toContainText('desktop');
  await expect(row(modified.name)).toContainText('duplicate');
  await expect(row(jpeg.name).getByRole('button', { name: 'View existing photo' })).toBeVisible();

  await page.getByRole('button', { name: 'Upload 2 new' }).click();
  await expect(row(heif.name)).toContainText('uploaded');
  await expect(row(incomplete.name)).toContainText('uploaded');

  const sync = await request.get('http://127.0.0.1:5000/sync?limit=100', {
    headers: { Authorization: `Basic ${credentials}` },
  });
  expect(sync.ok()).toBeTruthy();
  expect((await sync.json()).photos).toHaveLength(3);

  // The server hashes the uploaded HEIF with Pillow. A second browser scan
  // proves the canvas/HEIC hash still falls within the Python similarity limit.
  await page.getByRole('button', { name: 'Scan a folder' }).click();
  await expect(page.getByText('Local scan complete')).toBeVisible();
  await expect(row(heif.name)).toContainText('duplicate');
});
