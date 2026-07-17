import { Link, Outlet } from 'react-router-dom';

export default function Layout() {
  return (
    <div className="min-h-screen bg-background">
      {/* Top App Bar */}
      <header className="flex justify-between items-center w-full px-gutter h-16 sticky top-0 z-50 bg-surface shadow-sm">
        <div className="flex items-center gap-4">
          <span className="font-headline-md text-headline-md font-bold text-primary">MedCare Clinical</span>
        </div>
        <nav className="hidden md:flex items-center gap-8">
          <Link to="/" className="text-primary font-bold border-b-2 border-primary py-1">Home</Link>
          <Link to="/doctors" className="text-on-surface-variant hover:text-primary transition-colors">Doctors</Link>
          <Link to="/appointments" className="text-on-surface-variant hover:text-primary transition-colors">Appointments</Link>
        </nav>
        <div className="flex items-center gap-4">
          <span className="material-symbols-outlined text-on-surface-variant">notifications</span>
          <span className="material-symbols-outlined text-on-surface-variant">account_circle</span>
        </div>
      </header>

      {/* Main Content */}
      <main className="px-4 py-8 md:px-margin-desktop md:py-12 max-w-container-max mx-auto">
        <Outlet />
      </main>

      {/* Bottom Nav (Mobile) */}
      <nav className="md:hidden fixed bottom-0 left-0 w-full z-50 flex justify-around items-center px-4 py-3 bg-surface shadow-[0_-4px_12px_rgba(0,0,0,0.05)] rounded-t-xl">
        <Link to="/" className="flex flex-col items-center text-on-surface-variant">
          <span className="material-symbols-outlined">home</span>
          <span className="text-label-sm">Home</span>
        </Link>
        <Link to="/doctors" className="flex flex-col items-center text-on-surface-variant">
          <span className="material-symbols-outlined">medical_services</span>
          <span className="text-label-sm">Doctors</span>
        </Link>
        <Link to="/appointments" className="flex flex-col items-center text-on-surface-variant">
          <span className="material-symbols-outlined">calendar_month</span>
          <span className="text-label-sm">Appointments</span>
        </Link>
      </nav>
    </div>
  );
}