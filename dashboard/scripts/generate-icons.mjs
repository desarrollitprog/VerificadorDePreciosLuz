import sharp from 'sharp';
import { mkdirSync, writeFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, '..');
const src = join(root, 'public', 'logoluz.png');
const outDir = join(root, 'public', 'icons');

mkdirSync(outDir, { recursive: true });

const sizes = [
  { name: 'icon-120x120.png', size: 120 },
  { name: 'icon-152x152.png', size: 152 },
  { name: 'icon-180x180.png', size: 180 },
  { name: 'pwa-192x192.png', size: 192 },
  { name: 'pwa-512x512.png', size: 512 },
  { name: 'favicon-32x32.png', size: 32 },
];

async function main() {
  const metadata = await sharp(src).metadata();
  const maxSide = Math.max(metadata.width, metadata.height);
  const squareSize = Math.max(maxSide, 512);

  // Create padded square version (white background)
  const left = Math.floor((squareSize - metadata.width) / 2);
  const top = Math.floor((squareSize - metadata.height) / 2);

  const squareBuffer = await sharp({
    create: {
      width: squareSize,
      height: squareSize,
      channels: 4,
      background: { r: 255, g: 255, b: 255, alpha: 1 },
    },
  })
    .composite([{ input: src, left, top }])
    .png()
    .toBuffer();

  // Generate each size
  for (const { name, size } of sizes) {
    const outPath = join(outDir, name);
    await sharp(squareBuffer)
      .resize(size, size, { fit: 'contain', background: { r: 255, g: 255, b: 255, alpha: 1 } })
      .png()
      .toFile(outPath);
    console.log(`✓ ${name} (${size}×${size})`);
  }

  // Also copy the square base as a reference
  const basePath = join(outDir, 'base-square.png');
  writeFileSync(basePath, squareBuffer);
  console.log(`✓ base-square.png (${squareSize}×${squareSize})`);
}

main().catch((err) => {
  console.error('Error generating icons:', err);
  process.exit(1);
});
