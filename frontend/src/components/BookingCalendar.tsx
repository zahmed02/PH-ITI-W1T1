import { useState, useEffect } from 'react';
import { getDoctorSchedulePreview, getDoctor } from '../api/client';

interface BookingCalendarProps {
  doctorId: number;
  weekStart: Date;
}

interface PreviewSlot {
  time: string; // e.g. "09:00 AM"
  status: 'available' | 'booked';
}

interface PreviewResponse {
  [isoDate: string]: {
    day_name: string;
    slots: PreviewSlot[];
  };
}

function parseHour12(label: string): number {
  // "09:00 AM" -> 9, "02:00 PM" -> 14, "12:00 AM" -> 0, "12:00 PM" -> 12
  const [time, meridiem] = label.split(' ');
  let [hour] = time.split(':').map(Number);
  if (meridiem === 'AM' && hour === 12) hour = 0;
  if (meridiem === 'PM' && hour !== 12) hour += 12;
  return hour;
}

function toISODate(d: Date): string {
  return d.toISOString().split('T')[0];
}

/**
 * The patient-facing "which slots are open" calendar. Deliberately never
 * shows who holds a booked slot - only whether it's available or taken.
 * This is what CalendarPage renders for role="patient"; doctors/admins
 * see the real schedule (with actual patient names) via components/Calendar.tsx
 * instead, which is backed by a different, access-restricted endpoint.
 */
export default function BookingCalendar({ doctorId, weekStart }: BookingCalendarProps) {
  const [doctor, setDoctor] = useState<any>(null);
  const [preview, setPreview] = useState<PreviewResponse>({});
  const [loading, setLoading] = useState(true);

  const days = Array.from({ length: 5 }, (_, i) => {
    const d = new Date(weekStart);
    d.setDate(d.getDate() + i);
    return d;
  });
  const timeSlots = Array.from({ length: 10 }, (_, i) => 8 + i); // 8:00 - 17:00

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const doc = await getDoctor(doctorId);
        setDoctor(doc);
        const data = await getDoctorSchedulePreview(doctorId, toISODate(days[0]));
        setPreview(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [doctorId, weekStart]);

  if (loading) return <div className="text-center py-8">Loading availability...</div>;

  const statusFor = (day: Date, hour: number): 'available' | 'booked' | 'not-working' => {
    const dayData = preview[toISODate(day)];
    if (!dayData || dayData.slots.length === 0) return 'not-working';
    const match = dayData.slots.find((s) => parseHour12(s.time) === hour);
    return match ? match.status : 'not-working';
  };

  const cellStyle = (status: string) => {
    if (status === 'available')
      return 'bg-secondary-container border border-secondary text-on-secondary-container shadow-sm flex flex-col items-center justify-center h-full w-full rounded text-xs cursor-pointer hover:opacity-80 transition-opacity';
    if (status === 'booked')
      return 'bg-tertiary-container/20 border-l-2 border-tertiary flex items-center justify-center h-full w-full rounded text-xs text-on-surface-variant';
    return 'flex items-center justify-center h-full w-full text-on-surface-variant/40 text-xs';
  };

  return (
    <div>
      {doctor && (
        <div className="flex items-center gap-4 mb-4 p-4 bg-white/80 rounded-xl border border-outline-variant shadow-sm">
          <div className="w-16 h-16 rounded-full overflow-hidden border-2 border-primary/20 flex-shrink-0">
            {doctor.profile_image ? (
              <img
                src={doctor.profile_image}
                alt={`Dr. ${doctor.first_name} ${doctor.last_name}`}
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full bg-surface-container flex items-center justify-center">
                <span className="material-symbols-outlined text-3xl text-primary/40">account_circle</span>
              </div>
            )}
          </div>
          <div>
            <h3 className="font-semibold text-lg text-primary">Dr. {doctor.first_name} {doctor.last_name}</h3>
            <p className="text-sm text-on-surface-variant">{doctor.specialty} • {doctor.years_of_experience} years</p>
          </div>
        </div>
      )}

      <div className="bg-white/90 backdrop-blur-sm rounded-xl border border-outline-variant shadow-lg overflow-hidden">
        <div className="grid grid-cols-6 bg-surface-container border-b border-outline-variant">
          <div className="p-2 text-center border-r border-outline-variant bg-surface-container-high">
            <span className="material-symbols-outlined text-outline text-sm">schedule</span>
          </div>
          {days.map((day, i) => (
            <div key={i} className={`p-2 text-center ${i < days.length - 1 ? 'border-r border-outline-variant' : ''}`}>
              <p className="text-xs font-medium text-on-surface-variant uppercase tracking-wider">
                {day.toLocaleDateString('en-US', { weekday: 'short' })}
              </p>
              <p className={`text-lg font-semibold ${day.toDateString() === new Date().toDateString() ? 'text-primary' : 'text-on-surface'}`}>
                {day.getDate()}
              </p>
            </div>
          ))}
        </div>

        <div className="overflow-y-auto max-h-[500px] relative">
          {timeSlots.map((hour) => {
            const label = new Date(2000, 0, 1, hour).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
            return (
              <div key={hour} className="grid grid-cols-6 border-b border-outline-variant">
                <div className="flex items-center justify-center border-r border-outline-variant bg-surface-container-low text-on-surface-variant text-xs p-1">
                  {label}
                </div>
                {days.map((day) => {
                  const status = statusFor(day, hour);
                  return (
                    <div key={day.toISOString() + hour} className={`p-0.5 border-r border-outline-variant`}>
                      <div className={cellStyle(status)}>
                        {status === 'available' && (
                          <>
                            <span className="font-bold">Open</span>
                            <span className="material-symbols-outlined text-xs">add_circle</span>
                          </>
                        )}
                        {status === 'booked' && <span>Booked</span>}
                        {status === 'not-working' && <span>—</span>}
                      </div>
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}