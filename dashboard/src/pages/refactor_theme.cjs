const fs = require('fs');
const path = require('path');

const dir = '/Users/shouryathakur/Development/LavenderHealth/dashboard_temp/src/pages/';
const files = ['ClinicDetailPage.jsx', 'ClinicsPage.jsx', 'DraftsPage.jsx', 'RunsPage.jsx', 'SettingsPage.jsx'];

const map = {
  'bg-white': 'bg-[#18181b]',
  'bg-surface': 'bg-[#121212]',
  'border-black/8': 'border-zinc-800',
  'border-black/10': 'border-zinc-700',
  'text-ink': 'text-zinc-100',
  'text-muted': 'text-zinc-400',
  'text-black': 'text-white',
  'bg-black/5': 'bg-zinc-800/50',
  'bg-black/[0.04]': 'bg-zinc-800/50',
  'bg-black/[0.02]': 'bg-zinc-800/30',
  'bg-black/[0.08]': 'bg-zinc-700/50',
  'bg-black': 'bg-zinc-100',
  'text-white': 'text-zinc-900',
  'bg-subtle': 'bg-[#121212]',
  'divide-black/8': 'divide-zinc-800',
  'rounded-[32px]': 'rounded-xl',
  'rounded-[24px]': 'rounded-lg',
  'rounded-[20px]': 'rounded-md',
  'rounded-[16px]': 'rounded-md',
  'rounded-[12px]': 'rounded-sm',
};

files.forEach(file => {
  const filePath = path.join(dir, file);
  if (!fs.existsSync(filePath)) {
    console.error('Not found:', filePath);
    return;
  }
  
  let content = fs.readFileSync(filePath, 'utf8');

  // Replace shadows first (using replace)
  content = content.replace(/shadow-\[[^\]]+\]/g, 'shadow-xl');

  // Token replacement for classes
  content = content.replace(/[\w\-./\[\]#]+/g, (match) => {
    // Exact mapping matches
    if (map.hasOwnProperty(match)) {
      return map[match];
    }
    
    // Prefix fallback mapping
    if (match.startsWith('bg-black/')) {
       return match.replace('bg-black', 'bg-zinc-100');
    }
    if (match.startsWith('border-black/')) {
       return match.replace('border-black', 'border-zinc-800');
    }
    if (match === 'border-black') {
       return 'border-zinc-800';
    }
    if (match.startsWith('divide-black/')) {
       return match.replace('divide-black', 'divide-zinc-800');
    }
    if (match === 'divide-black') {
       return 'divide-zinc-800';
    }
    
    return match;
  });

  fs.writeFileSync(filePath, content, 'utf8');
  console.log('Refactored:', file);
});
