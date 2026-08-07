// frontend/src/utils/dateUtils.ts

/**
 * Converts a Date to a "YYYY-MM-DD" string using its LOCAL calendar date
 * (year/month/day as displayed on the user's own clock) - never via
 * .toISOString(), which converts to UTC first.
 *
 * WHY THIS EXISTS:
 * `date.toISOString().split('T')[0]` looks like an innocent way to get
 * "today's date as a string", but it silently shifts the date backward
 * by one day for anyone in a timezone ahead of UTC (which includes
 * Pakistan, UTC+5) whenever the Date's time-of-day is early enough that
 * converting to UTC crosses midnight. A Date built at exactly local
 * midnight (e.g. `new Date(dateString + 'T00:00:00')`, as used when
 * turning a native <input type="date"> value back into a Date) crosses
 * that boundary EVERY time, with no exceptions - this is what caused the
 * admin booking form's week calculation to be reliably one day off.
 *
 * Use this function everywhere a Date needs to become a "YYYY-MM-DD"
 * string for the API (week_start params, date params, min= bounds on
 * date inputs, etc). Never use .toISOString().split('T')[0] for that
 * purpose - reserve toISOString() for actual UTC timestamps.
 */
export function toLocalISODate(d: Date): string {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

/** Today's date as a local "YYYY-MM-DD" string - for use as a date input's min= bound, etc. */
export function todayLocalISODate(): string {
  return toLocalISODate(new Date());
}

/**
 * Given any Date, returns the Date for the Monday of that same local
 * week (time-of-day preserved, so it's still safe to pass through
 * toLocalISODate afterward without a second conversion).
 */
export function mondayOfLocalWeek(d: Date): Date {
  const monday = new Date(d);
  const day = monday.getDay(); // 0=Sunday..6=Saturday
  const diff = (day + 6) % 7; // days to subtract to reach Monday
  monday.setDate(monday.getDate() - diff);
  return monday;
}