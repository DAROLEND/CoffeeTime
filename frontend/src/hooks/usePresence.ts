import { useEffect, useState } from 'react';

/**
 * Keeps a closing element mounted for its exit animation. `open` drives
 * it; returns whether to render and whether it's playing the exit.
 */
export function usePresence(open: boolean, exitMs = 360) {
  const [mounted, setMounted] = useState(open);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (open) {
      setMounted(true);
      // Next frame, so the "open" transition actually runs.
      const raf = requestAnimationFrame(() => requestAnimationFrame(() => setVisible(true)));
      return () => cancelAnimationFrame(raf);
    }
    setVisible(false);
    const t = window.setTimeout(() => setMounted(false), exitMs);
    return () => window.clearTimeout(t);
  }, [open, exitMs]);

  return { mounted, visible, closing: mounted && !open };
}
