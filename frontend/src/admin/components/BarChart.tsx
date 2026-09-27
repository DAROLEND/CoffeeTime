import { useEffect, useRef } from 'react';

const H = 220;
const PAD = { top: 24, right: 16, bottom: 38, left: 40 };

function renderBars(ctx: CanvasRenderingContext2D, W: number, labels: string[], values: number[], max: number) {
  const cW = W - PAD.left - PAD.right;
  const cH = H - PAD.top - PAD.bottom;
  ctx.clearRect(0, 0, W, H);
  ctx.strokeStyle = '#f0e8df';
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const gy = PAD.top + cH - (cH / 4) * i;
    ctx.beginPath();
    ctx.moveTo(PAD.left, gy);
    ctx.lineTo(PAD.left + cW, gy);
    ctx.stroke();
    ctx.fillStyle = '#bbb';
    ctx.font = '10px sans-serif';
    ctx.textAlign = 'right';
    ctx.fillText(String(Math.round((max / 4) * i)), PAD.left - 6, gy + 4);
  }
  const n = labels.length;
  const gap = n > 14 ? 2 : 4;
  const bW = Math.max(3, (cW - gap * (n - 1)) / n);
  for (let j = 0; j < n; j++) {
    const bh = cH * (values[j] / max);
    const bx = PAD.left + j * (bW + gap);
    const by = PAD.top + cH - bh;
    if (bh > 0) {
      const grad = ctx.createLinearGradient(0, by, 0, PAD.top + cH);
      grad.addColorStop(0, '#E8A838');
      grad.addColorStop(0.6, '#D4A853');
      grad.addColorStop(1, 'rgba(212,168,83,0.18)');
      ctx.fillStyle = grad;
      ctx.beginPath();
      if (ctx.roundRect) ctx.roundRect(bx, by, bW, Math.max(bh, 1), [3, 3, 0, 0]);
      else ctx.rect(bx, by, bW, Math.max(bh, 1));
      ctx.fill();
      if (bh > 16 && values[j] > 0) {
        ctx.fillStyle = 'rgba(139,69,19,0.7)';
        ctx.font = 'bold 9px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(String(Math.round(values[j])), bx + bW / 2, by - 3);
      }
    }
    ctx.fillStyle = '#aaa';
    ctx.font = '9px sans-serif';
    ctx.textAlign = 'center';
    const lbl = n > 12 && j % 3 !== 0 ? '' : labels[j];
    ctx.fillText(lbl, bx + bW / 2, H - PAD.bottom + 13);
  }
}

/**
 * The dashboard's hand-drawn bar chart (a straight port of the old canvas
 * code — no chart library). Data changes fade out, then bars grow in.
 */
export function BarChart({ labels, values }: { labels: string[]; values: number[] }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const first = useRef(true);
  const data = useRef({ labels, values });
  data.current = { labels, values };

  const setup = () => {
    const canvas = ref.current;
    if (!canvas?.parentElement) return null;
    canvas.style.width = '1px';
    const par = canvas.parentElement;
    const cs = window.getComputedStyle(par);
    const W = Math.floor(par.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight));
    const dpr = window.devicePixelRatio || 1;
    canvas.width = W * dpr;
    canvas.height = H * dpr;
    canvas.style.width = `${W}px`;
    canvas.style.height = `${H}px`;
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return { ctx, W };
  };

  useEffect(() => {
    const draw = () => {
      const s = setup();
      if (!s) return;
      const { labels: l, values: v } = data.current;
      renderBars(s.ctx, s.W, l, v, Math.max(...v, 0) || 1);
    };
    window.addEventListener('resize', draw);
    return () => window.removeEventListener('resize', draw);
  }, []);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    let raf = 0;
    let timer = 0;
    const max = Math.max(...values, 0) || 1;
    if (first.current) {
      first.current = false;
      const s = setup();
      if (s) renderBars(s.ctx, s.W, labels, values, max);
      return;
    }
    canvas.style.opacity = '0.05';
    timer = window.setTimeout(() => {
      canvas.style.opacity = '1';
      const s = setup();
      if (!s) return;
      const t0 = performance.now();
      const ease = (t: number) => 1 - Math.pow(1 - t, 3);
      const step = (ts: number) => {
        const p = Math.min(1, (ts - t0) / 450);
        renderBars(s.ctx, s.W, labels, values.map((v) => v * ease(p)), max);
        if (p < 1) raf = requestAnimationFrame(step);
      };
      raf = requestAnimationFrame(step);
    }, 130);
    return () => {
      window.clearTimeout(timer);
      cancelAnimationFrame(raf);
    };
  }, [labels, values]);

  return <canvas ref={ref} style={{ display: 'block', transition: 'opacity 0.13s ease' }} />;
}
