// src/components/Layout.tsx
import { NavLink, useLocation, useOutlet, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import BackgroundSlideshow from './BackgroundSlideshow';
import { useAuth } from '../auth/AuthContext';

// Page transition variants – smooth transform
const pageVariants = {
  initial: { opacity: 0, y: 15, scale: 0.97 },
  animate: { opacity: 1, y: 0, scale: 1 },
  exit: { opacity: 0, y: -15, scale: 0.97 },
};

const pageTransition = {
  duration: 0.35,
  ease: 'easeInOut' as const,
};

export default function Layout() {
  const location = useLocation();
  const outlet = useOutlet(); // Get the current outlet element
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    // Not strictly required - ProtectedRoute will redirect on its own once
    // `isAuthenticated` flips to false - but navigating explicitly avoids
    // a flash of the current protected page before the redirect kicks in.
    navigate('/login', { replace: true });
  };

  return (
    <div className="min-h-screen relative overflow-hidden">
      <BackgroundSlideshow />

      {/* ===== HEADER ===== */}
      <motion.header
        className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between h-16 px-6 bg-surface/80 backdrop-blur-md border-b border-outline-variant shadow-sm"
        initial={{ y: -60, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ type: 'spring', stiffness: 120, damping: 15, delay: 0.1 }}
      >
        <div className="flex items-center gap-3">
          <motion.img
            src="/images/logo.png"
            alt="Stellaris Hospital"
            className="h-10 w-10 object-contain"
            whileHover={{ rotate: 8, scale: 1.05 }}
            transition={{ type: 'spring', stiffness: 300 }}
          />
          <span className="text-lg font-bold text-primary hidden sm:block">Stellaris General Hospital</span>
        </div>
        <nav className="hidden md:flex items-center gap-6">
          {[
            { path: '/', label: 'AI Assistant' },
            { path: '/doctors', label: 'Find a Doctor' },
            { path: '/calendar', label: 'Schedule' },
          ].map((item, i) => (
            <motion.div
              key={item.path}
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 + i * 0.05 }}
            >
              <NavLink
                to={item.path}
                className={({ isActive }) =>
                  `text-sm font-medium transition-all duration-200 ${
                    isActive
                      ? 'text-primary border-b-2 border-primary pb-1'
                      : 'text-on-surface-variant hover:text-primary hover:scale-105'
                  }`
                }
              >
                {item.label}
              </NavLink>
            </motion.div>
          ))}
        </nav>
        <div className="flex items-center gap-3">
          <motion.span
            className="material-symbols-outlined text-on-surface-variant cursor-pointer"
            whileHover={{ scale: 1.2, rotate: 10, color: '#00478d' }}
            transition={{ type: 'spring', stiffness: 300 }}
          >
            notifications
          </motion.span>

          {/* Account / logout */}
          <div className="flex items-center gap-2">
            {user && (
              <span className="hidden sm:block text-sm text-on-surface-variant">
                {user.username}
              </span>
            )}
            <motion.button
              onClick={handleLogout}
              title="Log out"
              className="material-symbols-outlined text-on-surface-variant cursor-pointer"
              whileHover={{ scale: 1.2, rotate: -10, color: '#00478d' }}
              transition={{ type: 'spring', stiffness: 300 }}
            >
              logout
            </motion.button>
          </div>
        </div>
      </motion.header>

      {/* ===== SIDEBAR ===== */}
      <motion.aside
        className="hidden lg:flex flex-col w-64 fixed left-0 top-16 bottom-0 bg-surface-container-low/80 backdrop-blur-sm border-r border-outline-variant p-4 space-y-1 overflow-y-auto"
        initial={{ x: -80, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ type: 'spring', stiffness: 100, damping: 15, delay: 0.15 }}
      >
        <div className="mb-4 px-2">
          <p className="text-lg font-black text-primary">Stellaris General</p>
          <p className="text-xs text-on-surface-variant">Medical Portal</p>
        </div>
        <nav className="flex-1 space-y-1">
          {[
            { to: '/', label: 'AI Assistant', icon: 'smart_toy' },
            { to: '/doctors', label: 'Specialists', icon: 'medical_services' },
            { to: '/calendar', label: 'Calendar', icon: 'calendar_month' },
          ].map((item, i) => (
            <motion.div
              key={item.to}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.15 + i * 0.05 }}
            >
              <NavLink
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-4 py-2.5 rounded-lg transition-all duration-200 ${
                    isActive
                      ? 'bg-primary-container text-on-primary-container font-bold shadow-sm'
                      : 'text-on-surface-variant hover:bg-surface-container-high hover:scale-105'
                  }`
                }
              >
                <motion.span
                  className="material-symbols-outlined"
                  whileHover={{ rotate: 15, scale: 1.1 }}
                  transition={{ type: 'spring', stiffness: 300 }}
                >
                  {item.icon}
                </motion.span>
                <span>{item.label}</span>
              </NavLink>
            </motion.div>
          ))}
        </nav>
        <div className="pt-4 border-t border-outline-variant space-y-1">
          <motion.button
            className="w-full bg-tertiary text-on-tertiary py-2 rounded-lg font-bold"
            whileHover={{ scale: 1.03, boxShadow: '0 8px 25px rgba(148,0,24,0.3)' }}
            whileTap={{ scale: 0.95 }}
            transition={{ type: 'spring', stiffness: 400, damping: 10 }}
          >
            Emergency Call
          </motion.button>
          {['Settings', 'Support'].map((label) => (
            <NavLink
              key={label}
              to="#"
              className="flex items-center gap-3 px-4 py-2.5 rounded-lg text-on-surface-variant hover:bg-surface-container-high transition-all duration-200"
            >
              <span className="material-symbols-outlined">
                {label === 'Settings' ? 'settings' : 'contact_support'}
              </span>
              <span>{label}</span>
            </NavLink>
          ))}
        </div>
      </motion.aside>

      {/* ===== MAIN CONTENT ===== */}
      <motion.main
        className="lg:ml-64 pt-20 px-4 md:px-8 pb-8 max-w-7xl mx-auto"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.2 }}
      >
        <div className="bg-white/70 backdrop-blur-sm rounded-xl p-4 md:p-6 shadow-sm border border-outline-variant/30 relative overflow-hidden">
          {/* ✅ Use AnimatePresence with mode="wait" and the outlet */}
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial="initial"
              animate="animate"
              exit="exit"
              variants={pageVariants}
              transition={pageTransition}
              style={{ position: 'relative', width: '100%', height: '100%' }}
            >
              {outlet}
            </motion.div>
          </AnimatePresence>
        </div>
      </motion.main>

      {/* ===== MOBILE NAV ===== */}
      <motion.nav
        className="md:hidden fixed bottom-0 left-0 right-0 z-50 flex items-center justify-around bg-surface/80 backdrop-blur-md border-t border-outline-variant px-4 py-2"
        initial={{ y: 60, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ type: 'spring', stiffness: 100, damping: 15 }}
      >
        {[
          { to: '/', label: 'AI Chat', icon: 'chat' },
          { to: '/doctors', label: 'Doctors', icon: 'medical_services' },
          { to: '/calendar', label: 'Calendar', icon: 'calendar_month' },
        ].map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex flex-col items-center text-xs transition-all duration-200 ${
                isActive ? 'text-primary scale-110' : 'text-on-surface-variant'
              }`
            }
          >
            <motion.span
              className="material-symbols-outlined"
              whileHover={{ scale: 1.2 }}
              transition={{ type: 'spring', stiffness: 300 }}
            >
              {item.icon}
            </motion.span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </motion.nav>

      {/* ===== FOOTER ===== */}
      <motion.footer
        className="lg:ml-64 border-t border-outline-variant bg-surface-container-highest/50 backdrop-blur-sm py-6 px-4 md:px-8 mt-12"
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.3 }}
      >
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-4">
          <motion.p
            className="text-sm text-on-surface-variant"
            whileHover={{ scale: 1.02 }}
            transition={{ type: 'spring', stiffness: 300 }}
          >
            © 2024 Stellaris General Hospital. Providing trusted care.
          </motion.p>
          <div className="flex flex-wrap gap-4 text-sm text-on-surface-variant">
            {['Contact Us', 'Emergency Services', 'Privacy Policy', 'Terms of Service'].map((item) => (
              <motion.a
                key={item}
                href="#"
                className="hover:underline"
                whileHover={{ scale: 1.08, color: '#00478d' }}
                transition={{ type: 'spring', stiffness: 300 }}
              >
                {item}
              </motion.a>
            ))}
          </div>
        </div>
      </motion.footer>
    </div>
  );
}