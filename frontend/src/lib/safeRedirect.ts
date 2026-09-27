/** Only same-site relative paths are allowed as post-login redirects. */
export function safeRedirect(target: string | null | undefined, fallback = '/'): string {
  if (!target || !target.startsWith('/') || target.startsWith('//') || target.startsWith('/\\')) return fallback;
  return target;
}
