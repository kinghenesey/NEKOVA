#!/usr/bin/env node
// Runs as `vscode:prepublish`, so `vsce package` and `vsce publish` refuse
// to build if any JSON file in the extension starts with a UTF-8 BOM.
//
// Why this exists: a BOM makes a JSON file invalid. JSON.parse and the
// TextMate engine both reject it, so a BOM on syntaxes/nekova.tmLanguage.json
// silently breaks ALL syntax highlighting in the published extension, and a
// BOM on package.json breaks npm/vsce. Windows tools (PowerShell's
// Set-Content/Out-File, Notepad, some editor settings) add one on save.
//
//   node scripts/check-json-bom.js          # check; exit 1 if any found
//   node scripts/check-json-bom.js --fix    # strip them in place

'use strict';
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const SKIP = new Set(['node_modules', '.git', 'out', 'dist']);
const fix = process.argv.includes('--fix');

function* walk(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.isDirectory()) {
      if (!SKIP.has(entry.name)) yield* walk(path.join(dir, entry.name));
    } else if (entry.name.endsWith('.json')) {
      yield path.join(dir, entry.name);
    }
  }
}

const offenders = [];
for (const file of walk(ROOT)) {
  const buf = fs.readFileSync(file);
  if (buf.length >= 3 && buf[0] === 0xef && buf[1] === 0xbb && buf[2] === 0xbf) {
    offenders.push(file);
    if (fix) fs.writeFileSync(file, buf.subarray(3));
  }
}

if (offenders.length === 0) {
  console.log('check-json-bom: OK - no JSON file has a BOM.');
} else if (fix) {
  for (const f of offenders) console.log('check-json-bom: stripped BOM from ' + path.relative(ROOT, f));
} else {
  console.error('check-json-bom: these JSON files start with a UTF-8 BOM, which makes them invalid JSON:');
  for (const f of offenders) console.error('  ' + path.relative(ROOT, f));
  console.error('Fix with:  node scripts/check-json-bom.js --fix');
  process.exit(1);
}