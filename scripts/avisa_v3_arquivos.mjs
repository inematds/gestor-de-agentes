// Envia ao Nei pelo bot v3 (@inemav3bot) uma imagem com legenda e, opcionalmente, um documento (ex.: roteiro.md).
// Uso: node avisa_v3_arquivos.mjs <recibo.json> <imagem.jpg> "<legenda ≤1024>" [documento]   (não reenvia se o recibo existir)
import { writeFileSync, existsSync, readFileSync } from 'node:fs';
import { basename } from 'node:path';
import { carregarEnv, lerConfig, validarTokenTelegram } from '/home/nmaldaner/projetos/openpcbotv3/dist/config/env.js';
const [receipt, img, caption, doc] = process.argv.slice(2);
if (!receipt || !img || !caption) throw new Error('uso: node avisa_v3_arquivos.mjs <recibo.json> <imagem> "<legenda>" [documento]');
if (existsSync(receipt)) { console.log('Aviso já enviado:', receipt); process.exit(0); }
carregarEnv(); const config = lerConfig();
if (!validarTokenTelegram(config.telegramToken).ok || !config.chatPermitido) throw new Error('Invalid bot v3 configuration');
const base = `https://api.telegram.org/bot${config.telegramToken}/`;
const me = await (await fetch(base + 'getMe')).json();
if (!me.ok || me.result.username !== 'inemav3bot') throw new Error('Unexpected bot identity');
const envia = async (metodo, campo, arq, extra) => {
  const f = new FormData(); f.append('chat_id', String(config.chatPermitido));
  for (const [k, v] of Object.entries(extra)) f.append(k, v);
  f.append(campo, new Blob([readFileSync(arq)]), basename(arq));
  const r = await (await fetch(base + metodo, { method: 'POST', body: f })).json();
  if (!r.ok) throw new Error(metodo + ' HTTP ' + r.error_code); return r.result.message_id;
};
const ids = [await envia('sendPhoto', 'photo', img, { caption })];
if (doc) ids.push(await envia('sendDocument', 'document', doc, {}));
writeFileSync(receipt, JSON.stringify({ bot: me.result.username, message_ids: ids }, null, 2));
console.log('Entregue no bot v3', ids.length);
