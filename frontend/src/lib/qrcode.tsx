/**
 * Pure TypeScript QR Code generator (Version 3 & 4, Level L, Byte Mode).
 * Renders an accessible SVG without any third-party dependencies.
 */
import React from "react";

// GF(256) with primitive polynomial 0x11d
const EXP_TABLE = new Uint8Array(512);
const LOG_TABLE = new Uint8Array(256);

(() => {
  let x = 1;
  for (let i = 0; i < 255; i++) {
    EXP_TABLE[i] = x;
    EXP_TABLE[i + 255] = x;
    LOG_TABLE[x] = i;
    x <<= 1;
    if (x & 0x100) x ^= 0x11d;
  }
})();

function gfMul(x: number, y: number): number {
  if (x === 0 || y === 0) return 0;
  return EXP_TABLE[LOG_TABLE[x] + LOG_TABLE[y]];
}

function rsGeneratorPoly(degree: number): Uint8Array {
  let poly = new Uint8Array([1]);
  for (let i = 0; i < degree; i++) {
    const next = new Uint8Array(poly.length + 1);
    const factor = EXP_TABLE[i];
    for (let j = 0; j < poly.length; j++) {
      next[j] ^= gfMul(poly[j], factor);
      next[j + 1] ^= poly[j];
    }
    poly = next;
  }
  return poly;
}

function rsCalculateEC(data: Uint8Array, ecCount: number): Uint8Array {
  const gen = rsGeneratorPoly(ecCount);
  const remainder = new Uint8Array(ecCount);
  for (let i = 0; i < data.length; i++) {
    const factor = data[i] ^ remainder[0];
    remainder.copyWithin(0, 1);
    remainder[ecCount - 1] = 0;
    for (let j = 0; j < ecCount; j++) {
      remainder[j] ^= gfMul(gen[j], factor);
    }
  }
  return remainder;
}

