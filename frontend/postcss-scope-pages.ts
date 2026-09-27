/**
 * PostCSS plugin: scope every stylesheet under `src/styles/pages/<page>/`
 * to a `.pg-<page>` wrapper element.
 *
 * Why: the page stylesheets came over unchanged from the server-rendered
 * site, where each page loaded only its own CSS. In a SPA, Vite injects
 * a route's CSS when the route first loads and never removes it, so after
 * visiting /menu and then /cart both menu.css and cart-edit.css would be
 * active, and they define the same class names (`.item-modal`, ...).
 * Prefixing every selector with the page's wrapper class restores the
 * one-page-one-stylesheet behaviour without rewriting 11k lines of CSS.
 *
 * `:root`, `html` and `body` selectors map onto the wrapper itself, so
 * page-level CSS variables and backgrounds still apply. Keyframes are
 * left alone.
 */
import type { AtRule, Plugin, Rule } from 'postcss';

const PAGE_FILE = /[\\/]styles[\\/]pages[\\/]([\w-]+)[\\/][^\\/]+\.css$/;

export function scopeSelector(selector: string, scope: string): string {
  const sel = selector.trim();
  if (!sel || sel.startsWith(scope)) return sel;
  // `:root`, `html`, `body`, `html body` -> the wrapper itself
  if (/^(:root|html|body|html\s+body)$/.test(sel)) return scope;
  // `body.tab-settings .x` / `html .x` / `body > .x` -> hang it off the wrapper
  const rootMatch = sel.match(/^(?::root|html|body)((?:[.#:[][^\s>+~]*)?)(.*)$/);
  if (rootMatch) return `${scope}${rootMatch[1]}${rootMatch[2]}`;
  return `${scope} ${sel}`;
}

function insideKeyframes(rule: Rule): boolean {
  let parent: Rule['parent'] | undefined = rule.parent;
  while (parent) {
    if (parent.type === 'atrule' && /keyframes$/i.test((parent as AtRule).name)) return true;
    parent = (parent as { parent?: Rule['parent'] }).parent;
  }
  return false;
}

export default function scopePages(): Plugin {
  return {
    postcssPlugin: 'coffeetime-scope-pages',
    Once(root) {
      const file = root.source?.input.file ?? '';
      const match = file.match(PAGE_FILE);
      if (!match) return;
      const scope = `.pg-${match[1]}`;
      root.walkRules((rule) => {
        if (insideKeyframes(rule)) return;
        rule.selectors = rule.selectors.map((s) => scopeSelector(s, scope));
      });
    },
  };
}
scopePages.postcss = true;
