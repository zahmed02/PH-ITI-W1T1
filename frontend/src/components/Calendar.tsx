import { useState, useEffect } from 'react';
import { getAppointmentsByDoctor, getDoctorAvailability, getDoctor } from '../api/client';

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
              daySlots[hour] = { status: 'not-working' };
            } else if (hourNum < startHour || hourNum >= endHour) {
              daySlots[hour] = { status: 'off-duty' };
            } else if (occupied[dateStr] && occupied[dateStr][hour]) {
              daySlots[hour] = { status: 'occupied', patientName: occupied[dateStr][hour].patientName };
            } else {
              daySlots[hour] = { status: 'available' };
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
  }, [doctorId, weekStart]);

  if (loading) return <div className="text-center py-8">Loading calendar...</div>;

  const getCellContent = (status: string, patientName?: string) => {
    if (status === 'available') return 'A';
    if (status === 'not-working' || status === 'off-duty') return 'NW';
    if (status === 'occupied') return patientName || 'Booked';
    return '';
  };

  const getCellClass = (status: string) => {
    switch (status) {
      case 'available': return 'bg-secondary-container/10 group cursor-pointer hover:bg-secondary-container/20 transition-all';
      case 'occupied': return 'bg-tertiary-container/10 border-l-2 border-tertiary';
      case 'not-working':
      case 'off-duty': return 'bg-surface-container-highest/20';
      default: return '';
    }
  };

  const getCellStyle = (status: string) => {
    if (status === 'available') return 'bg-secondary-container border border-secondary text-on-secondary-container shadow-sm flex flex-col justify-between p-1 h-full w-full rounded text-xs';
    if (status === 'occupied') return 'flex flex-col justify-center p-1 h-full w-full rounded text-xs text-on-surface';
    if (status === 'not-working' || status === 'off-duty') return 'flex items-center justify-center h-full w-full text-on-surface-variant/50 text-xs';
    return '';
  };

  return (
    <div>
      {/* ✅ Doctor Image & Info */}
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
        {/* Header */}
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

        {/* Body */}
        <div className="overflow-y-auto max-h-[500px] relative">
          {timeSlots.map((slot) => (
            <div key={slot} className="grid grid-cols-6 border-b border-outline-variant">
              <div className="flex items-center justify-center border-r border-outline-variant bg-surface-container-low text-on-surface-variant text-xs p-1">
                {slot}
              </div>
              {days.map((day) => {
                const dateStr = day.toDateString();
                const info = slots[dateStr]?.[slot];
                const status = info?.status || 'not-working';
                const patientName = info?.patientName;
                const content = getCellContent(status, patientName);
                const cellClass = getCellClass(status);
                const cellStyle = getCellStyle(status);
                return (
                  <div key={day.toISOString() + slot} className={`p-0.5 border-r border-outline-variant ${cellClass}`}>
                    <div className={cellStyle}>
                      {status === 'available' && (
                        <>
                          <span className="font-bold">A</span>
                          <span className="material-symbols-outlined text-xs">add_circle</span>
                        </>
                      )}
                      {status === 'occupied' && (
                        <>
                          <span className="font-bold text-tertiary truncate">{patientName}</span>
                          <span className="text-[8px] opacity-60">Booked</span>
                        </>
                      )}
                      {(status === 'not-working' || status === 'off-duty') && (
                        <span className="font-bold">NW</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}