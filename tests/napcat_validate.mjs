// 用 NapCat 上游 typebox schema（loadConfig）校验生成的 onebot11 配置
import { build } from 'esbuild';
import fs from 'fs';
const [,, tsPath, jsonPath] = process.argv;
const out = tsPath + '.mjs';
await build({ entryPoints: [tsPath], outfile: out, format: 'esm', bundle: true, platform: 'node', logLevel: 'silent' });
const { loadConfig, OneBotConfigSchema } = await import(out);
const { Value } = await import('@sinclair/typebox/value');
const raw = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
const parsed = loadConfig(structuredClone(raw));
if (!Value.Check(OneBotConfigSchema, raw)) { console.error('raw config not strictly valid'); process.exit(2); }
console.log(JSON.stringify(parsed.network.websocketClients[0]));
