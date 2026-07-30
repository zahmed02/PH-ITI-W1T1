// frontend/src/components/calendarStatus.ts
import { MdCheckCircle, MdEventBusy, MdBlock } from 'react-icons/md';
import type { IconType } from 'react-icons';

export type SlotStatus = 'available' | 'booked' | 'not-working';

interface StatusStyle {
  label: string;
  icon: IconType;
  /** Cell background + border - deliberately solid/opaque, not a faint tint,
   *  so the three states are unmistakable from each other and from plain
   *  white at a glance. */
  cellClass: string;
  /** Text/icon color on top of cellClass. */
  textClass: string;
  /** Small swatch used in the legend - same classes as the cell, so the
   *  legend can never visually drift from what's actually in the grid. */
  swatchClass: string;
}

// Three genuinely distinct treatments, not just opacity variants of one
// color: available = solid rose fill, booked = solid terracotta fill with
// a strong left border, not-working = flat neutral with a diagonal-hatch
// texture. Each also carries a distinct icon, so the meaning doesn't rely
// on color alone (colorblind-safe).
export const SLOT_STATUS: Record<SlotStatus, StatusStyle> = {
  available: {
    label: 'Available',
    icon: MdCheckCircle,
    cellClass: 'bg-secondary-container border border-secondary',
    textClass: 'text-on-secondary-container',
    swatchClass: 'bg-secondary-container border border-secondary',
  },
  booked: {
    label: 'Booked',
    icon: MdEventBusy,
    cellClass: 'bg-tertiary-container border-l-[3px] border-tertiary',
    textClass: 'text-on-tertiary-container',
    swatchClass: 'bg-tertiary-container border-l-[3px] border-tertiary',
  },
  'not-working': {
    label: 'Not working',
    icon: MdBlock,
    cellClass: 'bg-surface-container-highest bg-diagonal-hatch border border-outline-variant',
    textClass: 'text-on-surface-variant',
    swatchClass: 'bg-surface-container-highest bg-diagonal-hatch border border-outline-variant',
  },
};