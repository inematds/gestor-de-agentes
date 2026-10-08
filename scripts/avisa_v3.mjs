// Envia um aviso de texto ao Nei pelo bot v3 (@inemav3bot), mesmo mecanismo do explicavideos/engine/send_final_v3.mjs.
// Uso: node avisa_v3.mjs <recibo.json> "<texto>"   (não reenvia se o recibo já existir)
import { writeFileSync, existsSync } from 'node:fs';
import { carregarEnv, lerConfig, validarTokenTelegram } from '/home/nmaldaner/projetos/openpcbotv3/dist/config/env.js';
const [receipt, text] = process.argv.slice(2);
if (!receipt || !text) throw new Error('uso: node avisa_v3.mjs <recibo.json> "<texto>"');
if (existsSync(receipt)) { console.log('Aviso já enviado:', receipt); process.exit(0); }
carregarEnv(); const config = lerConfig();
if (!validarTokenTelegram(config.telegramToken).ok || !config.chatPermitido) throw new Error('Invalid bot v3 configuration');
const base = `https://api.telegram.org/bot${config.telegramToken}/`;
const me = await (await fetch(base + 'getMe')).json();
if (!me.ok || me.result.username !== 'inemav3bot') throw new Error('Unexpected bot identity');
const r = await (await fetch(base + 'sendMessage', { method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ chat_id: config.chatPermitido, text, link_preview_options: { is_disabled: true } }) })).json();
if (!r.ok) throw new Error('Telegram delivery HTTP ' + r.error_code);
writeFileSync(receipt, JSON.stringify({ bot: me.result.username, message_id: r.result.message_id, date: r.result.date }, null, 2));
console.log('Aviso entregue no bot v3');
