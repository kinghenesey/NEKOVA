#!/usr/bin/env node
// Runs as part of `vscode:prepublish`. Fails packaging if the extension icon
// would be rejected by the Visual Studio Marketplace.
//
// Why this exists: the Marketplace refuses an icon larger than 1024x1024
// pixels ("The provided icon image exceeds the maximum allowed dimensions"),
// and only says so at upload time, after a successful local `vsce package`.
// It also wants at least 128x128 so the icon isn't blurry. This reads the
// PNG header directly (no image library needed) and checks both.
//
//   node scripts/check-icon.js

'use strict';
const fs = require('fs');
const path = require('path');

const MIN = 128;
const MAX = 1024;
const ROOT = path.join(__dirname, '..');
const pkg = JSON.parse(fs.readFileSync(path.join(ROOT, 'package.json'), 'utf8').replace(/^\uFEFF/, ''));

if (!pkg.icon) {
  console.log('check-icon: OK - no icon declared in package.json.');
  process.exit(0);
}

const iconPath = path.join(ROOT, pkg.icon);
if (!fs.existsSync(iconPath)) {
  console.error('check-icon: package.json declares icon "' + pkg.icon + '" but that file does not exist.');
  process.exit(1);
}

const buf = fs.readFileSync(iconPath);
const PNG_SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
if (buf.length < 24 || !buf.subarray(0, 8).equals(PNG_SIGNATURE)) {
  console.error('check-icon: ' + pkg.icon + ' is not a PNG file (the Marketplace requires PNG; SVG is not allowed).');
  process.exit(1);
}

const width = buf.readUInt32BE(16);
const height = buf.readUInt32BE(20);
const problems = [];
if (width > MAX || height > MAX) {
  problems.push(width + 'x' + height + ' exceeds the Marketplace maximum of ' + MAX + 'x' + MAX + ' pixels');
}
if (width < MIN || height < MIN) {
  problems.push(width + 'x' + height + ' is below the recommended minimum of ' + MIN + 'x' + MIN + ' pixels');
}
if (width !== height) {
  problems.push(width + 'x' + height + ' is not square; the Marketplace displays it in a square frame');
}

if (problems.length === 0) {
  console.log('check-icon: OK - ' + pkg.icon + ' is ' + width + 'x' + height + ' px.');
} else {
  console.error('check-icon: ' + pkg.icon + ' would be rejected or look wrong on the Marketplace:');
  for (const p of problems) console.error('  - ' + p);
  process.exit(1);
}