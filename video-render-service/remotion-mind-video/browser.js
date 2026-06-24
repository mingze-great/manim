import fs from 'node:fs';

const candidates = [
  process.env.CHROME_EXECUTABLE,
  process.env.REMOTION_BROWSER_EXECUTABLE,
  '/usr/bin/google-chrome',
  '/usr/bin/chromium',
  '/usr/bin/chromium-browser',
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
].filter(Boolean);

export const browserExecutable = candidates.find((candidate) => fs.existsSync(candidate)) ?? null;
