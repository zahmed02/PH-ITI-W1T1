import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { MdSchedule, MdAccountCircle } from 'react-icons/md';
import { getAppointmentsByDoctor, getDoctorAvailability, getDoctor } from '../api/client';
import { SLOT_STATUS } from './calendarStatus';
import type { SlotStatus } from './calendarStatus';

interface CalendarProps {
  doctorId: number;
  weekStart: Date;
}

export default function Calendar({ doctorId, weekStart }: CalendarProps) {
  const [doctor, setDoctor] = useState<any>(null);
  const [slots, setSlots] = useState<any>({});
  const [loading, setLoading] = useState(true);
  const days = Array.from({ length: 5 }, (_, i) => {
    const d = new Date(weekStart);
    d.setDate(d.getDate() + i);
    return d;
  });
  const timeSlots = Array.from({ length: 10 }, (_, i) => {
    const hour = 8 + i;
    return `${hour}:00`;
  });

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const doc = await getDoctor(doctorId);
        setDoctor(doc);
        const avail = await getDoctorAvailability(doctorId);
        const appts = await getAppointmentsByDoctor(doctorId);

        const occupied: any = {};
        appts.forEach((app: any) => {
          if (app.status === 'cancelled') return;
          const date = new Date(app.appointment_time);
          const dateStr = date.toDateString();
          const hourStr = date.getHours() + ':00';
          if (!occupied[dateStr]) occupied[dateStr] = {};
          occupied[dateStr][hourStr] = { patientName: `${app.patient?.first_name || ''} ${app.patient?.last_name || 'Patient'}`.trim() || 'Patient' };
        });

        const slotMap: any = {};
        days.forEach((day) => {
          const dateStr = day.toDateString();
          const dayOfWeek = day.getDay();
          const working = avail.filter((a: any) => a.day_of_week === dayOfWeek);
          const isWorking = working.length > 0;
          const startHour = isWorking ? parseInt(working[0].start_time.split(':')[0]) : 0;
          const endHour = isWorking ? parseInt(working[0].end_time.split(':')[0]) : 0;

          const daySlots: any = {};
          timeSlots.forEach((hour) => {
            const hourNum = parseInt(hour.split(':')[0]);
            if (!isWorking) {
              daySlots[hour] = { status: 'not-working' as SlotStatus };
            } else if (hourNum < startHour || hourNum >= endHour) {
              daySlots[hour] = { status: 'not-working' as SlotStatus };
            } else if (occupied[dateStr] && occupied[dateStr][hour]) {
              daySlots[hour] = { status: 'booked' as SlotStatus, patientName: occupied[dateStr][hour].patientName };
            } else {
              daySlots[hour] = { status: 'available' as SlotStatus };
            }
          });
          slotMap[dateStr] = daySlots;
        });
        setSlots(slotMap);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [doctorId, weekStart]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16 text-on-surface-variant gap-2">
        <motion.span
          animate={{ rotate: 360 }}
          transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}
          className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full"
        />
        Loading calendar...
      </div>
    );
  }

  return (
    <div>
      {doctor && (
        <motion.div
          className="flex items-center gap-4 mb-4 p-4 bg-white/80 rounded-xl border border-outline-variant shadow-sm"
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <div className="w-16 h-16 rounded-full overflow-hidden border-2 border-primary/20 flex-shrink-0">
            {doctor.profile_image ? (
              <img
                src={doctor.profile_image}
                alt={`Dr. ${doctor.first_name} ${doctor.last_name}`}
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full bg-surface-container flex items-center justify-center">
                <MdAccountCircle className="text-3xl text-primary/40" />
              </div>
            )}
          </div>
          <div>
            <h3 className="font-semibold text-lg text-primary">Dr. {doctor.first_name} {doctor.last_name}</h3>
            <p className="text-sm text-on-surface-variant">{doctor.specialty} • {doctor.years_of_experience} years</p>
          </div>
        </motion.div>
      )}

      <div className="bg-white/90 backdrop-blur-sm rounded-xl border border-outline-variant shadow-lg overflow-hidden">
        {/* Header */}
        <div className="grid grid-cols-6 bg-surface-container border-b border-outline-variant">
          <div className="p-2 text-center border-r border-outline-variant bg-surface-container-high flex items-center justify-center">
            <MdSchedule className="text-outline text-sm" />
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

        {/* Body */}
        <div className="overflow-y-auto max-h-[500px] relative">
          {timeSlots.map((slot, rowIndex) => (
            <motion.div
              key={slot}
              className="grid grid-cols-6 border-b border-outline-variant"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.2, delay: Math.min(rowIndex * 0.02, 0.3) }}
            >
              <div className="flex items-center justify-center border-r border-outline-variant bg-surface-container-low text-on-surface-variant text-xs p-1">
                {slot}
              </div>
              {days.map((day) => {
                const dateStr = day.toDateString();
                const info = slots[dateStr]?.[slot];
                const status: SlotStatus = info?.status || 'not-working';
                const patientName = info?.patientName;
                const s = SLOT_STATUS[status];
                const Icon = s.icon;
                return (
                  <div key={day.toISOString() + slot} className="p-0.5 border-r border-outline-variant">
                    <motion.div
                      className={`flex flex-col items-center justify-center gap-0.5 h-full w-full rounded text-xs p-1 ${s.cellClass} ${s.textClass}`}
                      whileHover={status !== 'not-working' ? { scale: 1.03 } : undefined}
                      transition={{ type: 'spring', stiffness: 400, damping: 20 }}
                    >
                      {status === 'available' && (
                        <>
                          <Icon className="text-sm" />
                          <span className="font-bold text-[10px]">Open</span>
                        </>
                      )}
                      {status === 'booked' && (
                        <>
                          <span className="font-bold truncate w-full text-center leading-tight">{patientName}</span>
                          <span className="text-[9px] opacity-80 flex items-center gap-0.5">
                            <Icon className="text-[10px]" /> Booked
                          </span>
                        </>
                      )}
                      {status === 'not-working' && <Icon className="text-sm opacity-70" />}
                    </motion.div>
                  </div>
                );
              })}
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}