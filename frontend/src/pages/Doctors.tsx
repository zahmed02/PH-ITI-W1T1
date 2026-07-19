// src/pages/Doctors.tsx
import { useState, useEffect, useRef } from 'react';
import { getDoctors, getReviewsByDoctor, uploadDoctorImage } from '../api/client';
import { useNavigate } from 'react-router-dom';
import { AnimatedButton, AnimatedCard } from '../components/AnimatedComponents';
import { motion } from 'framer-motion';

export default function Doctors() {
  const [doctors, setDoctors] = useState<any[]>([]);
  const [specialty, setSpecialty] = useState('');
  const [minExp, setMinExp] = useState<number | undefined>();
  const [minRating, setMinRating] = useState<number | undefined>();
  const [expandedDoctorId, setExpandedDoctorId] = useState<number | null>(null);
  const [reviewsMap, setReviewsMap] = useState<{ [key: number]: any[] }>({});
  const [loadingReviews, setLoadingReviews] = useState<{ [key: number]: boolean }>({});
  const [uploading, setUploading] = useState<{ [key: number]: boolean }>({});
  const fileInputRef = useRef<{ [key: number]: HTMLInputElement | null }>({});
  const navigate = useNavigate();

  const search = async () => {
    const params: any = {};
    if (specialty) params.specialty = specialty;
    if (minExp) params.min_experience = minExp;
    if (minRating) params.min_rating = minRating;
    const data = await getDoctors(params);
    setDoctors(data);
  };

  useEffect(() => { search(); }, []);

  const toggleReviews = async (doctorId: number) => {
    if (expandedDoctorId === doctorId) {
      setExpandedDoctorId(null);
      return;
    }
    setExpandedDoctorId(doctorId);
    if (!reviewsMap[doctorId]) {
      setLoadingReviews(prev => ({ ...prev, [doctorId]: true }));
      try {
        const reviews = await getReviewsByDoctor(doctorId);
        setReviewsMap(prev => ({ ...prev, [doctorId]: reviews }));
      } catch {
        // ignore
      } finally {
        setLoadingReviews(prev => ({ ...prev, [doctorId]: false }));
      }
    }
  };

  const goToCalendar = (doctorId: number) => navigate(`/calendar?doctorId=${doctorId}`);

  const handleFileChange = async (doctorId: number, event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploading(prev => ({ ...prev, [doctorId]: true }));
    try {
      await uploadDoctorImage(doctorId, file);
      await search();
    } catch {
      alert('Failed to upload image');
    } finally {
      setUploading(prev => ({ ...prev, [doctorId]: false }));
      event.target.value = '';
    }
  };

  const triggerFileInput = (doctorId: number) => {
    fileInputRef.current[doctorId]?.click();
  };

  return (
    <div className="flex flex-col lg:flex-row gap-8">
      {/* Filters Sidebar */}
      <aside className="lg:w-64 shrink-0">
        <motion.div
          className="bg-surface-container-low p-4 rounded-xl border border-outline-variant sticky top-24"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1 }}
        >
          <h3 className="text-lg font-semibold text-primary mb-4">Filters</h3>
          <div className="mb-4">
            <label className="text-xs font-medium text-on-surface-variant block mb-1">Specialty</label>
            <div className="space-y-1">
              {['All Specialties', 'Cardiology', 'Neurology', 'Pediatrics', 'Orthopedics', 'Dermatology'].map((spec) => (
                <label key={spec} className="flex items-center gap-2 cursor-pointer text-sm">
                  <input
                    type="checkbox"
                    checked={specialty === (spec === 'All Specialties' ? '' : spec)}
                    onChange={() => setSpecialty(spec === 'All Specialties' ? '' : spec)}
                    className="rounded border-outline text-primary focus:ring-primary"
                  />
                  <span>{spec}</span>
                </label>
              ))}
            </div>
          </div>
          <div className="mb-4">
            <label className="text-xs font-medium text-on-surface-variant block mb-1">Min. Rating</label>
            <select
              value={minRating || ''}
              onChange={(e) => setMinRating(e.target.value ? Number(e.target.value) : undefined)}
              className="w-full bg-surface-container-lowest border border-outline-variant rounded-lg p-1.5 text-sm focus:border-primary focus:ring-1 focus:ring-primary outline-none"
            >
              <option value="">Any Rating</option>
              <option value="4.0">4.0+ Stars</option>
              <option value="4.5">4.5+ Stars</option>
            </select>
          </div>
          <AnimatedButton
            variant="primary"
            onClick={() => { setSpecialty(''); setMinRating(undefined); search(); }}
            className="w-full text-sm"
          >
            Reset Filters
          </AnimatedButton>
        </motion.div>
      </aside>

      {/* Doctor Grid */}
      <section className="flex-1">
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-6 gap-4">
          <div>
            <h1 className="text-3xl font-bold text-primary">Find a Doctor</h1>
            <p className="text-sm text-on-surface-variant">Connect with our world-class specialists.</p>
          </div>
          <div className="relative w-full md:w-64">
            <input
              className="w-full pl-9 pr-3 py-1.5 bg-surface-container-lowest border border-outline-variant rounded-full text-sm focus:border-primary focus:ring-1 focus:ring-primary outline-none"
              placeholder="Search by name or keyword..."
              value={specialty}
              onChange={(e) => { setSpecialty(e.target.value); search(); }}
            />
            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline text-sm">search</span>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-6">
          {doctors.map((doc, index) => (
            <motion.div
              key={doc.id}
              className="bg-white/90 backdrop-blur-sm rounded-xl border-2 border-outline-variant shadow-sm hover:shadow-md transition-all flex flex-col overflow-hidden"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: index * 0.05 }}
              whileHover={{
                y: -4,
                boxShadow: '0 12px 40px rgba(0,0,0,0.08)',
                transition: { type: 'spring', stiffness: 300, damping: 15 },
              }}
            >
              {/* Image Section */}
              <div className="relative w-full aspect-square overflow-hidden bg-surface-container">
                {doc.profile_image ? (
                  <img
                    src={doc.profile_image}
                    alt={`Dr. ${doc.first_name} ${doc.last_name}`}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center bg-surface-container">
                    <span className="material-symbols-outlined text-6xl text-primary/40">account_circle</span>
                  </div>
                )}
                <div className="absolute top-2 right-2 bg-secondary-container/90 backdrop-blur-sm text-on-secondary-container px-2 py-0.5 rounded-full flex items-center gap-1 text-xs font-medium">
                  <span className="material-symbols-outlined text-[14px]" style={{ fontVariationSettings: "'FILL' 1" }}>star</span>
                  <span>{doc.rating || doc.avg_rating || 'N/A'}</span>
                </div>
                <button
                  onClick={() => triggerFileInput(doc.id)}
                  className="absolute bottom-2 right-2 bg-primary text-white rounded-full p-1 text-xs hover:bg-primary-container hover:text-on-primary-container transition"
                  disabled={uploading[doc.id]}
                >
                  <span className="material-symbols-outlined text-sm">upload</span>
                </button>
                <input
                  type="file"
                  accept="image/*"
                  ref={(el) => (fileInputRef.current[doc.id] = el)}
                  onChange={(e) => handleFileChange(doc.id, e)}
                  className="hidden"
                />
              </div>

              {/* Info Section */}
              <div className="p-4 flex flex-col flex-1">
                <h3 className="font-semibold text-lg text-on-surface">Dr. {doc.first_name} {doc.last_name}</h3>
                <p className="text-xs font-medium text-primary uppercase tracking-wider">{doc.specialty}</p>
                <div className="flex items-center gap-1 text-xs text-on-surface-variant mt-1">
                  <span className="material-symbols-outlined text-[16px]">verified_user</span>
                  <span>{doc.years_of_experience}+ Years</span>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <AnimatedButton
                    variant="outline"
                    onClick={() => toggleReviews(doc.id)}
                    className="flex-1 text-xs"
                  >
                    {expandedDoctorId === doc.id ? 'Hide Reviews' : 'View Reviews'}
                  </AnimatedButton>
                  <AnimatedButton
                    variant="primary"
                    onClick={() => goToCalendar(doc.id)}
                    className="flex-1 text-xs"
                  >
                    Schedule
                  </AnimatedButton>
                </div>

                {expandedDoctorId === doc.id && (
                  <div className="mt-3 pt-3 border-t border-outline-variant/30">
                    <h4 className="text-xs font-medium text-primary">Patient Reviews</h4>
                    {loadingReviews[doc.id] ? (
                      <p className="text-xs text-on-surface-variant mt-1">Loading...</p>
                    ) : reviewsMap[doc.id] && reviewsMap[doc.id].length > 0 ? (
                      <ul className="space-y-1 mt-1">
                        {reviewsMap[doc.id].map((review: any) => (
                          <li key={review.id} className="bg-surface-container-low p-1.5 rounded flex items-start gap-1 text-xs">
                            <span className="text-yellow-500 material-symbols-outlined text-sm">star</span>
                            <span className="font-bold">{review.rating}/5</span>
                            <span className="text-on-surface-variant">- {review.comment}</span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-xs text-on-surface-variant mt-1">No reviews yet.</p>
                    )}
                  </div>
                )}
              </div>
            </motion.div>
          ))}
        </div>
      </section>
    </div>
  );
}