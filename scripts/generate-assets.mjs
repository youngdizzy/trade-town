#!/usr/bin/env node
/**
 * Asset discovery pipeline for TradeTown.
 *
 * Single source of truth for game art is `assets/cute-fantasy-rpg/` at the repo
 * root. This script:
 *   1. Recursively discovers every image in that directory (no hardcoded file
 *      list) and mirrors it into `frontend/public/assets/cute-fantasy-rpg/` so
 *      Vite can serve it.
 *   2. Reads each PNG's dimensions directly from its IHDR chunk (no external
 *      image library needed).
 *   3. Emits `frontend/src/assets/manifest.generated.json`, a data file the
 *      AssetLoader reads at runtime so no game code ever hardcodes a file path.
 *
 * Run via `npm run assets:sync` (also wired into predev/prebuild).
 */
import { readdirSync, statSync, mkdirSync, copyFileSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "..");
const SOURCE_DIR = path.join(REPO_ROOT, "assets", "cute-fantasy-rpg");
const PUBLIC_DEST_DIR = path.join(REPO_ROOT, "frontend", "public", "assets", "cute-fantasy-rpg");
const MANIFEST_OUT = path.join(REPO_ROOT, "frontend", "src", "assets", "manifest.generated.json");
const ANIMATION_CONFIG_PATH = path.join(REPO_ROOT, "frontend", "src", "assets", "animation-config.json");

/** Read PNG width/height straight from the IHDR chunk (bytes 16-24). */
function readPngSize(filePath) {
  const buf = Buffer.alloc(24);
  const fd = readFileSync(filePath);
  fd.copy(buf, 0, 0, 24);
  if (buf.readUInt32BE(0) !== 0x89504e47 && buf.toString("ascii", 1, 4) !== "PNG") {
    // Fall back: still attempt the standard offsets; PNG signature is 8 bytes.
  }
  const width = buf.readUInt32BE(16);
  const height = buf.readUInt32BE(20);
  return { width, height };
}

function toId(relPath) {
  return relPath
    .replace(/\.png$/i, "")
    .split(path.sep)
    .map((seg) => seg.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, ""))
    .join("/");
}

function walk(dir, base = "") {
  const entries = readdirSync(dir, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const abs = path.join(dir, entry.name);
    const rel = path.join(base, entry.name);
    if (entry.isDirectory()) {
      files.push(...walk(abs, rel));
    } else if (entry.isFile() && /\.png$/i.test(entry.name)) {
      files.push(rel);
    }
  }
  return files;
}

function categoryFromRelPath(relPath) {
  const top = relPath.split(path.sep)[0].toLowerCase();
  if (top === "tiles") return "tile";
  if (top === "player") return "player";
  if (top === "enemies") return "enemy";
  if (top === "animals") return "animal";
  if (top.startsWith("outdoor")) return "decoration";
  return "misc";
}

function main() {
  if (!existsSync(SOURCE_DIR)) {
    console.error(`[assets] Source directory not found: ${SOURCE_DIR}`);
    process.exit(1);
  }

  const relFiles = walk(SOURCE_DIR).sort();
  mkdirSync(PUBLIC_DEST_DIR, { recursive: true });
  mkdirSync(path.dirname(MANIFEST_OUT), { recursive: true });

  let animationConfig = {};
  if (existsSync(ANIMATION_CONFIG_PATH)) {
    animationConfig = JSON.parse(readFileSync(ANIMATION_CONFIG_PATH, "utf-8"));
  }

  const assets = {};

  for (const rel of relFiles) {
    const srcAbs = path.join(SOURCE_DIR, rel);
    const destAbs = path.join(PUBLIC_DEST_DIR, rel);
    mkdirSync(path.dirname(destAbs), { recursive: true });
    copyFileSync(srcAbs, destAbs);

    const { width, height } = readPngSize(srcAbs);
    const id = toId(rel);
    const publicUrl = `/assets/cute-fantasy-rpg/${rel.split(path.sep).join("/")}`;
    const category = categoryFromRelPath(rel);
    const override = animationConfig[id] ?? animationConfig[rel.split(path.sep).join("/")];

    assets[id] = {
      id,
      category,
      sourcePath: rel.split(path.sep).join("/"),
      url: publicUrl,
      width,
      height,
      ...(override ?? {}),
    };
  }

  const manifest = {
    generatedAt: new Date().toISOString(),
    assetCount: Object.keys(assets).length,
    assets,
  };

  writeFileSync(MANIFEST_OUT, JSON.stringify(manifest, null, 2));
  console.log(`[assets] Discovered ${Object.keys(assets).length} assets -> ${path.relative(REPO_ROOT, MANIFEST_OUT)}`);
}

main();
