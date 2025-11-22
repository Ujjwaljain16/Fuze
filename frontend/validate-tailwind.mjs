// Validate Tailwind config
import config from './tailwind.config.js';

if (!config) {
  console.error('✗ Tailwind config is empty or invalid');
  process.exit(1);
}

console.log('✓ Tailwind config is valid');
process.exit(0);

