// frontend/src/components/CalendarLegend.tsx
import { motion } from 'framer-motion';
import { SLOT_STATUS } from './calendarStatus';
import type { SlotStatus } from './calendarStatus';

const ORDER: SlotStatus[] = ['available', 'booked', 'not-working'];

export default function CalendarLegend() {
  return (
    <motion.div
      className="flex flex-wrap gap-4 text-xs mb-3 p-3 bg-surface-container-low rounded-lg border border-outline-variant"
      initial={{ opacity: 0, y: -6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      {ORDER.map((key) => {
        const s = SLOT_STATUS[key];
        const Icon = s.icon;
        return (
          <span key={key} className="flex items-center gap-2 font-medium text-on-surface-variant">
            <span className={`inline-flex items-center justify-center w-5 h-5 rounded ${s.swatchClass}`}>
              <Icon className={`${s.textClass} text-[13px]`} />
            </span>
            {s.label}
          </span>
        );
      })}
    </motion.div>
  );
}