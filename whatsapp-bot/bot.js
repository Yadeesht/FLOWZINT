const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const express = require('express');

const app = express();
app.use(express.json());

const PORT = process.env.PORT || 3001;
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

const fs = require('fs');
const path = require('path');
const os = require('os');

// Resolve local Chrome executable path (Windows + Linux)
let executablePath = '';
if (process.platform === 'win32') {
    const possiblePaths = [
        'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
        'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
        path.join(os.homedir(), 'AppData\\Local\\Google\\Chrome\\Application\\chrome.exe')
    ];
    for (const p of possiblePaths) {
        if (fs.existsSync(p)) {
            executablePath = p;
            break;
        }
    }
} else {
    const linuxPaths = [
        '/usr/bin/google-chrome-stable',
        '/usr/bin/google-chrome',
        '/usr/bin/chromium-browser',
        '/usr/bin/chromium'
    ];
    for (const p of linuxPaths) {
        if (fs.existsSync(p)) {
            executablePath = p;
            break;
        }
    }
}

if (executablePath) {
    console.log(`[WhatsApp Bot] Using browser: ${executablePath}`);
} else {
    console.log('[WhatsApp Bot] No local Chrome found — using Puppeteer bundled Chromium.');
}

// Clean up stale Chrome lock files
const sessionDir = path.join(__dirname, 'whatsapp_session', 'session');
if (fs.existsSync(sessionDir)) {
    const lockFiles = ['SingletonLock', 'SingletonCookie', 'SingletonSocket'];
    lockFiles.forEach(file => {
        const filePath = path.join(sessionDir, file);
        if (fs.existsSync(filePath)) {
            try {
                fs.unlinkSync(filePath);
                console.log(`[WhatsApp Bot] Cleaned stale lock file: ${file}`);
            } catch (err) {
                console.warn(`[WhatsApp Bot] Could not clean lock file ${file}:`, err.message);
            }
        }
    });
}

// Initialize WhatsApp Web Client
const client = new Client({
    authStrategy: new LocalAuth({
        dataPath: './whatsapp_session'
    }),
    puppeteer: {
        headless: true,
        executablePath: executablePath || undefined,
        protocolTimeout: 120000,  // 2 min — give slow VMs time to load WA Web
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-software-rasterizer',
            '--disable-extensions',
            '--disable-default-apps',
            '--disable-background-networking',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-sync',
            '--disable-blink-features=AutomationControlled',
            '--no-first-run',
            '--no-zygote',
            '--single-process',   // critical for Azure VMs
            '--metrics-recording-only',
            '--mute-audio',
            '--hide-scrollbars',
            '--window-size=1280,720',
            '--ignore-certificate-errors',
            '--allow-running-insecure-content',
        ]
    }
});

// ── Event Handlers ──────────────────────────────────────────

client.on('loading_screen', (percent, message) => {
    console.log(`[WhatsApp Bot] Loading: ${percent}% — ${message}`);
});

client.on('qr', async (qr) => {
    console.log('\n[WhatsApp Bot] QR received — generating...');
    const botPhone = process.env.BOT_PHONE;

    if (botPhone) {
        const cleanPhone = botPhone.replace(/\D/g, '');
        console.log(`[WhatsApp Bot] Requesting pairing code for +${cleanPhone}...`);
        try {
            const pairingCode = await client.requestPairingCode(cleanPhone);
            console.log('\n======================================================');
            console.log(`🔑  PAIRING CODE:  ${pairingCode}`);
            console.log('======================================================');
            console.log('1. Open WhatsApp → Linked Devices → Link a Device');
            console.log('2. Tap "Link with phone number instead"');
            console.log('3. Enter the code above\n');
        } catch (err) {
            console.error('[WhatsApp Bot] Pairing code failed, falling back to QR:', err.message);
            qrcode.generate(qr, { small: true });
        }
    } else {
        console.log('\n--- SCAN THIS QR CODE IN WHATSAPP → LINKED DEVICES ---');
        qrcode.generate(qr, { small: true });
        console.log('\n💡 Tip: Set BOT_PHONE=91XXXXXXXXXX to use pairing code instead.\n');
    }
});

client.on('authenticated', () => {
    console.log('[WhatsApp Bot] ✅ Authenticated successfully!');
});

client.on('auth_failure', (msg) => {
    console.error('[WhatsApp Bot] ❌ Authentication failed:', msg);
    console.error('[WhatsApp Bot] Deleting session and restarting in 5s...');
    setTimeout(() => {
        fs.rmSync('./whatsapp_session', { recursive: true, force: true });
        client.initialize();
    }, 5000);
});

client.on('ready', () => {
    console.log('[WhatsApp Bot] ✅ Client is ready and connected!');
});

client.on('disconnected', (reason) => {
    console.warn('[WhatsApp Bot] ⚠️  Disconnected:', reason);
    console.log('[WhatsApp Bot] Attempting to reinitialize in 10s...');
    setTimeout(() => {
        client.initialize();
    }, 10000);
});

// ── Incoming Message Handler ─────────────────────────────────

client.on('message', async (msg) => {
    if (!msg.from.endsWith('@c.us')) return; // ignore groups

    const rawPhone = msg.from.split('@')[0];
    const senderFormatted = `whatsapp:+${rawPhone}`;

    try {
        const contact = await msg.getContact();
        const profileName = contact.pushname || 'WhatsApp User';

        console.log(`[WhatsApp Incoming] ${profileName} (${rawPhone}): ${msg.body}`);

        const params = new URLSearchParams();
        params.append('From', senderFormatted);
        params.append('Body', msg.body);
        params.append('ProfileName', profileName);

        const response = await fetch(`${BACKEND_URL}/api/whatsapp/incoming`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: params
        });

        if (!response.ok) {
            console.error(`[Webhook Error] Status: ${response.status}`);
        }
    } catch (err) {
        console.error('[Webhook Dispatch Error]', err.message);
    }
});

// ── Outbound API ─────────────────────────────────────────────

app.post('/send', async (req, res) => {
    const { phone, message } = req.body;

    if (!phone || !message) {
        return res.status(400).json({ error: 'Missing phone or message' });
    }

    try {
        let cleanPhone = phone.replace(/\D/g, '');
        if (cleanPhone.length === 10) cleanPhone = `91${cleanPhone}`;

        const chatId = `${cleanPhone}@c.us`;
        console.log(`[WhatsApp Outbound] Sending to ${chatId}...`);
        await client.sendMessage(chatId, message);

        res.json({ success: true, message: `Sent to ${cleanPhone}` });
    } catch (err) {
        console.error('[WhatsApp Send Failure]', err.message);
        res.status(500).json({ error: 'Failed to send message', details: err.message });
    }
});

// ── Startup Watchdog ─────────────────────────────────────────

setTimeout(() => {
    console.warn('[WATCHDOG] ⚠️  90s passed with no QR or auth event.');
    console.warn('[WATCHDOG] Check: ps aux | grep chrome && free -h');
}, 90000);

// ── Start ────────────────────────────────────────────────────

app.listen(PORT, () => {
    console.log(`WhatsApp Gateway API listening on port ${PORT}`);
});

client.initialize();