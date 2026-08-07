// src/pages/CalendarPage.tsx
import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { MdChevronLeft, MdChevronRight, MdEventBusy, MdEventAvailable, MdAssignment, MdGroups } from 'react-icons/md';
import { getDoctors, setDoctorDayOff, listDoctorDaysOff } from '../api/client';
import Calendar from '../components/Calendar';
import BookingCalendar from '../components/BookingCalendar';
import CalendarLegend from '../components/CalendarLegend';
import { useAuth } from '../auth/AuthContext';
import { todayLocalISODate } from '../utils/dateUtils';

export default function CalendarPage() {
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const initialDoctorId = searchParams.get('doctorId') ? Number(searchParams.get('doctorId')) : null;

  // Doctors are locked to their OWN schedule - no picker, and they see
  // the real view (with actual patient names) since it's their own data.
  const isDoctorLockedToSelf = user?.role === 'doctor';
  const lockedDoctorId = isDoctorLockedToSelf ? user?.doctorId ?? null : null;

  const [doctors, setDoctors] = useState<any[]>([]);
  const [selectedDoctor, setSelectedDoctor] = useState<number | null>(lockedDoctorId ?? initialDoctorId);
  const [weekStart, setWeekStart] = useState<Date>(() => {
    const now = new Date();
    const day = now.getDay();
    const diff = now.getDate() - day + (day === 0 ? -6 : 1);
    return new Date(now.setDate(diff));
  });
  const [refreshKey, setRefreshKey] = useState(0);

  // Day-off dialog state (doctor only)
  const [dayOffOpen, setDayOffOpen] = useState(false);
  const [dayOffDate, setDayOffDate] = useState('');
  const [dayOffReason, setDayOffReason] = useState('');
  const [dayOffSubmitting, setDayOffSubmitting] = useState(false);
  const [dayOffMessage, setDayOffMessage] = useState<string | null>(null);
  const [upcomingDaysOff, setUpcomingDaysOff] = useState<{ date: string; reason: string | null }[]>([]);

  useEffect(() => {
    if (!isDoctorLockedToSelf) {
      getDoctors().then(setDoctors);
    }
  }, [isDoctorLockedToSelf]);

  useEffect(() => {
    if (isDoctorLockedToSelf) return; // ignore ?doctorId= for doctors - always their own
    const id = searchParams.get('doctorId');
    if (id) setSelectedDoctor(Number(id));
  }, [searchParams, isDoctorLockedToSelf]);

  useEffect(() => {
    if (lockedDoctorId) {
      listDoctorDaysOff(lockedDoctorId).then(setUpcomingDaysOff).catch(() => {});
    }
  }, [lockedDoctorId, refreshKey]);

  const goToPreviousWeek = () => {
    const newDate = new Date(weekStart);
    newDate.setDate(newDate.getDate() - 7);
    setWeekStart(newDate);
  };

  const goToNextWeek = () => {
    const newDate = new Date(weekStart);
    newDate.setDate(newDate.getDate() + 7);
    setWeekStart(newDate);
  };

  const pageTitle = user?.role === 'doctor' ? 'My Schedule' : user?.role === 'patient' ? 'Book an Appointment' : 'Doctor Availability';
  const pageSubtitle =
    user?.role === 'doctor'
      ? 'Your weekly schedule, including which patients are booked.'
      : user?.role === 'patient'
      ? 'Pick a doctor and an open slot to request an appointment.'
      : 'View and manage weekly schedules.';

  // Admins/doctors see the REAL calendar (actual patient names on booked
  // slots) since GET /appointments/doctor/{id} is restricted server-side
  // to the doctor themselves or an admin. Patients get the privacy-safe
  // free/busy view instead - they should never see another patient's name.
  const showRealCalendar = user?.role === 'doctor' || user?.role === 'admin';

  const submitDayOff = async () => {
    if (!lockedDoctorId || !dayOffDate) return;
    setDayOffSubmitting(true);
    setDayOffMessage(null);
    try {
      const result = await setDoctorDayOff(lockedDoctorId, dayOffDate, dayOffReason || undefined);
      setDayOffMessage(result.message);
      setDayOffDate('');
      setDayOffReason('');
      setRefreshKey((k) => k + 1); // refresh the calendar grid + days-off list
    } catch (err: any) {
      setDayOffMessage(err?.response?.data?.detail || 'Could not set that day off.');
    } finally {
      setDayOffSubmitting(false);
    }
  };

  const todayISO = todayLocalISODate();

  return (
    <div>
      <motion.div
        className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-6"
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <div>
          <h1 className="text-3xl font-bold text-primary">{pageTitle}</h1>
          <p className="text-sm text-on-surface-variant">{pageSubtitle}</p>
        </div>
        <div className="flex items-center gap-3">
          {isDoctorLockedToSelf && (
            <motion.button
              onClick={() => setDayOffOpen(true)}
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
              className="px-3 py-1.5 rounded-lg border border-outline-variant text-sm hover:bg-surface-container-low flex items-center gap-1.5"
            >
              <MdEventBusy className="text-sm" />
              Take a Day Off
            </motion.button>
          )}
          <div className="flex items-center gap-2 bg-surface-container-high p-1 rounded-lg border border-outline-variant shadow-sm">
            <button onClick={goToPreviousWeek} className="p-1.5 hover:bg-surface-container-highest rounded transition-colors flex items-center justify-center">
              <MdChevronLeft className="text-sm" />
            </button>
            <span className="px-3 text-sm font-bold text-on-surface">
              {weekStart.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
            </span>
            <button onClick={goToNextWeek} className="p-1.5 hover:bg-surface-container-highest rounded transition-colors flex items-center justify-center">
              <MdChevronRight className="text-sm" />
            </button>
          </div>
        </div>
      </motion.div>

      {isDoctorLockedToSelf && upcomingDaysOff.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="mb-4 p-3 bg-surface-container-low rounded-lg border border-outline-variant text-xs text-on-surface-variant"
        >
          <span className="font-medium text-primary">Upcoming days off:</span>{' '}
          {upcomingDaysOff.map((d) => d.date).join(', ')}
        </motion.div>
      )}

      {!isDoctorLockedToSelf && (
        <div className="flex flex-wrap items-center gap-4 mb-6">
          <div>
            <label className="block text-xs font-medium text-on-surface-variant">Select Doctor</label>
            <select
              value={selectedDoctor || ''}
              onChange={(e) => setSelectedDoctor(Number(e.target.value))}
              className="border border-outline-variant rounded-lg p-1.5 text-sm bg-surface"
            >
              <option value="">Choose a doctor...</option>
              {doctors.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  Dr. {doc.first_name} {doc.last_name} – {doc.specialty}
                </option>
              ))}
            </select>
          </div>
        </div>
      )}

      {selectedDoctor ? (
        <>
          <CalendarLegend />

          {showRealCalendar ? (
            <Calendar key={refreshKey} doctorId={selectedDoctor} weekStart={weekStart} />
          ) : (
            <BookingCalendar key={refreshKey} doctorId={selectedDoctor} weekStart={weekStart} />
          )}

          {showRealCalendar && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
              {[
                { Icon: MdEventAvailable, label: 'Available Slots', bg: 'bg-secondary-container', fg: 'text-on-secondary-container' },
                { Icon: MdGroups, label: 'Pending Approvals', bg: 'bg-tertiary-container/25', fg: 'text-tertiary' },
                { Icon: MdAssignment, label: 'Lab Results', bg: 'bg-primary-container/20', fg: 'text-primary' },
              ].map((stat, i) => (
                <motion.div
                  key={i}
                  className="bg-white/90 backdrop-blur-sm p-4 rounded-xl border border-outline-variant shadow-sm flex items-center gap-3"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 + i * 0.05 }}
                  whileHover={{
                    y: -4,
                    boxShadow: '0 12px 40px rgba(140,0,33,0.10)',
                    transition: { type: 'spring', stiffness: 300, damping: 15 },
                  }}
                >
                  <div className={`h-10 w-10 rounded-full ${stat.bg} flex items-center justify-center ${stat.fg}`}>
                    <stat.Icon className="text-xl" />
                  </div>
                  <div>
                    <p className="text-xs text-on-surface-variant">{stat.label}</p>
                    <p className="text-lg font-semibold">--</p>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </>
      ) : (
        <div className="text-center py-12 text-on-surface-variant">
          {isDoctorLockedToSelf
            ? 'Your schedule will appear here once an admin links your account to a doctor profile.'
            : 'Please select a doctor to view their availability.'}
        </div>
      )}

      {/* Day off dialog */}
      <AnimatePresence>
        {dayOffOpen && (
          <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => !dayOffSubmitting && setDayOffOpen(false)}
          >
            <motion.div
              className="bg-white rounded-xl shadow-lg p-6 max-w-sm w-full"
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="text-lg font-bold text-primary mb-2 flex items-center gap-2">
                <MdEventBusy /> Take a Day Off
              </h3>
              <p className="text-sm text-on-surface-variant mb-4">
                Any existing appointments on that date will be cancelled automatically and each patient will be emailed.
              </p>
              <div className="space-y-3">
                <div>
                  <label className="text-xs font-medium text-on-surface-variant block mb-1">Date</label>
                  <input
                    type="date"
                    min={todayISO}
                    value={dayOffDate}
                    onChange={(e) => setDayOffDate(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-outline-variant bg-surface-bright text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-on-surface-variant block mb-1">Reason (optional)</label>
                  <input
                    type="text"
                    value={dayOffReason}
                    onChange={(e) => setDayOffReason(e.target.value)}
                    placeholder="e.g. Personal leave"
                    className="w-full px-3 py-2 rounded-lg border border-outline-variant bg-surface-bright text-sm"
                  />
                </div>
              </div>
              {dayOffMessage && <p className="text-sm text-secondary mt-3">{dayOffMessage}</p>}
              <div className="flex gap-2 mt-4">
                <button
                  onClick={() => setDayOffOpen(false)}
                  disabled={dayOffSubmitting}
                  className="flex-1 py-2 rounded-lg border border-outline-variant text-on-surface-variant hover:bg-surface-container-low disabled:opacity-60"
                >
                  Close
                </button>
                <motion.button
                  onClick={submitDayOff}
                  disabled={dayOffSubmitting || !dayOffDate}
                  whileHover={!dayOffSubmitting && dayOffDate ? { scale: 1.02 } : undefined}
                  whileTap={!dayOffSubmitting && dayOffDate ? { scale: 0.97 } : undefined}
                  className="flex-1 py-2 rounded-lg bg-primary text-white hover:bg-primary/90 disabled:opacity-60"
                >
                  {dayOffSubmitting ? 'Saving...' : 'Confirm'}
                </motion.button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}