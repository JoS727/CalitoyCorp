/** No Static Assets binding: Access context must reach this Worker directly. */
const headers = {
  'Cache-Control': 'private, no-store, max-age=0',
  'Referrer-Policy': 'no-referrer',
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'Vary': 'Cookie',
};
function response(body, status = 200, type = 'application/json; charset=utf-8', extra = {}) {
  return new Response(body, { status, headers: { ...headers, 'Content-Type': type, ...extra } });
}
function error(status, message, api) {
  if (api) return response(JSON.stringify({ error: message }), status);
  return response(`<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Calitoy Admin - Access</title><body style="margin:0;background:#101018;color:#f5f2fb;font:18px system-ui;padding:10vw"><p style="color:#d5b475">CALITOY / PRIVATE ADMIN</p><h1>${message}</h1><p>The master app dashboard is private. Its Cloudflare Access sign-in and approved account must be configured before it can open.</p><p>No access key belongs in the address bar.</p></body></html>`, status, 'text/html; charset=utf-8');
}
export function createHandler(html) {
  return async function handle(request, env, ctx) {
    const path = new URL(request.url).pathname;
    const api = path.startsWith('/api/');
    const allowed = new Set(String(env.ADMIN_ALLOWED_EMAILS || '').split(',').map(s => s.trim().toLowerCase()).filter(Boolean));
    if (!allowed.size || !env.INVENTORY) return error(503, 'Admin setup is incomplete', api);
    // A request header or ?k= value is NOT proof of authentication.
    if (!ctx?.access || typeof ctx.access.getIdentity !== 'function') return error(401, 'Sign-in is required', api);
    let identity;
    try { identity = await ctx.access.getIdentity(); }
    catch { return error(401, 'Your sign-in could not be verified', api); }
    if (!allowed.has(String(identity?.email || '').toLowerCase())) return error(403, 'This account is not approved', api);
    if (!['GET', 'HEAD'].includes(request.method)) return response('', 405, 'text/plain', { Allow: 'GET, HEAD' });
    if (path === '/api/inventory') {
      try {
        const data = await env.INVENTORY.get('inventory:latest', 'json');
        if (!data || !Array.isArray(data.repos) || !Number.isFinite(Date.parse(data.generated_at))) {
          return error(503, 'The first private inventory sync has not completed', true);
        }
        return response(request.method === 'HEAD' ? null : JSON.stringify(data));
      } catch { return error(503, 'Private inventory is temporarily unavailable', true); }
    }
    if (!['/', '/index.html'].includes(path)) return response('Not found', 404, 'text/plain; charset=utf-8');
    const nonce = crypto.randomUUID();
    const csp = `default-src 'none'; script-src 'nonce-${nonce}'; style-src 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; base-uri 'none'; object-src 'none'; frame-ancestors 'none'; form-action 'none'`;
    return response(request.method === 'HEAD' ? null : html.replaceAll('{{NONCE}}', nonce), 200, 'text/html; charset=utf-8', { 'Content-Security-Policy': csp });
  };
}
