import { useState } from 'react';
import { sendChatMessage } from '../api/client';

interface Props {
  patientId?: number;
}

export default function ChatInterface({ patientId }: Props) {
  const [messages, setMessages] = useState<{ role: 'user' | 'bot'; text: string }[]>([
    { role: 'bot', text: "Hello! I'm your Stellaris AI Assistant. How can I help you today?" }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const sendMessage = async () => {
    if (!input.trim()) return;
    const userMsg = input;
    setMessages(prev => [...prev, { role: 'user', text: userMsg }]);
    setInput('');
    setLoading(true);

    try {
      const res = await sendChatMessage(userMsg, patientId);
      setMessages(prev => [...prev, { role: 'bot', text: res.response }]);
    } catch {
      setMessages(prev => [...prev, { role: 'bot', text: 'Sorry, an error occurred.' }]);
    } finally {
      setLoading(false);
    }
  };

  const suggestedActions = [
    { icon: 'calendar_add_on', label: 'Book Appointment' },
    { icon: 'schedule', label: 'Check Schedules' },
    { icon: 'info', label: 'General Inquiry' },
  ];

  return (
    <div className="bg-white/90 backdrop-blur-sm rounded-xl border border-outline-variant shadow-sm flex flex-col h-[600px]">
      {/* Header */}
      <div className="bg-surface-container-high px-4 py-3 flex items-center justify-between border-b border-outline-variant">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-full bg-primary flex items-center justify-center text-on-primary">
            <span className="material-symbols-outlined">smart_toy</span>
          </div>
          <div>
            <h2 className="font-semibold text-primary">Stellaris AI Assistant</h2>
            <p className="text-xs text-secondary flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-secondary animate-pulse"></span>
              Clinical Protocol Active
            </p>
          </div>
        </div>
        <button className="p-1 hover:bg-surface-variant rounded-full transition-colors">
          <span className="material-symbols-outlined text-on-surface-variant">more_vert</span>
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex items-start gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}>
            {msg.role === 'bot' && (
              <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center shrink-0">
                <span className="material-symbols-outlined text-on-primary text-sm">smart_toy</span>
              </div>
            )}
            <div className={`max-w-[80%] px-4 py-2 rounded-xl ${
              msg.role === 'user'
                ? 'bg-primary-container text-on-primary rounded-tr-none'
                : 'bg-white border border-outline-variant rounded-tl-none'
            }`}>
              <p className="text-sm">{msg.text}</p>
            </div>
            {msg.role === 'user' && (
              <div className="h-8 w-8 rounded-full bg-surface-container-highest flex items-center justify-center border border-outline-variant">
                <span className="material-symbols-outlined text-on-surface-variant text-sm">person</span>
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="flex items-start gap-3">
            <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center shrink-0">
              <span className="material-symbols-outlined text-on-primary text-sm">smart_toy</span>
            </div>
            <div className="bg-white border border-outline-variant px-4 py-2 rounded-xl rounded-tl-none">
              <p className="text-sm text-on-surface-variant">Thinking...</p>
            </div>
          </div>
        )}
      </div>

      {/* Suggested Actions */}
      <div className="px-4 pb-2 flex flex-wrap gap-2">
        {suggestedActions.map((action, i) => (
          <button
            key={i}
            onClick={() => {
              setInput(action.label);
              setTimeout(sendMessage, 100);
            }}
            className="px-3 py-1.5 bg-surface-container text-primary border border-primary/20 rounded-full text-xs font-medium hover:bg-primary-container hover:text-on-primary transition-all flex items-center gap-1"
          >
            <span className="material-symbols-outlined text-sm">{action.icon}</span>
            {action.label}
          </button>
        ))}
      </div>

      {/* Input */}
      <div className="p-4 bg-white border-t border-outline-variant">
        <div className="flex items-center gap-2 bg-surface-container-low border border-outline-variant rounded-lg px-3 py-1.5 focus-within:ring-2 focus-within:ring-primary/20">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            className="flex-1 bg-transparent border-none focus:ring-0 text-sm placeholder:text-on-surface-variant/50"
            placeholder="Type your inquiry..."
            onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
          />
          <button
            onClick={sendMessage}
            className="bg-primary text-white h-8 w-8 rounded-lg flex items-center justify-center shadow-sm hover:shadow active:scale-95 transition-all"
            disabled={loading}
          >
            <span className="material-symbols-outlined text-sm">send</span>
          </button>
        </div>
        <p className="text-center text-xs text-on-surface-variant mt-1">
          AI may provide general info. For emergencies, call <span className="text-tertiary font-bold">911</span>.
        </p>
      </div>
    </div>
  );
}