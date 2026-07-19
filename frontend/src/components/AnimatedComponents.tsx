// src/components/AnimatedComponents.tsx
import { motion } from 'framer-motion';
import { ReactNode } from 'react';
import { NavLink } from 'react-router-dom';

export const pageVariants = {
  initial: { opacity: 0, y: 15, scale: 0.98 },
  animate: { opacity: 1, y: 0, scale: 1 },
  exit: { opacity: 0, y: -15, scale: 0.98 },
};

export const pageTransition = {
  duration: 0.3,
  ease: 'easeInOut',
};

export const fadeInUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: 'easeOut' } },
};

// Animated Button (unchanged)
export const AnimatedButton = ({ children, onClick, className = '', variant = 'primary', ...props }) => {
  const getBaseStyles = () => {
    switch (variant) {
      case 'primary':
        return 'bg-primary text-white hover:bg-primary/80';
      case 'secondary':
        return 'bg-secondary text-white hover:bg-secondary/80';
      case 'outline':
        return 'border border-primary text-primary hover:bg-primary hover:text-white';
      case 'danger':
        return 'bg-tertiary text-white hover:bg-tertiary/80';
      default:
        return 'bg-primary text-white hover:bg-primary/80';
    }
  };

  return (
    <motion.button
      onClick={onClick}
      className={`px-4 py-2 rounded-lg font-medium transition-all duration-200 ${getBaseStyles()} ${className}`}
      whileHover={{
        scale: 1.03,
        boxShadow: '0 8px 25px rgba(0,0,0,0.15)',
        transition: { type: 'spring', stiffness: 400, damping: 10 },
      }}
      whileTap={{ scale: 0.95 }}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      {...props}
    >
      {children}
    </motion.button>
  );
};

// Animated Card – with visible border and shadow
export const AnimatedCard = ({
  children,
  className = '',
  delay = 0,
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
}) => (
  <motion.div
    className={`bg-white/90 backdrop-blur-sm rounded-xl border border-outline-variant shadow-sm hover:shadow-md transition-shadow ${className}`}
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.4, delay, ease: 'easeOut' }}
    whileHover={{
      y: -4,
      boxShadow: '0 12px 40px rgba(0,0,0,0.08)',
      transition: { type: 'spring', stiffness: 300, damping: 15 },
    }}
  >
    {children}
  </motion.div>
);