export function generateQrMatrix(text: string): boolean[][] {
  const bytes = new TextEncoder().encode(text);
  const version = bytes.length <= 53 ? 3 : 4;
  const size = 17 + 4 * version;
  const dataCapacity = version === 3 ? 55 : 80;
  const ecCount = version === 3 ? 15 : 20;

  const bitstream: number[] = [];
  const pushBits = (val: number, len: number) => {
    for (let i = len - 1; i >= 0; i--) {
      bitstream.push((val >> i) & 1);
    }
  };

  pushBits(0b0100, 4); // Byte mode indicator
  pushBits(bytes.length, 8); // Character count
  for (const b of bytes) pushBits(b, 8);

  const padLen = Math.min(4, dataCapacity * 8 - bitstream.length);
  pushBits(0, padLen);

  while (bitstream.length % 8 !== 0) bitstream.push(0);

  const dataBytes = new Uint8Array(dataCapacity);
  for (let i = 0; i < bitstream.length / 8; i++) {
    let byteVal = 0;
    for (let b = 0; b < 8; b++) byteVal = (byteVal << 1) | bitstream[i * 8 + b];
    dataBytes[i] = byteVal;
  }

  let padToggle = 0xec;
  for (let i = bitstream.length / 8; i < dataCapacity; i++) {
    dataBytes[i] = padToggle;
    padToggle = padToggle === 0xec ? 0x11 : 0xec;
  }

  const ecBytes = rsCalculateEC(dataBytes, ecCount);
  const totalCodewords = new Uint8Array(dataCapacity + ecCount);
  totalCodewords.set(dataBytes);
  totalCodewords.set(ecBytes, dataCapacity);

  const matrix: boolean[][] = Array.from({ length: size }, () => Array(size).fill(false));
  const reserved: boolean[][] = Array.from({ length: size }, () => Array(size).fill(false));

  const setModule = (r: number, c: number, val: boolean) => {
    matrix[r][c] = val;
    reserved[r][c] = true;
  };

  const drawFinder = (row: number, col: number) => {
    for (let r = -1; r <= 7; r++) {
      for (let c = -1; c <= 7; c++) {
        const mr = row + r;
        const mc = col + c;
        if (mr >= 0 && mr < size && mc >= 0 && mc < size) {
          const isBlack = (r >= 0 && r <= 6 && (c === 0 || c === 6)) ||
                          (c >= 0 && c <= 6 && (r === 0 || r === 6)) ||
                          (r >= 2 && r <= 4 && c >= 2 && c <= 4);
          setModule(mr, mc, isBlack);
        }
      }
    }
  };

  drawFinder(0, 0);
  drawFinder(0, size - 7);
  drawFinder(size - 7, 0);

  const alignCenter = version === 3 ? 22 : 26;
  for (let r = -2; r <= 2; r++) {
    for (let c = -2; c <= 2; c++) {
      const isBlack = Math.max(Math.abs(r), Math.abs(c)) !== 1;
      setModule(alignCenter + r, alignCenter + c, isBlack);
    }
  }

  for (let i = 8; i < size - 8; i++) {
    const val = i % 2 === 0;
    if (!reserved[6][i]) setModule(6, i, val);
    if (!reserved[i][6]) setModule(i, 6, val);
  }

  setModule(4 * version + 9, 8, true);

  for (let i = 0; i < 9; i++) {
    if (i !== 6) {
      reserved[8][i] = true;
      reserved[i][8] = true;
    }
  }
  for (let i = 0; i < 8; i++) {
    reserved[8][size - 1 - i] = true;
    reserved[size - 1 - i][8] = true;
  }

  let bitIndex = 0;
  const allBits: number[] = [];
  for (const b of totalCodewords) {
    for (let i = 7; i >= 0; i--) allBits.push((b >> i) & 1);
  }

  let dir = -1;
  for (let c = size - 1; c > 0; c -= 2) {
    if (c === 6) c--;
    const rStart = dir === -1 ? size - 1 : 0;
    const rEnd = dir === -1 ? -1 : size;
    for (let r = rStart; r !== rEnd; r += dir) {
      for (const col of [c, c - 1]) {
        if (!reserved[r][col]) {
          const bit = bitIndex < allBits.length ? allBits[bitIndex++] : 0;
          const mask = (r + col) % 2 === 0;
          matrix[r][col] = (bit === 1) !== mask;
        }
      }
    }
    dir = -dir;
  }

  const formatBits = [1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 1, 0, 0];
  const fmtCoords = [
    [8, 0], [8, 1], [8, 2], [8, 3], [8, 4], [8, 5], [8, 7], [8, 8],
    [7, 8], [5, 8], [4, 8], [3, 8], [2, 8], [1, 8], [0, 8],
  ];
  for (let i = 0; i < 15; i++) {
    const val = formatBits[i] === 1;
    const [r, c] = fmtCoords[i];
    matrix[r][c] = val;
  }
  for (let i = 0; i < 7; i++) {
    matrix[size - 1 - i][8] = formatBits[i] === 1;
  }
  for (let i = 0; i < 8; i++) {
    matrix[8][size - 8 + i] = formatBits[7 + i] === 1;
  }

  return matrix;
}

export function QrCodeSvg({
  value,
  size = 180,
  className = "",
}: {
  value: string;
  size?: number;
  className?: string;
}) {
  const matrix = React.useMemo(() => generateQrMatrix(value), [value]);
  const n = matrix.length;
  const padding = 2;
  const total = n + padding * 2;

  const rects: React.ReactNode[] = [];
  for (let r = 0; r < n; r++) {
    for (let c = 0; c < n; c++) {
      if (matrix[r][c]) {
        rects.push(
          <rect
            key={`${r}-${c}`}
            x={c + padding}
            y={r + padding}
            width={1}
            height={1}
            fill="#0f172a"
          />
        );
      }
    }
  }

  return (
    <svg
      viewBox={`0 0 ${total} ${total}`}
      width={size}
      height={size}
      className={`rounded-xl bg-white p-2 shadow-xs border border-line ${className}`}
      aria-label={`QR Code for ${value}`}
      role="img"
    >
      <rect width={total} height={total} fill="#ffffff" rx="1" />
      {rects}
    </svg>
  );
}
