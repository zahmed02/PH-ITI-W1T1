import { useState } from 'react';
import ChatInterface from '../components/ChatInterface';

export default function Home() {
  const [patientId, setPatientId] = useState<number | undefined>(1);

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center gap-3 mb-4">
        <h1 className="text-3xl font-bold text-primary">Stellaris AI Assistant</h1>
        <span className="h-2 w-2 rounded-full bg-secondary animate-pulse"></span>
      </div>
      <div className="flex items-center gap-4 mb-6">
        <label className="text-sm font-medium text-on-surface-variant">Patient ID (for booking)</label>
        <input
          type="number"
          value={patientId || ''}
          onChange={(e) => setPatientId(e.target.value ? Number(e.target.value) : undefined)}
          className="border border-outline-variant rounded-lg p-2 w-24 bg-surface-container-lowest"
        />
      </div>
      <ChatInterface patientId={patientId} />
    </div>
  );
}