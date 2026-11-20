import { motion } from "framer-motion";
import { motion as m } from "../../theme/motion";

export type Bar = { key: string; label: string; value: number; color: string; text: string };

/** Horizontal bars on a shared scale, with the value written next to each bar (colour never carries meaning alone). */
export function Bars({ bars, max, caption }: { bars: Bar[]; max: number; caption: string }) {
  return (
    <figure>
      <figcaption className="sr-only">{caption}</figcaption>
      <ul className="space-y-2">
        {bars.map((b, i) => (
          <li key={b.key} className="flex items-center gap-3">
            <span className="w-label shrink-0 text-small text-copy">{b.label}</span>
            <span className="relative h-bar flex-1">
              <motion.span
                className="absolute inset-y-0 left-0 rounded-soft"
                style={{ backgroundColor: b.color }}
                initial={{ width: 0 }}
                animate={{ width: `${Math.max(0.5, (b.value / max) * 100)}%` }}
                transition={{ duration: m.settle, delay: i * m.stagger, ease: m.ease }}
              />
            </span>
            <span className="w-24 shrink-0 text-right text-small font-semibold text-ink">{b.text}</span>
          </li>
        ))}
      </ul>
    </figure>
  );
}
