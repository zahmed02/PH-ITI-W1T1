import { useState } from 'react';
import ChatInterface from '../components/ChatInterface';
import { useAuth } from '../auth/AuthContext';

export default function Home() {
  const { user } = useAuth();
  // Only relevant for admins acting on a patient's behalf - a patient's
  // own identity is resolved server-side from their login token, and any
  // patient_id sent from here is IGNORED for patient accounts (see
  // backend/chat_router.py::_resolve_acting_patient_id). Showing this
  // field to patients would be actively misleading, since typing a
  // different number here would silently do nothing.
  const [adminTargetPatientId, setAdminTargetPatientId] = useState<number | undefined>(undefined);

  const effectivePatientId = user?.role === 'admin' ? adminTargetPatientId : user?.patientId ?? undefined;

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center gap-3 mb-4">
        <h1 className="text-3xl font-bold text-primary">Stellaris AI Assistant</h1>
        <span className="h-2 w-2 rounded-full bg-secondary animate-pulse"></span>
      </div>

      {user?.role === 'admin' && (
        <div className="flex items-center gap-4 mb-6">
          <label className="text-sm font-medium text-on-surface-variant">Assisting Patient ID</label>
          <input
            type="number"
            value={adminTargetPatientId ?? ''}
            onChange={(e) => setAdminTargetPatientId(e.target.value ? Number(e.target.value) : undefined)}
            className="border border-outline-variant rounded-lg p-2 w-24 bg-surface-container-lowest"
            placeholder="e.g. 3"
          />
        </div>
      )}

      <ChatInterface patientId={effectivePatientId} />
    </div>
  );
}