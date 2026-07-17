import { Injectable } from '@angular/core';

export function hashSimilar(a: string, b: string, hashSize: number, similarity: number): boolean {
  const left = Uint8Array.from(atob(a), (c) => c.charCodeAt(0));
  const right = Uint8Array.from(atob(b), (c) => c.charCodeAt(0));
  if (left.length !== hashSize ** 2 || right.length !== left.length) return false;
  let differences = 0;
  for (let i = 0; i < left.length; i++) differences += left[i] === right[i] ? 0 : 1;
  return differences <= Math.floor((1 - similarity / 100) * hashSize ** 2);
}

@Injectable({ providedIn: 'root' })
export class PerceptualHashService {
  async variants(
    file: File,
    hashSize: number,
  ): Promise<{ variants: string[]; width: number; height: number }> {
    const bitmap = await this.decode(file);
    try {
      const width = bitmap.width;
      const height = bitmap.height;
      const canvas = new OffscreenCanvas(hashSize, hashSize);
      const context = canvas.getContext('2d', { willReadFrequently: true });
      if (!context) throw new Error('Canvas is unavailable');
      context.imageSmoothingEnabled = true;
      context.imageSmoothingQuality = 'high';
      context.drawImage(bitmap, 0, 0, hashSize, hashSize);
      const rgba = context.getImageData(0, 0, hashSize, hashSize).data;
      const gray = new Uint8Array(hashSize ** 2);
      let sum = 0;
      for (let i = 0; i < gray.length; i++) {
        const offset = i * 4;
        gray[i] = Math.round(
          0.299 * rgba[offset] + 0.587 * rgba[offset + 1] + 0.114 * rgba[offset + 2],
        );
        sum += gray[i];
      }
      const mean = sum / gray.length;
      let grid: Uint8Array<ArrayBufferLike> = Uint8Array.from(gray, (pixel) =>
        pixel > mean ? 1 : 0,
      );
      const variants: string[] = [];
      for (let degrees = 0; degrees < 360; degrees += 90) {
        variants.push(this.base64(grid));
        grid = this.rotateClockwise(grid, hashSize);
      }
      return { variants, width, height };
    } finally {
      bitmap.close();
    }
  }

  private async decode(file: File): Promise<ImageBitmap> {
    if (/\.(heic|heif)$/i.test(file.name)) {
      const { default: heic2any } = await import('heic2any');
      const converted = await heic2any({ blob: file, toType: 'image/jpeg', quality: 1 });
      return createImageBitmap(Array.isArray(converted) ? converted[0] : converted, {
        imageOrientation: 'none',
      });
    }
    return createImageBitmap(file, { imageOrientation: 'none' });
  }
  private rotateClockwise(
    source: Uint8Array<ArrayBufferLike>,
    size: number,
  ): Uint8Array<ArrayBufferLike> {
    const result = new Uint8Array(source.length);
    for (let y = 0; y < size; y++)
      for (let x = 0; x < size; x++) result[y * size + x] = source[(size - 1 - x) * size + y];
    return result;
  }
  private base64(data: Uint8Array<ArrayBufferLike>): string {
    let binary = '';
    for (let i = 0; i < data.length; i += 0x8000)
      binary += String.fromCharCode(...data.subarray(i, i + 0x8000));
    return btoa(binary);
  }
}
