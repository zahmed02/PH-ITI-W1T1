import { useState, useEffect } from 'react';
import { getAppointmentsByPatient } from '../api/client';

export default function Appointments() {
  const [patientId, setPatientId] = useState<number>(1);
  const [appointments, setAppointments] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAppointments = async () => {
    if (!patientId || patientId < 1) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getAppointmentsByPatient(patientId);
      setAppointments(data);
    } catch (err) {
      setError('Failed to load appointments. Please check the patient ID.');
      setAppointments([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAppointments();
  }, [patientId]);

  return (
    <div>
      <h1 className="font-headline-lg text-headline-lg mb-2">Patient Appointments</h1>
      <p className="text-on-surface-variant font-body-md mb-8">Search and manage patient medical visits.</p>

      {/* Search */}
      <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 mb-12">
        <label className="block font-label-md text-label-md text-primary mb-4">SEARCH PATIENT RECORDS</label>
        <div className="relative flex flex-col md:flex-row gap-4">
          <input
            type="number"
            min="1"
            value={patientId}
            onChange={(e) => setPatientId(Number(e.target.value))}
            className="flex-1 px-4 py-4 rounded-xl border border-outline-variant focus:border-primary focus:ring-0 outline-none font-body-md bg-surface-bright"
            placeholder="Enter Patient ID (e.g., 1)"
          />
          <button
            onClick={fetchAppointments}
            className="bg-primary text-white px-8 py-4 rounded-xl font-label-md hover:bg-primary-container transition-colors flex items-center justify-center gap-2 active:scale-95"
          >
            <span className="material-symbols-outlined">person_search</span>
            Search Appointments
          </button>
        </div>
        <p className="text-sm text-on-surface-variant mt-2">Valid patient IDs: 1-10</p>
      </div>

      {/* Results */}
      {loading && <p className="text-center">Loading appointments...</p>}
      {error && <p className="text-error text-center">{error}</p>}
      {!loading && !error && appointments.length === 0 && (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <span className="material-symbols-outlined text-6xl text-primary/30 mb-4">event_note</span>
          <h3 className="font-headline-sm text-headline-sm text-on-surface mb-2">No appointments found</h3>
          <p className="text-on-surface-variant max-w-sm">No records for patient ID {patientId}.</p>
        </div>
      )}
      {!loading && !error && appointments.length > 0 && (
        <div className="space-y-4">
          {appointments.map((app) => (
            <div key={app.id} className="bg-surface-container-lowest border border-outline-variant p-5 rounded-xl shadow-sm hover:shadow-md transition-all">
              <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                  <p className="font-headline-sm text-headline-sm text-primary">
                    Dr. {app.doctor?.first_name} {app.doctor?.last_name}
                  </p>
                  <p className="text-on-surface-variant">{app.doctor?.specialty}</p>
                  <p className="text-sm text-on-surface-variant">
                    {new Date(app.appointment_time).toLocaleString()}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`px-3 py-1 rounded-full text-label-sm font-bold ${
                    app.status === 'scheduled' ? 'bg-secondary-container text-on-secondary-container' : 'bg-surface-container text-on-surface-variant'
                  }`}>
                    {app.status}
                  </span>
                  <button className="text-primary hover:text-primary-container font-label-md">Details</button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}