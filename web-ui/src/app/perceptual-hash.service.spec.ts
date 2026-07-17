import { hashSimilar } from './perceptual-hash.service';

function encode(cells: number[]): string {
  return btoa(String.fromCharCode(...cells));
}

describe('hashSimilar', () => {
  it('mirrors the Python inclusive Hamming-distance threshold', () => {
    const base = Array(100).fill(0);
    const withinLimit = [...base];
    withinLimit[0] = 1;
    withinLimit[1] = 1;
    withinLimit[2] = 1;
    const overLimit = [...withinLimit];
    overLimit[3] = 1;
    expect(hashSimilar(encode(base), encode(withinLimit), 10, 97)).toBe(true);
    expect(hashSimilar(encode(base), encode(overLimit), 10, 97)).toBe(false);
  });

  it('rejects hashes with an unexpected grid size', () => {
    expect(hashSimilar(encode([0]), encode([0]), 70, 97)).toBe(false);
  });
});
