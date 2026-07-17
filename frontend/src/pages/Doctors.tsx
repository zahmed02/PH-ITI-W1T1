import { useState, useEffect } from 'react';
import { getDoctors } from '../api/client';
import { Link } from 'react-router-dom';

export default function Doctors() {
  const [doctors, setDoctors] = useState<any[]>([]);
  const [specialty, setSpecialty] = useState('');
  const [minExp, setMinExp] = useState<number | undefined>();
  const [minRating, setMinRating] = useState<number | undefined>();

  const search = async () => {
    const params: any = {};
    if (specialty) params.specialty = specialty;
    if (minExp) params.min_experience = minExp;
    if (minRating) params.min_rating = minRating;
    const data = await getDoctors(params);
    setDoctors(data);
  };

  useEffect(() => { search(); }, []);

  return (
    <div>
      {/* Hero Section */}
      <section className="mb-12 relative overflow-hidden rounded-xl bg-primary p-8 md:p-12">
        <div className="absolute right-0 top-0 opacity-10 transform translate-x-1/4 -translate-y-1/4 scale-150">
          <span className="material-symbols-outlined text-[320px]">stethoscope</span>
        </div>
        <div className="relative z-10">
          <h1 className="font-headline-lg text-headline-lg text-white mb-4">Find Specialized Care</h1>
          <p className="font-body-lg text-body-lg text-white/80 max-w-2xl mb-8">Access our network of board-certified medical professionals.</p>
          <div className="relative max-w-2xl">
            <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant text-[24px]">search</span>
            <input
              className="w-full pl-14 pr-6 py-4 rounded-xl border-none ring-1 ring-outline-variant focus:ring-2 focus:ring-white bg-white text-on-surface font-body-md transition-all shadow-lg outline-none"
              placeholder="Search by doctor name or specialty..."
              value={specialty}
              onChange={(e) => setSpecialty(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && search()}
            />
          </div>
        </div>
      </section>

      {/* Filter Chips */}
      <div className="flex flex-wrap gap-3 mb-8">
        <button onClick={() => { setSpecialty(''); search(); }} className={`px-6 py-2 rounded-full font-label-md transition-all ${specialty === '' ? 'bg-primary text-white' : 'bg-surface-container hover:bg-surface-variant text-on-surface-variant'}`}>
          All Specialists
        </button>
        {['Cardiology', 'Neurology', 'Pediatrics', 'Orthopedics', 'Dermatology'].map(spec => (
          <button
            key={spec}
            onClick={() => { setSpecialty(spec); search(); }}
            className={`px-6 py-2 rounded-full font-label-md transition-all ${specialty === spec ? 'bg-primary text-white' : 'bg-surface-container hover:bg-surface-variant text-on-surface-variant'}`}
          >
            {spec}
          </button>
        ))}
      </div>

      {/* Doctor Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {doctors.map((doc) => (
          <Link key={doc.id} to={`/doctor/${doc.id}`} className="block bg-surface-container-lowest border border-outline-variant p-6 rounded-xl shadow-sm hover:-translate-y-1 hover:shadow-md transition-all group">
            <div className="flex items-start gap-6 mb-6">
              <div className="w-24 h-24 rounded-xl bg-surface-container flex items-center justify-center border border-outline-variant">
                <span className="material-symbols-outlined text-5xl text-primary/40">account_circle</span>
              </div>
              <div>
                <h3 className="font-headline-sm text-headline-sm text-primary mb-1">Dr. {doc.first_name} {doc.last_name}</h3>
                <div className="font-label-sm text-label-sm text-primary uppercase tracking-wider mb-2">{doc.specialty}</div>
                <div className="flex items-center gap-1 text-yellow-500 mb-1">
                  <span className="material-symbols-outlined text-[18px]">star</span>
                  <span className="text-on-surface-variant font-label-sm ml-1">{doc.rating || doc.avg_rating || 'N/A'}</span>
                </div>
                <div className="font-body-sm text-body-sm text-on-surface-variant">{doc.years_of_experience} years of experience</div>
              </div>
            </div>
            <div className="flex items-center justify-between border-t border-outline-variant/30 pt-6">
              <div className="flex flex-col">
                <span className="font-label-sm text-on-surface-variant">Next Available</span>
                <span className="font-label-md text-primary">Check schedule</span>
              </div>
              <button className="bg-primary hover:bg-primary-container text-white px-5 py-2.5 rounded-full font-label-md transition-all active:scale-95">View Profile</button>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}