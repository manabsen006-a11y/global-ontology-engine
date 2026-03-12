import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const dir = path.join(__dirname, 'src', 'pages');
const files = fs.readdirSync(dir).filter(f => f.endsWith('.jsx'));

for (const file of files) {
    const p = path.join(dir, file);
    let code = fs.readFileSync(p, 'utf8');

    // 1. Remove gaming fonts
    code = code.replace(/fontFamily:\s*["']'Rajdhani',sans-serif["']\s*,?\s*/g, '');
    code = code.replace(/fontFamily:\s*["']'Share Tech Mono',monospace["']\s*,?\s*/g, '');

    // 2. Remove letter spacing
    code = code.replace(/letterSpacing:\s*['"][0-9.]+px['"]\s*,?\s*/g, '');

    // 3. Fix C.white in cards -> C.textBright. 
    code = code.replace(/color:\s*C\.white/g, 'color: C.textBright');

    // Restore header's C.white. The header always has `background: C.primary, color: C.textBright` now.
    code = code.replace(/background:\s*C\.primary,\s*color:\s*C\.textBright/g, 'background: C.primary, color: C.white');

    // Also restore active tab text color which is usually `color: C.textBright` next to `background: active ?` or `tab === t ?`
    code = code.replace(/color:\s*C\.textBright,\s*borderRadius/g, 'color: C.white, borderRadius');
    code = code.replace(/color:\s*(active[ \?]+C\.textBright)[^,]/g, 'color: active ? C.white');

    fs.writeFileSync(p, code);
    console.log(`Processed ${file}`);
}
