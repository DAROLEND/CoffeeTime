import type { CSSProperties, ElementType, ReactNode } from 'react';
import { useReveal } from '@/hooks/useReveal';

type Props = {
  as?: ElementType;
  className?: string;
  /** Extra class that hides the element until revealed ("reveal", "reveal-left", ...). */
  base?: string;
  delay?: number;
  style?: CSSProperties;
  children?: ReactNode;
};

/** Fades/slides its content in when scrolled into view (animations.css). */
export function Reveal({ as: Tag = 'div', className = '', base = 'reveal', delay = 0, style, children }: Props) {
  const ref = useReveal<HTMLElement>({ delay });
  return (
    <Tag ref={ref} className={`${className} ${base}`.trim()} style={style}>
      {children}
    </Tag>
  );
}
