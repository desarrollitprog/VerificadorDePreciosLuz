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
  const cropSize = Math.min(metadata.width, metadata.height);

  // Center crop to square, then resize to each target size
  // No padding — avoids artifacts on iOS/Android icon rendering
  for (const { name, size } of sizes) {
    const outPath = join(outDir, name);
    await sharp(src)
      .resize(size, size, {
        fit: 'cover',
        position: 'centre',
      })
      .png()
      .toFile(outPath);
    console.log(`✓ ${name} (${size}×${size})`);
  }
}

main().catch((err) => {
  console.error('Error generating icons:', err);
  process.exit(1);
});
