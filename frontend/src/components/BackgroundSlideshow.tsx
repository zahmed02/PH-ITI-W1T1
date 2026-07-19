// src/components/BackgroundSlideshow.tsx
import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const images = [
  '/images/healthcare_professionals_background_high_quality_photography_of_diverse_medical.png',
  '/images/medical_equipment_background_high_quality_photography_of_modern_surgical_tools.png',
  '/images/professional_medical_background_high_quality_photography_of_a_modern_clean.png',
];

export default function BackgroundSlideshow() {
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % images.length);
    }, 7000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="fixed inset-0" style={{ zIndex: -1 }}>
      <AnimatePresence>
        {images.map((src, idx) => (
          <motion.div
            key={idx}
            className="absolute inset-0"
            initial={{ opacity: 0 }}
            animate={{ opacity: idx === currentIndex ? 1.0 : 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 2, ease: 'easeInOut' }}
            style={{
              backgroundImage: `url(${src})`,
              backgroundSize: 'cover',
              backgroundPosition: 'center',
            }}
          />
        ))}
      </AnimatePresence>
    </div>
  );
}