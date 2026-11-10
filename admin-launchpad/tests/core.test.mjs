import test from 'node:test';
import assert from 'node:assert/strict';
import { createHandler } from '../core.mjs';
const handler = createHandler('<html><script nonce="{{NONCE}}"></script></html>');
const good = { access: { getIdentity: async () => ({ email: 'owner@example.invalid' }) } };
function env(get = async () => ({ generated_at: new Date().toISOString(), repos: [] })) {
  return { ADMIN_ALLOWED_EMAILS: 'owner@example.invalid', INVENTORY: { get } };
}
const req = path => new Request('https://admin.example.invalid' + path);
test('unconfigured deployment fails closed', async () => assert.equal((await handler(req('/'), {}, {})).status, 503));
test('unauthenticated root is not a blank response', async () => { const r = await handler(req('/'), env(), {}); assert.equal(r.status, 401); assert.match(await r.text(), /Sign-in is required/); });
test('unauthenticated API cannot read KV', async () => { let called=false; const r=await handler(req('/api/inventory'),env(async()=>{called=true;}),{}); assert.equal(r.status,401); assert.equal(called,false); });
test('URL keys and spoofed identity headers do not authenticate', async () => { const r=new Request('https://admin.example.invalid/?k=not-a-login',{headers:{'Cf-Access-Authenticated-User-Email':'owner@example.invalid'}}); assert.equal((await handler(r,env(),{})).status,401); });
test('unapproved signed-in identity is rejected', async () => assert.equal((await handler(req('/'),env(),{access:{getIdentity:async()=>({email:'other@example.invalid'})}})).status,403));
test('identity lookup error fails closed', async () => assert.equal((await handler(req('/'),env(),{access:{getIdentity:async()=>{throw Error('bad');}}})).status,401));
test('approved account loads root with nonce and no caching', async () => { const r=await handler(req('/'),env(),good); assert.equal(r.status,200); assert.match(r.headers.get('cache-control'),/no-store/); assert.match(r.headers.get('content-security-policy'),/nonce-/); assert.doesNotMatch(await r.text(),/\{\{NONCE\}\}/); });
test('approved account reads inventory', async () => { const r=await handler(req('/api/inventory'),env(),good); assert.equal(r.status,200); assert.deepEqual((await r.json()).repos,[]); });
test('missing snapshot is explicit', async () => assert.equal((await handler(req('/api/inventory'),env(async()=>null),good)).status,503));
test('storage error is handled', async () => assert.equal((await handler(req('/api/inventory'),env(async()=>{throw Error('failure');}),good)).status,503));
test('unknown path never exposes raw storage', async () => assert.equal((await handler(req('/inventory.json'),env(),good)).status,404));
test('write methods are rejected', async () => assert.equal((await handler(new Request('https://admin.example.invalid/api/inventory',{method:'POST'}),env(),good)).status,405));
test('HEAD has no body', async () => assert.equal(await (await handler(new Request('https://admin.example.invalid/',{method:'HEAD'}),env(),good)).text(),''));
