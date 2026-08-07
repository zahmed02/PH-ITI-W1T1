// frontend/src/pages/AdminPanel.tsx
import { useState, useEffect, useRef } from 'react';
import type { FormEvent } from 'react';
import { motion } from 'framer-motion';
import {
  adminListUsers, adminCreateDoctor, adminCreateAdmin, adminCreatePatient,
} from '../api/auth';
import type { AdminUserRow, CreateDoctorPayload } from '../api/auth';
import {
  adminListPatients, getDoctors, getDoctorSchedulePreview, bookAppointment, uploadDoctorImage,
} from '../api/client';
import type { PatientRow, BookAppointmentResult } from '../api/client';
import { AnimatedButton } from '../components/AnimatedComponents';
import { toLocalISODate, todayLocalISODate, mondayOfLocalWeek } from '../utils/dateUtils';

const SPECIALTIES = ['Cardiology', 'Neurology', 'Pediatrics', 'Orthopedics', 'Dermatology'];
const DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

type Tab = 'users' | 'new-doctor' | 'new-patient' | 'new-admin' | 'book';

export default function AdminPanel() {
  const [users, setUsers] = useState<AdminUserRow[]>([]);
  const [loadingUsers, setLoadingUsers] = useState(true);
  const [tab, setTab] = useState<Tab>('users');

  const loadUsers = async () => {
    setLoadingUsers(true);
    try {
      const data = await adminListUsers();
      setUsers(data);
    } catch {
      // ignore - the table just stays empty, form below still works
    } finally {
      setLoadingUsers(false);
    }
  };

  useEffect(() => { loadUsers(); }, []);

  return (
    <div>
      <h1 className="text-3xl font-bold text-primary mb-1">Admin Panel</h1>
      <p className="text-sm text-on-surface-variant mb-6">
        Full manual control - create any account, book any patient with any doctor, all without the AI assistant.
      </p>

      <div className="flex gap-2 mb-6 border-b border-outline-variant flex-wrap">
        {([
          { key: 'users', label: 'All Users' },
          { key: 'book', label: 'Book Appointment' },
          { key: 'new-patient', label: 'Create Patient Account' },
          { key: 'new-doctor', label: 'Create Doctor Account' },
          { key: 'new-admin', label: 'Create Admin Account' },
        ] as const).map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t.key ? 'border-primary text-primary' : 'border-transparent text-on-surface-variant hover:text-primary'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'users' && <UsersTable users={users} loading={loadingUsers} />}
      {tab === 'book' && <BookAppointmentForm />}
      {tab === 'new-patient' && <CreatePatientForm onCreated={() => { loadUsers(); setTab('users'); }} />}
      {tab === 'new-doctor' && <CreateDoctorForm onCreated={() => { loadUsers(); setTab('users'); }} />}
      {tab === 'new-admin' && <CreateAdminForm onCreated={() => { loadUsers(); setTab('users'); }} />}
    </div>
  );
}

