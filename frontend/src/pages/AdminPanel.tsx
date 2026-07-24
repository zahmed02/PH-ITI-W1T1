// frontend/src/pages/AdminPanel.tsx
import { useState, useEffect } from 'react';
import type { FormEvent } from 'react';
import { motion } from 'framer-motion';
import {
  adminListUsers, adminCreateDoctor, adminCreateAdmin,
} from '../api/auth';
import type { AdminUserRow } from '../api/auth';
import { AnimatedButton } from '../components/AnimatedComponents';

const SPECIALTIES = ['Cardiology', 'Neurology', 'Pediatrics', 'Orthopedics', 'Dermatology'];

export default function AdminPanel() {
  const [users, setUsers] = useState<AdminUserRow[]>([]);
  const [loadingUsers, setLoadingUsers] = useState(true);
  const [tab, setTab] = useState<'users' | 'new-doctor' | 'new-admin'>('users');

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
        Manage every login account in the system - patients, doctors, and admins.
      </p>

      <div className="flex gap-2 mb-6 border-b border-outline-variant">
        {([
          { key: 'users', label: 'All Users' },
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
      const created = await adminCreateDoctor({
        username: username.trim(),
        password,
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        specialty,
        years_of_experience: years,
        bio: bio.trim() || undefined,
      });
      setSuccess(`Doctor account "${created.username}" created. Share the username/password with them securely.`);
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
      className="bg-white/90 backdrop-blur-sm rounded-xl border border-outline-variant shadow-sm p-6 max-w-xl space-y-4"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
    >
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

      {error && <p className="text-sm text-error">{error}</p>}
      {success && <p className="text-sm text-secondary">{success}</p>}

      <AnimatedButton variant="primary" type="submit" onClick={() => {}} className="w-full" disabled={submitting}>
        {submitting ? 'Creating...' : 'Create Doctor Account'}
      </AnimatedButton>
    </motion.form>
  );
}

function CreateAdminForm({ onCreated }: { onCreated: () => void }) {
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