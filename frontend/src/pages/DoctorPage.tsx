import { useParams } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { getDoctor, getReviewsByDoctor } from '../api/client';

export default function DoctorPage() {
  const { id } = useParams();
  const [doctor, setDoctor] = useState<any>(null);
  const [reviews, setReviews] = useState<any[]>([]);

  useEffect(() => {
    if (id) {
      getDoctor(Number(id)).then(setDoctor);
      getReviewsByDoctor(Number(id)).then(setReviews);
    }
  }, [id]);

  if (!doctor) return <div className="text-center py-12">Loading...</div>;

  return (
    <div>
      <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-8 mb-8">
        <div className="flex items-start gap-8">
          <div className="w-32 h-32 rounded-xl bg-surface-container flex items-center justify-center border border-outline-variant">
            <span className="material-symbols-outlined text-7xl text-primary/40">account_circle</span>
          </div>
          <div>
            <h1 className="font-headline-lg text-headline-lg text-primary">Dr. {doctor.first_name} {doctor.last_name}</h1>
            <p className="text-xl text-primary font-bold">{doctor.specialty}</p>
            <p className="text-on-surface-variant">{doctor.years_of_experience} years of experience</p>
            <div className="flex items-center gap-2 mt-2">
              <span className="text-yellow-500 material-symbols-outlined">star</span>
              <span className="font-bold">{doctor.rating || doctor.avg_rating || 'N/A'}</span>
            </div>
            <p className="mt-4 text-on-surface">{doctor.bio}</p>
          </div>
        </div>
      </div>

      <h2 className="font-headline-md text-headline-md mb-4">Patient Reviews</h2>
      {reviews.length === 0 ? (
        <p className="text-on-surface-variant">No reviews yet.</p>
      ) : (
        <div className="space-y-4">
          {reviews.map((r) => (
            <div key={r.id} className="bg-surface-container-lowest border border-outline-variant p-4 rounded-xl">
              <div className="flex items-center gap-2">
                <span className="text-yellow-500 material-symbols-outlined">star</span>
                <span className="font-bold">{r.rating}/5</span>
                <span className="text-on-surface-variant text-sm">- {r.comment}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}