function RoleBadge({ role }: { role: string }) {
  const colors: Record<string, string> = {
    admin: 'bg-tertiary-container text-on-tertiary-container',
    doctor: 'bg-primary-container text-on-primary-container',
    patient: 'bg-secondary-container text-on-secondary-container',
  };
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-bold uppercase ${colors[role] || 'bg-surface-container'}`}>
      {role}
    </span>
  );
}

function UsersTable({ users, loading }: { users: AdminUserRow[]; loading: boolean }) {
  if (loading) return <p className="text-on-surface-variant text-sm">Loading users...</p>;
  if (users.length === 0) return <p className="text-on-surface-variant text-sm">No users found.</p>;

  return (
    <div className="bg-white/90 backdrop-blur-sm rounded-xl border border-outline-variant shadow-sm overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-surface-container-high text-on-surface-variant text-left">
          <tr>
            <th className="px-4 py-3 font-medium">Username</th>
            <th className="px-4 py-3 font-medium">Role</th>
            <th className="px-4 py-3 font-medium">Linked Record</th>
            <th className="px-4 py-3 font-medium">Created</th>
          </tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id} className="border-t border-outline-variant/50">
              <td className="px-4 py-3 font-medium">{u.username}</td>
              <td className="px-4 py-3"><RoleBadge role={u.role} /></td>
              <td className="px-4 py-3 text-on-surface-variant">
                {u.doctor_id ? `Doctor #${u.doctor_id}` : u.patient_id ? `Patient #${u.patient_id}` : '—'}
              </td>
              <td className="px-4 py-3 text-on-surface-variant">
                {new Date(u.created_at).toLocaleDateString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CreateDoctorForm({ onCreated }: { onCreated: () => void }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [specialty, setSpecialty] = useState(SPECIALTIES[0]);
  const [years, setYears] = useState<number>(1);
  const [bio, setBio] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [availability, setAvailability] = useState<{ day_of_week: number; start_time: string; end_time: string }[]>([]);

  const addDefaultAvailability = () => {
    setAvailability([
      { day_of_week: 1, start_time: '09:00', end_time: '17:00' },
      { day_of_week: 2, start_time: '09:00', end_time: '17:00' },
      { day_of_week: 3, start_time: '09:00', end_time: '17:00' },
      { day_of_week: 4, start_time: '09:00', end_time: '17:00' },
      { day_of_week: 5, start_time: '09:00', end_time: '13:00' },
    ]);
  };

  const addBlock = () => {
    setAvailability([...availability, { day_of_week: 1, start_time: '09:00', end_time: '17:00' }]);
  };

  const updateBlock = (index: number, field: string, value: string | number) => {
    const updated = [...availability];
    updated[index] = { ...updated[index], [field]: value };
    setAvailability(updated);
  };

  const removeBlock = (index: number) => {
    setAvailability(availability.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    if (!username.trim() || password.length < 8 || !firstName.trim() || !lastName.trim()) {
      setError('Fill in all required fields (password needs 8+ characters).');
      return;
    }
    setSubmitting(true);
    try {
      const payload: CreateDoctorPayload = {
        username: username.trim(),
        password,
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        specialty,
        years_of_experience: years,
        bio: bio.trim() || undefined,
        availability: availability.length > 0 ? availability : undefined,
      };
      const created = await adminCreateDoctor(payload);

      // If an image was selected, upload it now using the created doctor_id
      if (imageFile && created.doctor_id) {
        try {
          await uploadDoctorImage(created.doctor_id, imageFile);
          setSuccess(`Doctor "${created.username}" created and profile image uploaded successfully.`);
          setImageFile(null);
          if (fileInputRef.current) fileInputRef.current.value = '';
        } catch (imgErr: any) {
          setSuccess(`Doctor "${created.username}" created, but image upload failed: ${imgErr?.response?.data?.detail || 'Unknown error'}`);
        }
      } else {
        setSuccess(`Doctor account "${created.username}" created. Share the username/password with them securely.`);
      }

      // Reset fields (keep availability as is, but optionally clear it)
      setUsername(''); setPassword(''); setFirstName(''); setLastName(''); setBio(''); setYears(1);
      onCreated();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Could not create the account.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <motion.form
      onSubmit={handleSubmit}
      className="bg-white/90 backdrop-blur-sm rounded-xl border border-outline-variant shadow-sm p-6 max-w-3xl space-y-4"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
    >
      {/* Basic fields (unchanged) */}
      <div className="grid grid-cols-2 gap-3">
        <Field label="First Name" value={firstName} onChange={setFirstName} />
        <Field label="Last Name" value={lastName} onChange={setLastName} />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs font-medium text-on-surface-variant block mb-1">Specialty</label>
          <select
            value={specialty}
            onChange={(e) => setSpecialty(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-outline-variant bg-surface-bright text-sm"
          >
            {SPECIALTIES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs font-medium text-on-surface-variant block mb-1">Years of Experience</label>
          <input
            type="number"
            min={0}
            value={years}
            onChange={(e) => setYears(Number(e.target.value))}
            className="w-full px-3 py-2 rounded-lg border border-outline-variant bg-surface-bright text-sm"
          />
        </div>
      </div>
      <div>
        <label className="text-xs font-medium text-on-surface-variant block mb-1">Bio (optional)</label>
        <textarea
          value={bio}
          onChange={(e) => setBio(e.target.value)}
          rows={2}
          className="w-full px-3 py-2 rounded-lg border border-outline-variant bg-surface-bright text-sm"
        />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Username" value={username} onChange={setUsername} />
        <Field label="Temporary Password" value={password} onChange={setPassword} type="password" />
      </div>

      {/* Availability section (unchanged) */}
      <div className="border-t border-outline-variant pt-4">
        <div className="flex justify-between items-center mb-2">
          <label className="text-xs font-medium text-on-surface-variant block">Weekly Availability (optional)</label>
          <div className="flex gap-2">
            <button type="button" onClick={addDefaultAvailability} className="text-xs text-primary hover:underline">
              Set Mon-Fri 9-5
            </button>
            <button type="button" onClick={addBlock} className="text-xs text-primary hover:underline">
              + Add Block
            </button>
          </div>
        </div>
        {availability.length === 0 && (
          <p className="text-xs text-on-surface-variant">No availability set. You can add blocks below.</p>
        )}
        {availability.map((block, index) => (
          <div key={index} className="flex items-center gap-2 mt-2">
            <select
              value={block.day_of_week}
              onChange={(e) => updateBlock(index, 'day_of_week', Number(e.target.value))}
              className="px-2 py-1 rounded border border-outline-variant bg-surface-bright text-sm"
            >
              {DAYS.map((day, i) => (
                <option key={i} value={i}>{day}</option>
              ))}
            </select>
            <input
              type="time"
              value={block.start_time}
              onChange={(e) => updateBlock(index, 'start_time', e.target.value)}
              className="px-2 py-1 rounded border border-outline-variant bg-surface-bright text-sm w-24"
            />
            <span className="text-xs">to</span>
            <input
              type="time"
              value={block.end_time}
              onChange={(e) => updateBlock(index, 'end_time', e.target.value)}
              className="px-2 py-1 rounded border border-outline-variant bg-surface-bright text-sm w-24"
            />
            <button type="button" onClick={() => removeBlock(index)} className="text-error text-xs hover:underline">
              Remove
            </button>
          </div>
        ))}
      </div>

      {/* Image upload section – always enabled */}
      <div className="border-t border-outline-variant pt-4">
        <label className="text-xs font-medium text-on-surface-variant block mb-1">Profile Image (optional)</label>
        <input
          type="file"
          accept="image/*"
          ref={fileInputRef}
          onChange={(e) => setImageFile(e.target.files?.[0] || null)}
          className="text-sm"
        />
        {imageFile && <span className="text-xs text-on-surface-variant ml-2">File selected: {imageFile.name}</span>}
      </div>

      {error && <p className="text-sm text-error">{error}</p>}
      {success && <p className="text-sm text-secondary">{success}</p>}

      <AnimatedButton variant="primary" type="submit" onClick={() => {}} className="w-full" disabled={submitting}>
        {submitting ? 'Creating...' : 'Create Doctor Account'}
      </AnimatedButton>
    </motion.form>
  );
}

function CreatePatientForm({ onCreated }: { onCreated: () => void }) {
  // ... unchanged ...
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    if (!username.trim() || password.length < 8 || !firstName.trim() || !lastName.trim() || !email.trim()) {
      setError('Fill in all required fields (password needs 8+ characters).');
      return;
    }
    setSubmitting(true);
    try {
      const created = await adminCreatePatient({
        username: username.trim(),
        password,
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        email: email.trim(),
        phone: phone.trim() || undefined,
      });
      setSuccess(`Patient account "${created.username}" created (Patient ID ${created.patient_id}). Share the username/password with them securely.`);
      setUsername(''); setPassword(''); setFirstName(''); setLastName(''); setEmail(''); setPhone('');
      onCreated();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Could not create the account.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <motion.form
      onSubmit={handleSubmit}
      className="bg-white/90 backdrop-blur-sm rounded-xl border border-outline-variant shadow-sm p-6 max-w-xl space-y-4"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <p className="text-xs text-on-surface-variant bg-surface-container-low p-3 rounded-lg">
        Creates the patient's record and login account together - useful for booking a walk-in or
        phone patient who doesn't want to self-register.
      </p>
      <div className="grid grid-cols-2 gap-3">
        <Field label="First Name" value={firstName} onChange={setFirstName} />
        <Field label="Last Name" value={lastName} onChange={setLastName} />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Email" value={email} onChange={setEmail} type="email" />
        <Field label="Phone (optional)" value={phone} onChange={setPhone} type="tel" />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Username" value={username} onChange={setUsername} />
        <Field label="Temporary Password" value={password} onChange={setPassword} type="password" />
      </div>

      {error && <p className="text-sm text-error">{error}</p>}
      {success && <p className="text-sm text-secondary">{success}</p>}

      <AnimatedButton variant="primary" type="submit" onClick={() => {}} className="w-full" disabled={submitting}>
        {submitting ? 'Creating...' : 'Create Patient Account'}
      </AnimatedButton>
    </motion.form>
  );
}

function CreateAdminForm({ onCreated }: { onCreated: () => void }) {
  // ... unchanged ...
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    if (!username.trim() || password.length < 8) {
      setError('Username required; password needs 8+ characters.');
      return;
    }
    setSubmitting(true);
    try {
      const created = await adminCreateAdmin({ username: username.trim(), password });
      setSuccess(`Admin account "${created.username}" created. Share the credentials securely.`);
      setUsername(''); setPassword('');
      onCreated();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Could not create the account.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <motion.form
      onSubmit={handleSubmit}
      className="bg-white/90 backdrop-blur-sm rounded-xl border border-outline-variant shadow-sm p-6 max-w-md space-y-4"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <p className="text-xs text-on-surface-variant bg-surface-container-low p-3 rounded-lg">
        New admins have full control over the system - only create accounts for people who should have it.
      </p>
      <Field label="Username" value={username} onChange={setUsername} />
      <Field label="Temporary Password" value={password} onChange={setPassword} type="password" />

      {error && <p className="text-sm text-error">{error}</p>}
      {success && <p className="text-sm text-secondary">{success}</p>}

      <AnimatedButton variant="primary" type="submit" onClick={() => {}} className="w-full" disabled={submitting}>
        {submitting ? 'Creating...' : 'Create Admin Account'}
      </AnimatedButton>
    </motion.form>
  );
}

function BookAppointmentForm() {
  const [patients, setPatients] = useState<PatientRow[]>([]);
  const [doctors, setDoctors] = useState<any[]>([]);
  const [patientId, setPatientId] = useState<number | ''>('');
  const [doctorId, setDoctorId] = useState<number | ''>('');
  const [date, setDate] = useState('');
  const [availableTimes, setAvailableTimes] = useState<string[]>([]);
  const [time, setTime] = useState('');
  const [loadingTimes, setLoadingTimes] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BookAppointmentResult | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    adminListPatients().then(setPatients).catch(() => {});
    getDoctors().then(setDoctors).catch(() => {});
  }, []);

  useEffect(() => {
    const fetchTimes = async () => {
      setAvailableTimes([]);
      setTime('');
      if (!doctorId || !date) return;
      setLoadingTimes(true);
      try {
        const chosen = new Date(date + 'T00:00:00');
        const monday = mondayOfLocalWeek(chosen);
        const weekStart = toLocalISODate(monday);

        const preview = await getDoctorSchedulePreview(Number(doctorId), weekStart);
        const dayData = preview[date];
        const open = (dayData?.slots || [])
          .filter((s: any) => s.status === 'available')
          .map((s: any) => s.time);
        setAvailableTimes(open);
      } catch {
        setAvailableTimes([]);
      } finally {
        setLoadingTimes(false);
      }
    };
    fetchTimes();
  }, [doctorId, date]);

  const to24Hour = (label: string) => {
    const [t, meridiem] = label.split(' ');
    let [hour, minute] = t.split(':').map(Number);
    if (meridiem === 'AM' && hour === 12) hour = 0;
    if (meridiem === 'PM' && hour !== 12) hour += 12;
    return `${hour.toString().padStart(2, '0')}:${minute.toString().padStart(2, '0')}`;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setResult(null);
    if (!patientId || !doctorId || !date || !time) {
      setError('Please select a patient, doctor, date, and time.');
      return;
    }
    setSubmitting(true);
    try {
      const res = await bookAppointment({
        doctor_id: Number(doctorId),
        patient_id: Number(patientId),
        date,
        time: to24Hour(time),
      });
      setResult(res);
      if (res.success) {
        setTime('');
        setAvailableTimes((prev) => prev.filter((t) => t !== time));
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Could not book the appointment.');
    } finally {
      setSubmitting(false);
    }
  };

  const todayISO = todayLocalISODate();

  return (
    <motion.form
      onSubmit={handleSubmit}
      className="bg-white/90 backdrop-blur-sm rounded-xl border border-outline-variant shadow-sm p-6 max-w-xl space-y-4"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div>
        <label className="text-xs font-medium text-on-surface-variant block mb-1">Patient</label>
        <select
          value={patientId}
          onChange={(e) => setPatientId(e.target.value ? Number(e.target.value) : '')}
          className="w-full px-3 py-2 rounded-lg border border-outline-variant bg-surface-bright text-sm"
        >
          <option value="">Choose a patient...</option>
          {patients.map((p) => (
            <option key={p.id} value={p.id}>
              {p.first_name} {p.last_name} ({p.email}) - ID {p.id}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="text-xs font-medium text-on-surface-variant block mb-1">Doctor</label>
        <select
          value={doctorId}
          onChange={(e) => setDoctorId(e.target.value ? Number(e.target.value) : '')}
          className="w-full px-3 py-2 rounded-lg border border-outline-variant bg-surface-bright text-sm"
        >
          <option value="">Choose a doctor...</option>
          {doctors.map((d) => (
            <option key={d.id} value={d.id}>
              Dr. {d.first_name} {d.last_name} - {d.specialty}
            </option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs font-medium text-on-surface-variant block mb-1">Date</label>
          <input
            type="date"
            min={todayISO}
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-outline-variant bg-surface-bright text-sm"
          />
        </div>
        <div>
          <label className="text-xs font-medium text-on-surface-variant block mb-1">Time</label>
          <select
            value={time}
            onChange={(e) => setTime(e.target.value)}
            disabled={!doctorId || !date || loadingTimes}
            className="w-full px-3 py-2 rounded-lg border border-outline-variant bg-surface-bright text-sm disabled:opacity-60"
          >
            <option value="">
              {loadingTimes ? 'Loading...' : !doctorId || !date ? 'Pick doctor + date first' : availableTimes.length === 0 ? 'No open slots' : 'Choose a time...'}
            </option>
            {availableTimes.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
      </div>

      {error && <p className="text-sm text-error">{error}</p>}
      {result && (
        <p className={`text-sm ${result.success ? 'text-secondary' : 'text-error'}`}>
          {result.message}
          {result.success && result.confirmation_email_sent && ' A confirmation email was sent to the patient.'}
        </p>
      )}

      <AnimatedButton variant="primary" type="submit" onClick={() => {}} className="w-full" disabled={submitting}>
        {submitting ? 'Booking...' : 'Book Appointment'}
      </AnimatedButton>
    </motion.form>
  );
}

function Field({
  label, value, onChange, type = 'text',
}: {
  label: string; value: string; onChange: (v: string) => void; type?: string;
}) {
  return (
    <div>
      <label className="text-xs font-medium text-on-surface-variant block mb-1">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 rounded-lg border border-outline-variant bg-surface-bright text-sm"
      />
    </div>
  );
}