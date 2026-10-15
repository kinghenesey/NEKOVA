#!/usr/bin/env node
// Runs as part of `vscode:prepublish`. Guards against shipping an extension
// whose runtime dependencies are missing from the VSIX.
//
// Why this exists: extension.js does `require('vscode-languageclient/node')`
// at load time. If node_modules is excluded by .vscodeignore (or was never
// installed), the packaged extension throws "Cannot find module" the moment
// VS Code loads it, which silently disables the language server, hover,
// diagnostics, and every command. Highlighting and snippets still work
// (they are declarative), so nothing looks obviously wrong on a quick
// test, and it cannot be caught by F5 development, where node_modules is
// always present. Only a real install of the packaged VSIX shows it.
//
//   node scripts/check-runtime-deps.js

'use strict';
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const readText = (p) => fs.readFileSync(p, 'utf8').replace(/^\uFEFF/, '');

const pkg = JSON.parse(readText(path.join(ROOT, 'package.json')));
const deps = Object.keys(pkg.dependencies || {});
const problems = [];

// 1. Every runtime dependency must be installed, or vsce has nothing to package.
for (const dep of deps) {
  if (!fs.existsSync(path.join(ROOT, 'node_modules', dep, 'package.json'))) {
    problems.push(`runtime dependency "${dep}" is not installed - run: npm install`);
  }
}

// 2. .vscodeignore must not exclude node_modules wholesale.
const ignorePath = path.join(ROOT, '.vscodeignore');
if (deps.length > 0 && fs.existsSync(ignorePath)) {
  const rules = readText(ignorePath).split(/\r?\n/).map((l) => l.trim())
    .filter((l) => l && !l.startsWith('#'));
  const excludesAll = rules.some((l) => /^(\*\*\/)?node_modules(\/(\*\*)?)?$/.test(l));
  const reincludes = rules.some((l) => l.startsWith('!') && l.includes('node_modules'));
  if (excludesAll && !reincludes) {
    problems.push('.vscodeignore excludes node_modules, so ' + deps.join(', ') +
      ' would be missing from the VSIX and extension.js would fail to load');
  }
}

if (problems.length === 0) {
  console.log('check-runtime-deps: OK - ' + (deps.length ? deps.join(', ') + ' will ship in the VSIX.' : 'no runtime dependencies.'));
} else {
  console.error('check-runtime-deps: the packaged extension would be broken:');
  for (const p of problems) console.error('  - ' + p);
  process.exit(1);
}