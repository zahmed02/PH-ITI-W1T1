import { useState } from 'react';
import { sendChatMessage } from '../api/client';

interface Props {
  patientId?: number;
}

export default function ChatInterface({ patientId }: Props) {
  const [messages, setMessages] = useState<{ role: 'user' | 'bot'; text: string }[]>([
    { role: 'bot', text: "Hello! I'm your MedCare Assistant. How can I help you today?" }
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
    } catch (err) {
      setMessages(prev => [...prev, { role: 'bot', text: 'Sorry, an error occurred.' }]);
    } finally {
      setLoading(false);
    }
  };

  const suggestedActions = [
    { icon: 'calendar_month', label: "Find a cardiologist for tomorrow" },
    { icon: 'favorite', label: "Book appointment for cardiology" },
    { icon: 'description', label: "Show my medical records" },
  ];

  return (
    <div className="bg-surface-container-lowest border border-outline-variant rounded-xl shadow-sm p-4">
      <div className="h-96 overflow-y-auto mb-4 space-y-4" id="chat-history">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex gap-4 max-w-[85%] ${msg.role === 'user' ? 'ml-auto flex-row-reverse' : ''}`}
          >
            <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center shadow-sm ${msg.role === 'user' ? 'bg-primary text-white' : 'bg-secondary-container text-on-secondary-container'}`}>
              <span className="material-symbols-outlined">
                {msg.role === 'user' ? 'person' : 'smart_toy'}
              </span>
            </div>
            <div className="space-y-2">
              <div className={`p-4 rounded-2xl ${msg.role === 'user' ? 'bg-primary text-white rounded-tr-none' : 'bg-surface-container-low border border-outline-variant/20 rounded-tl-none'}`}>
                <p className="text-body-md">{msg.text}</p>
              </div>
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex gap-4 max-w-[85%]">
            <div className="flex-shrink-0 w-10 h-10 rounded-full bg-secondary-container flex items-center justify-center shadow-sm">
              <span className="material-symbols-outlined text-on-secondary-container">smart_toy</span>
            </div>
            <div className="p-4 bg-surface-container-low border border-outline-variant/20 rounded-2xl rounded-tl-none">
              <p className="text-body-md text-on-surface-variant">Thinking...</p>
            </div>
          </div>
        )}
      </div>

      {/* Suggested Actions */}
      <div className="flex flex-wrap gap-2 mb-4">
        {suggestedActions.map((action, i) => (
          <button
            key={i}
            onClick={() => {
              setInput(action.label);
              // Auto-send after a small delay for UX
              setTimeout(() => sendMessage(), 100);
            }}
            className="px-4 py-2 bg-surface-container-high hover:bg-surface-variant text-on-surface-variant text-label-md rounded-full border border-outline-variant/30 transition-all flex items-center gap-2 active:scale-95"
          >
            <span className="material-symbols-outlined text-[18px]">{action.icon}</span>
            {action.label}
          </button>
        ))}
      </div>

      {/* Input Area */}
      <div className="relative bg-surface border border-outline-variant rounded-full shadow-lg flex items-center p-1.5 focus-within:ring-2 focus-within:ring-primary/20">
        <button className="p-3 text-on-surface-variant hover:text-primary transition-colors">
          <span className="material-symbols-outlined">attach_file</span>
        </button>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          className="flex-1 bg-transparent border-none focus:ring-0 px-4 text-body-md placeholder:text-on-surface-variant/60 outline-none"
          placeholder="Ask anything about doctors or appointments..."
          onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
        />
        <button
          onClick={sendMessage}
          className="bg-primary text-white w-12 h-12 rounded-full flex items-center justify-center shadow-md active:scale-90 transition-transform"
          disabled={loading}
        >
          <span className="material-symbols-outlined">send</span>
        </button>
      </div>
      <p className="text-center text-[10px] text-on-surface-variant mt-3 uppercase tracking-widest font-bold">Encrypted & HIPAA Compliant</p>
    </div>
  );
}