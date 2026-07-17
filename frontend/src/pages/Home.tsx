import { useState } from 'react';
import ChatInterface from '../components/ChatInterface';

export default function Home() {
  const [patientId, setPatientId] = useState<number | undefined>(1);

  return (
    <div>
      <div className="mb-8">
        <h1 className="font-headline-lg text-headline-lg text-on-surface mb-2">AI Appointment Assistant</h1>
        <p className="text-on-surface-variant font-body-md">Ask me to find or book a doctor for you.</p>
      </div>
      <div className="mb-4 flex items-center gap-4">
        <label className="font-label-md text-primary">Patient ID (for booking)</label>
        <input
          type="number"
          value={patientId || ''}
          onChange={(e) => setPatientId(e.target.value ? Number(e.target.value) : undefined)}
          className="border border-outline-variant rounded-lg p-2 w-24"
        />
      </div>
      <ChatInterface patientId={patientId} />
    </div>
  );
}