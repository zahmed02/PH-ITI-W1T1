// frontend/src/pages/AppointmentSlips.tsx
import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '../auth/AuthContext';
import {
  getDoctorSlips, fetchSlipPdfBlob, cancelAppointment, proposeTransfer,
  getIncomingTransfers, confirmTransfer, declineTransfer, getDoctors, getDoctor,
} from '../api/client';
import type { AppointmentSlipRow, IncomingTransfer } from '../api/client';

export default function AppointmentSlips() {
  const { user } = useAuth();
  const doctorId = user?.doctorId ?? null;

  const [slips, setSlips] = useState<AppointmentSlipRow[]>([]);
  const [incoming, setIncoming] = useState<IncomingTransfer[]>([]);
  const [loading, setLoading] = useState(true);
  const [pdfLoading, setPdfLoading] = useState<number | null>(null);
  const [transferTarget, setTransferTarget] = useState<AppointmentSlipRow | null>(null);
  const [colleagues, setColleagues] = useState<any[] | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  const load = useCallback(async () => {
    if (!doctorId) return;
    setLoading(true);
    try {
      const [slipsData, incomingData] = await Promise.all([
        getDoctorSlips(doctorId, true),
        getIncomingTransfers(),
      ]);
      setSlips(slipsData);
      setIncoming(incomingData);
    } finally {
      setLoading(false);
    }
  }, [doctorId]);

  useEffect(() => { load(); }, [load]);

  if (!doctorId) {
    return (
      <div className="text-center py-12 text-on-surface-variant">
        Your account isn't linked to a doctor record yet. Contact an admin.
      </div>
    );
  }

  const viewSlip = async (appointmentId: number) => {
    setPdfLoading(appointmentId);
    try {
      const url = await fetchSlipPdfBlob(appointmentId);
      // Open in a new tab so the browser's own full PDF viewer handles
      // zoom/scroll/print/download - an embedded iframe was rendering
      // the A5 slip tiny and unreadable with no reliable way to zoom.
      const win = window.open(url, '_blank');
      if (!win) {
        setActionMessage('Your browser blocked the popup - please allow popups for this site, or check your downloads.');
      }
      // Revoke after a delay long enough for the new tab to load it.
      setTimeout(() => URL.revokeObjectURL(url), 30_000);
    } catch {
      setActionMessage('Could not load that appointment slip.');
    } finally {
      setPdfLoading(null);
    }
  };

  const handleCancel = async (slip: AppointmentSlipRow) => {
    if (!confirm(`Cancel ${slip.patient_name}'s appointment? They'll be emailed automatically.`)) return;
    setBusyId(slip.id);
    try {
      const result = await cancelAppointment(slip.id);
      await load();
      // Immediately offer to transfer, rather than requiring the doctor
      // to notice the "Transfer" button appear on the now-cancelled row.
      if (confirm(`${result.message}\n\nTransfer this patient to another doctor now?`)) {
        openTransferDialog(slip);
      } else {
        setActionMessage(result.message);
      }
    } catch (err: any) {
      setActionMessage(err?.response?.data?.detail || 'Could not cancel that appointment.');
    } finally {
      setBusyId(null);
    }
  };

  const openTransferDialog = async (slip: AppointmentSlipRow) => {
    setTransferTarget(slip);
    setColleagues(null); // null = still loading, [] = loaded but empty
    try {
      const me = await getDoctor(doctorId);
      const all = await getDoctors({ specialty: me.specialty });
      // Belt-and-suspenders: also filter client-side in case the search
      // endpoint ever does a fuzzy/partial specialty match instead of exact.
      setColleagues(all.filter((d: any) => d.id !== doctorId && d.specialty === me.specialty));
    } catch {
      setColleagues([]);
    }
  };

  const handleTransfer = async (toDoctorId: number) => {
    if (!transferTarget) return;
    setBusyId(transferTarget.id);
    try {
      const result = await proposeTransfer(transferTarget.id, toDoctorId);
      setActionMessage(result.message);
      setTransferTarget(null);
      await load();
    } catch (err: any) {
      setActionMessage(err?.response?.data?.detail || 'Could not propose that transfer.');
    } finally {
      setBusyId(null);
    }
  };

  const handleConfirmTransfer = async (transferId: number) => {
    setBusyId(transferId);
    try {
      const result = await confirmTransfer(transferId);
      setActionMessage(result.message);
      await load();
    } catch (err: any) {
      setActionMessage(err?.response?.data?.detail || 'Could not confirm that transfer.');
    } finally {
      setBusyId(null);
    }
  };

  const handleDeclineTransfer = async (transferId: number) => {
    setBusyId(transferId);
    try {
      const result = await declineTransfer(transferId);
      setActionMessage(result.message);
      await load();
    } catch (err: any) {
      setActionMessage(err?.response?.data?.detail || 'Could not decline that transfer.');
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div>
      <h1 className="text-3xl font-bold text-primary mb-1">Appointment Slips</h1>
      <p className="text-sm text-on-surface-variant mb-6">
        View the same PDF slip your patients received, cancel a visit, or transfer a cancelled patient to a colleague.
      </p>

      {actionMessage && (
        <div className="mb-4 p-3 bg-secondary-container text-on-secondary-container rounded-lg text-sm flex items-center justify-between">
          <span>{actionMessage}</span>
          <button onClick={() => setActionMessage(null)} className="text-on-secondary-container/70">
            <span className="material-symbols-outlined text-sm">close</span>
          </button>
        </div>
      )}

      {incoming.length > 0 && (
        <div className="mb-8">
          <h2 className="text-lg font-semibold text-primary mb-3">Incoming Transfer Requests</h2>
          <div className="space-y-2">
            {incoming.map((t) => (
              <div key={t.id} className="bg-primary-container/20 border border-primary/30 rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-medium">
                    {t.from_doctor_name} wants to transfer <strong>{t.patient_name}</strong> to you
                  </p>
                  <p className="text-xs text-on-surface-variant">
                    {new Date(t.appointment_time).toLocaleString('en-US', { weekday: 'long', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleDeclineTransfer(t.id)}
                    disabled={busyId === t.id}
                    className="px-3 py-1.5 rounded-lg border border-outline-variant text-sm hover:bg-surface-container-low disabled:opacity-60"
                  >
                    Decline
                  </button>
                  <button
                    onClick={() => handleConfirmTransfer(t.id)}
                    disabled={busyId === t.id}
                    className="px-3 py-1.5 rounded-lg bg-primary text-white text-sm hover:bg-primary/90 disabled:opacity-60"
                  >
                    {busyId === t.id ? 'Confirming...' : "Confirm - I'll take them"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <h2 className="text-lg font-semibold text-primary mb-3">Your Upcoming Appointments</h2>
      {loading ? (
        <p className="text-on-surface-variant text-sm">Loading...</p>
      ) : slips.length === 0 ? (
        <p className="text-on-surface-variant text-sm">No upcoming appointments.</p>
      ) : (
        <div className="bg-white/90 backdrop-blur-sm rounded-xl border border-outline-variant shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-surface-container-high text-on-surface-variant text-left">
              <tr>
                <th className="px-4 py-3 font-medium">Appointment ID</th>
                <th className="px-4 py-3 font-medium">Patient</th>
                <th className="px-4 py-3 font-medium">When</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {slips.map((slip) => (
                <tr key={slip.id} className="border-t border-outline-variant/50">
                  <td className="px-4 py-3 font-mono text-xs">{slip.display_appointment_id}</td>
                  <td className="px-4 py-3 font-medium">{slip.patient_name}</td>
                  <td className="px-4 py-3 text-on-surface-variant">
                    {new Date(slip.appointment_time).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-bold uppercase ${
                      slip.status === 'cancelled' ? 'bg-tertiary-container text-on-tertiary-container' : 'bg-secondary-container text-on-secondary-container'
                    }`}>
                      {slip.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2 flex-wrap">
                      <button
                        onClick={() => viewSlip(slip.id)}
                        disabled={pdfLoading === slip.id}
                        className="px-2.5 py-1 rounded-lg border border-outline-variant text-xs hover:bg-surface-container-low disabled:opacity-60 flex items-center gap-1"
                      >
                        {pdfLoading === slip.id ? (
                          'Loading...'
                        ) : (
                          <>
                            View PDF
                            <span className="material-symbols-outlined text-[13px]">open_in_new</span>
                          </>
                        )}
                      </button>
                      {slip.status === 'scheduled' && (
                        <button
                          onClick={() => handleCancel(slip)}
                          disabled={busyId === slip.id}
                          className="px-2.5 py-1 rounded-lg border border-error text-error text-xs hover:bg-error/10 disabled:opacity-60"
                        >
                          Cancel
                        </button>
                      )}
                      {slip.status === 'cancelled' && (
                        <button
                          onClick={() => openTransferDialog(slip)}
                          className="px-2.5 py-1 rounded-lg border border-primary text-primary text-xs hover:bg-primary/10"
                        >
                          Transfer
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Transfer dialog */}
      <AnimatePresence>
        {transferTarget && (
          <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setTransferTarget(null)}
          >
            <motion.div
              className="bg-white rounded-xl shadow-lg p-6 max-w-sm w-full"
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="text-lg font-bold text-primary mb-1">Transfer Patient</h3>
              <p className="text-sm text-on-surface-variant mb-4">
                Send {transferTarget.patient_name}'s cancelled appointment to a colleague in the same department. They'll need to manually confirm.
              </p>
<div className="space-y-1 max-h-64 overflow-y-auto">
  {colleagues === null ? (
    <p className="text-sm text-on-surface-variant">Loading colleagues...</p>
  ) : colleagues.length === 0 ? (
    <p className="text-sm text-on-surface-variant">No colleagues with the same specialty available.</p>
  ) : (
    colleagues.map((doc) => (
      <button
        key={doc.id}
        onClick={() => handleTransfer(doc.id)}
        disabled={busyId === transferTarget.id}
        className="w-full text-left px-3 py-2 rounded-lg border border-outline-variant hover:bg-surface-container-low disabled:opacity-60 text-sm"
      >
        Dr. {doc.first_name} {doc.last_name} <span className="text-on-surface-variant">- {doc.specialty}</span>
      </button>
    ))
  )}
</div>
              <button
                onClick={() => setTransferTarget(null)}
                className="mt-4 w-full py-2 rounded-lg border border-outline-variant text-on-surface-variant hover:bg-surface-container-low text-sm"
              >
                Cancel
              </button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}