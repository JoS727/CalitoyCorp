import html from './index.html';
import { createHandler } from './core.mjs';
export default { fetch: createHandler(html) };
