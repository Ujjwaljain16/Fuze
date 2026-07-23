/**
 * validate-tailwind.mjs
 * CI validation script — verifies Tailwind CSS v4 setup integrity.
 *
 * Checks:
 *  1. postcss.config.js uses @tailwindcss/postcss
 *  2. index.css uses @import "tailwindcss" (v4 syntax)
 *  3. No legacy tailwind.config.js (v3 artifact)
 *  4. Key @theme tokens are present in index.css
 */

import { readFileSync, existsSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

let errors = 0;

function check(description, condition, hint = '') {
  if (condition) {
    console.log(`  ✅  ${description}`);
  } else {
    console.error(`  ❌  ${description}${hint ? `\n      hint: ${hint}` : ''}`);
    errors++;
  }
}

console.log('\n🎨  Validating Tailwind CSS v4 configuration...\n');

// ── 1. postcss.config.js ────────────────────────────────────────────────────
const postcssPath = resolve(__dirname, 'postcss.config.js');
check(
  'postcss.config.js exists',
  existsSync(postcssPath),
  'Create postcss.config.js with @tailwindcss/postcss plugin',
);

if (existsSync(postcssPath)) {
  const postcssContent = readFileSync(postcssPath, 'utf8');
  check(
    'postcss.config.js uses @tailwindcss/postcss plugin',
    postcssContent.includes('@tailwindcss/postcss'),
    'Add { "@tailwindcss/postcss": {} } to postcss plugins',
  );
}

// ── 2. index.css — Tailwind v4 import ───────────────────────────────────────
const indexCssPath = resolve(__dirname, 'src/index.css');
check(
  'src/index.css exists',
  existsSync(indexCssPath),
  'Create src/index.css with @import "tailwindcss"',
);

if (existsSync(indexCssPath)) {
  const indexCss = readFileSync(indexCssPath, 'utf8');

  check(
    'src/index.css uses Tailwind v4 @import syntax',
    indexCss.includes('@import "tailwindcss"') || indexCss.includes("@import 'tailwindcss'"),
    'Add @import "tailwindcss"; to the top of index.css (v4 syntax — no tailwind.config.js needed)',
  );

  check(
    'src/index.css has @theme block for custom tokens',
    indexCss.includes('@theme'),
    'Add @theme { --color-primary-500: ...; } to index.css for custom design tokens',
  );

  // Spot-check key custom tokens
  const requiredTokens = [
    '--color-primary-500',
    '--color-secondary-500',
    '--font-family-sans',
  ];
  for (const token of requiredTokens) {
    check(
      `@theme token ${token} is defined`,
      indexCss.includes(token),
      `Add ${token} inside the @theme block in index.css`,
    );
  }
}

// ── 3. No legacy tailwind.config.js ─────────────────────────────────────────
const legacyConfig = resolve(__dirname, 'tailwind.config.js');
const legacyConfigTs = resolve(__dirname, 'tailwind.config.ts');
check(
  'No legacy tailwind.config.js (v3 artifact)',
  !existsSync(legacyConfig),
  'Delete tailwind.config.js — Tailwind v4 is configured entirely via CSS @theme',
);
check(
  'No legacy tailwind.config.ts (v3 artifact)',
  !existsSync(legacyConfigTs),
  'Delete tailwind.config.ts — Tailwind v4 is configured entirely via CSS @theme',
);

// ── 4. package.json has correct tailwind deps ────────────────────────────────
const pkgPath = resolve(__dirname, 'package.json');
if (existsSync(pkgPath)) {
  const pkg = JSON.parse(readFileSync(pkgPath, 'utf8'));
  const allDeps = { ...pkg.dependencies, ...pkg.devDependencies };

  check(
    '@tailwindcss/postcss is in devDependencies',
    '@tailwindcss/postcss' in allDeps,
    'Run: npm install -D @tailwindcss/postcss',
  );
}

// ── Result ───────────────────────────────────────────────────────────────────
console.log('');
if (errors === 0) {
  console.log('🎉  All Tailwind CSS v4 checks passed!\n');
  process.exit(0);
} else {
  console.error(`💥  ${errors} check(s) failed. Fix the issues above.\n`);
  process.exit(1);
}
