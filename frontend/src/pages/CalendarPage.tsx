// src/pages/CalendarPage.tsx
import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { getDoctors } from '../api/client';
import Calendar from '../components/Calendar';
import { motion } from 'framer-motion';

export default function CalendarPage() {
  const [searchParams] = useSearchParams();
  const initialDoctorId = searchParams.get('doctorId') ? Number(searchParams.get('doctorId')) : null;
  const [doctors, setDoctors] = useState<any[]>([]);
  const [selectedDoctor, setSelectedDoctor] = useState<number | null>(initialDoctorId);
  const [weekStart, setWeekStart] = useState<Date>(() => {
    const now = new Date();
    const day = now.getDay();
    const diff = now.getDate() - day + (day === 0 ? -6 : 1);
    return new Date(now.setDate(diff));
  });

  useEffect(() => {
    getDoctors().then(setDoctors);
  }, []);

  useEffect(() => {
    const id = searchParams.get('doctorId');
    if (id) setSelectedDoctor(Number(id));
  }, [searchParams]);

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

  return (
    <div>
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-6">
        <div>
          <h1 className="text-3xl font-bold text-primary">Doctor Availability</h1>
          <p className="text-sm text-on-surface-variant">View and manage weekly schedules.</p>
        </div>
        <div className="flex items-center gap-2 bg-surface-container-high p-1 rounded-lg border border-outline-variant shadow-sm">
          <button onClick={goToPreviousWeek} className="p-1.5 hover:bg-surface-container-highest rounded transition-colors material-symbols-outlined text-sm">chevron_left</button>
          <span className="px-3 text-sm font-bold text-on-surface">
            {weekStart.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
          </span>
          <button onClick={goToNextWeek} className="p-1.5 hover:bg-surface-container-highest rounded transition-colors material-symbols-outlined text-sm">chevron_right</button>
        </div>
      </div>

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

      {selectedDoctor ? (
        <>
          {/* ✅ LEGEND – Moved ABOVE the calendar */}
          <div className="flex flex-wrap gap-4 text-xs mb-3 p-3 bg-surface-container-low rounded-lg border border-outline-variant">
            <span className="flex items-center gap-2">
              <span className="inline-block w-4 h-4 bg-secondary-container border border-secondary rounded"></span>
              Available
            </span>
            <span className="flex items-center gap-2">
              <span className="inline-block w-4 h-4 bg-tertiary-container/20 border-l-2 border-tertiary rounded"></span>
              Booked
            </span>
            <span className="flex items-center gap-2">
              <span className="inline-block w-4 h-4 bg-surface-container-highest/50 border border-outline-variant rounded"></span>
              Not Working
            </span>
          </div>

          <Calendar doctorId={selectedDoctor} weekStart={weekStart} />

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
            {[
              { icon: 'event_available', label: 'Available Slots', color: 'bg-secondary-container' },
              { icon: 'patient_list', label: 'Pending Approvals', color: 'bg-tertiary-container/20' },
              { icon: 'assignment', label: 'Lab Results', color: 'bg-primary-container/20' },
            ].map((stat, i) => (
              <motion.div
                key={i}
                className="bg-white/90 backdrop-blur-sm p-4 rounded-xl border border-outline-variant shadow-sm flex items-center gap-3"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 + i * 0.05 }}
                whileHover={{
                  y: -4,
                  boxShadow: '0 12px 40px rgba(0,0,0,0.08)',
                  transition: { type: 'spring', stiffness: 300, damping: 15 },
                }}
              >
                <div className={`h-10 w-10 rounded-full ${stat.color} flex items-center justify-center text-on-secondary-container`}>
                  <span className="material-symbols-outlined">{stat.icon}</span>
                </div>
                <div>
                  <p className="text-xs text-on-surface-variant">{stat.label}</p>
                  <p className="text-lg font-semibold">--</p>
                </div>
              </motion.div>
            ))}
          </div>
        </>
      ) : (
        <div className="text-center py-12 text-on-surface-variant">Please select a doctor to view their availability.</div>
      )}
    </div>
  );
}