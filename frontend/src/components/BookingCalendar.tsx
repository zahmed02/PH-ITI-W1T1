import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { getDoctorSchedulePreview, getDoctor, bookAppointment } from '../api/client';
import { useAuth } from '../auth/AuthContext';

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

function to24Hour(hour: number): string {
  return `${hour.toString().padStart(2, '0')}:00`;
}

/**
 * The patient-facing "which slots are open" calendar. Deliberately never
 * shows who holds a booked slot - only whether it's available or taken.
 * Clicking an available slot books it DIRECTLY (no AI assistant needed) -
 * the AI chat remains available as an alternative for patients who'd
 * rather just ask in plain language, but this is the manual path.
 */
export default function BookingCalendar({ doctorId, weekStart }: BookingCalendarProps) {
  const { user } = useAuth();
  const [doctor, setDoctor] = useState<any>(null);
  const [preview, setPreview] = useState<PreviewResponse>({});
  const [loading, setLoading] = useState(true);
  const [pendingSlot, setPendingSlot] = useState<{ date: Date; hour: number } | null>(null);
  const [booking, setBooking] = useState(false);
  const [bookingError, setBookingError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const days = Array.from({ length: 5 }, (_, i) => {
    const d = new Date(weekStart);
    d.setDate(d.getDate() + i);
    return d;
  });
  const timeSlots = Array.from({ length: 10 }, (_, i) => 8 + i); // 8:00 - 17:00

  const loadPreview = async () => {
    try {
      const data = await getDoctorSchedulePreview(doctorId, toISODate(days[0]));
      setPreview(data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const doc = await getDoctor(doctorId);
        setDoctor(doc);
        await loadPreview();
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

  const handleSlotClick = (day: Date, hour: number) => {
    if (statusFor(day, hour) !== 'available') return;
    setBookingError(null);
    setPendingSlot({ date: day, hour });
  };

  const confirmBooking = async () => {
    if (!pendingSlot || !user?.patientId) return;
    setBooking(true);
    setBookingError(null);
    try {
      const result = await bookAppointment({
        doctor_id: doctorId,
        patient_id: user.patientId,
        date: toISODate(pendingSlot.date),
        time: to24Hour(pendingSlot.hour),
      });
      if (result.success) {
        setSuccessMessage(
          `Booked with Dr. ${doctor.first_name} ${doctor.last_name} on ${result.date} at ${result.time}. A confirmation email is on its way.`
        );
        setPendingSlot(null);
        await loadPreview(); // reflect the now-booked slot immediately
      } else {
        setBookingError(result.message || 'Could not book that slot.');
      }
    } catch (err: any) {
      setBookingError(err?.response?.data?.detail || 'Could not book that slot. It may have just been taken.');
      await loadPreview(); // someone else may have grabbed it - refresh to show the truth
    } finally {
      setBooking(false);
    }
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

      {successMessage && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-4 p-3 bg-secondary-container text-on-secondary-container rounded-lg text-sm flex items-center justify-between gap-3"
        >
          <span>{successMessage}</span>
          <button onClick={() => setSuccessMessage(null)} className="text-on-secondary-container/70 hover:text-on-secondary-container">
            <span className="material-symbols-outlined text-sm">close</span>
          </button>
        </motion.div>
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
                      <div className={cellStyle(status)} onClick={() => handleSlotClick(day, hour)}>
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

      {/* Booking confirmation */}
      <AnimatePresence>
        {pendingSlot && (
          <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => !booking && setPendingSlot(null)}
          >
            <motion.div
              className="bg-white rounded-xl shadow-lg p-6 max-w-sm w-full"
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="text-lg font-bold text-primary mb-2">Confirm Appointment</h3>
              <p className="text-sm text-on-surface-variant mb-4">
                Book with Dr. {doctor?.first_name} {doctor?.last_name} on{' '}
                <strong>{pendingSlot.date.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}</strong>{' '}
                at <strong>{new Date(2000, 0, 1, pendingSlot.hour).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}</strong>?
              </p>
              {bookingError && <p className="text-sm text-error mb-3">{bookingError}</p>}
              <div className="flex gap-2">
                <button
                  onClick={() => setPendingSlot(null)}
                  disabled={booking}
                  className="flex-1 py-2 rounded-lg border border-outline-variant text-on-surface-variant hover:bg-surface-container-low transition-colors disabled:opacity-60"
                >
                  Cancel
                </button>
                <button
                  onClick={confirmBooking}
                  disabled={booking}
                  className="flex-1 py-2 rounded-lg bg-primary text-white hover:bg-primary/90 transition-colors disabled:opacity-60"
                >
                  {booking ? 'Booking...' : 'Confirm'}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}