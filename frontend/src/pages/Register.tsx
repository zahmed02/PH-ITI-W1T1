// frontend/src/pages/Register.tsx
import { useState } from 'react';
import type { FormEvent } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import BackgroundSlideshow from '../components/BackgroundSlideshow';

export default function Register() {
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [showWelcome, setShowWelcome] = useState(false);

  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!firstName.trim() || !lastName.trim() || !email.trim()) {
      setError('Please fill in your name and email.');
      return;
    }
    if (!username.trim() || !password) {
      setError('Please choose a username and password.');
      return;
    }
    if (username.trim().length < 3) {
      setError('Username must be at least 3 characters.');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      // Registering as a patient also creates the linked Patient record,
      // so once logged in, "my appointments" etc. resolve automatically -
      // no more manually typing a patient ID anywhere in the app.
      await register({
        username: username.trim(),
        password,
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        email: email.trim(),
        phone: phone.trim() || undefined,
      });
      setShowWelcome(true);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Could not create your account. Please try again.');
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen relative flex items-center justify-center overflow-hidden px-4 py-8">
      <BackgroundSlideshow />

      <motion.div
        className="relative z-10 w-full max-w-md bg-white/90 backdrop-blur-sm rounded-2xl border border-outline-variant shadow-lg p-8"
        initial={{ opacity: 0, y: 24, scale: 0.97 }}
        animate={{ opacity: showWelcome ? 0 : 1, y: 0, scale: 1 }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
      >
        <div className="flex flex-col items-center mb-6">
          <img src="/images/logo.png" alt="Stellaris General Hospital" className="h-14 w-14 mb-3 object-contain" />
          <h1 className="text-2xl font-bold text-primary text-center">Create Your Account</h1>
          <p className="text-sm text-on-surface-variant">Join the Stellaris patient portal</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-on-surface-variant block mb-1">First Name</label>
              <input
                type="text"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                className="w-full px-4 py-2.5 rounded-lg border border-outline-variant focus:border-primary focus:ring-1 focus:ring-primary outline-none bg-surface-bright"
                placeholder="Jane"
                autoComplete="given-name"
                disabled={submitting}
              />
            </div>
            <div>
              <label className="text-xs font-medium text-on-surface-variant block mb-1">Last Name</label>
              <input
                type="text"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                className="w-full px-4 py-2.5 rounded-lg border border-outline-variant focus:border-primary focus:ring-1 focus:ring-primary outline-none bg-surface-bright"
                placeholder="Doe"
                autoComplete="family-name"
                disabled={submitting}
              />
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-on-surface-variant block mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg border border-outline-variant focus:border-primary focus:ring-1 focus:ring-primary outline-none bg-surface-bright"
              placeholder="you@example.com"
              autoComplete="email"
              disabled={submitting}
            />
            <p className="text-xs text-on-surface-variant/70 mt-1">Appointment confirmations will be sent here.</p>
          </div>

          <div>
            <label className="text-xs font-medium text-on-surface-variant block mb-1">Phone (optional)</label>
            <input
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg border border-outline-variant focus:border-primary focus:ring-1 focus:ring-primary outline-none bg-surface-bright"
              placeholder="555-0100"
              autoComplete="tel"
              disabled={submitting}
            />
          </div>

          <div>
            <label className="text-xs font-medium text-on-surface-variant block mb-1">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg border border-outline-variant focus:border-primary focus:ring-1 focus:ring-primary outline-none bg-surface-bright"
              placeholder="Choose a username"
              autoComplete="username"
              disabled={submitting}
            />
          </div>
          <div>
            <label className="text-xs font-medium text-on-surface-variant block mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg border border-outline-variant focus:border-primary focus:ring-1 focus:ring-primary outline-none bg-surface-bright"
              placeholder="At least 8 characters"
              autoComplete="new-password"
              disabled={submitting}
            />
          </div>
          <div>
            <label className="text-xs font-medium text-on-surface-variant block mb-1">Confirm Password</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg border border-outline-variant focus:border-primary focus:ring-1 focus:ring-primary outline-none bg-surface-bright"
              placeholder="Re-enter your password"
              autoComplete="new-password"
              disabled={submitting}
            />
          </div>

          {error && <p className="text-sm text-error">{error}</p>}

          <motion.button
            type="submit"
            disabled={submitting}
            className="w-full bg-primary text-white py-2.5 rounded-lg font-medium hover:bg-primary/90 transition-colors disabled:opacity-60"
            whileHover={{ scale: submitting ? 1 : 1.02 }}
            whileTap={{ scale: submitting ? 1 : 0.97 }}
          >
            {submitting ? 'Creating account...' : 'Register'}
          </motion.button>
        </form>

        <p className="text-center text-sm text-on-surface-variant mt-6">
          Already have an account?{' '}
          <Link to="/login" className="text-primary font-medium hover:underline">
            Sign In
          </Link>
        </p>
      </motion.div>

      <AnimatePresence>
        {showWelcome && (
          <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center bg-primary"
            initial={{ clipPath: 'circle(0% at 50% 50%)' }}
            animate={{ clipPath: 'circle(150% at 50% 50%)' }}
            transition={{ duration: 0.9, ease: 'easeInOut' }}
            onAnimationComplete={() => navigate('/', { replace: true })}
          >
            <motion.div
              className="text-center text-white px-6"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.25, duration: 0.4 }}
            >
              <span className="material-symbols-outlined text-6xl mb-3" style={{ fontVariationSettings: "'FILL' 1" }}>
                celebration
              </span>
              <h2 className="text-2xl font-bold">Welcome to Stellaris, {firstName}!</h2>
              <p className="text-white/80 mt-1">Setting up your portal...</p>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}