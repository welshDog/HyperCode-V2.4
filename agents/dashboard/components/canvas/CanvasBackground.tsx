import React from 'react';
import { motion } from 'framer-motion';

const stars = [...Array(50)].map(() => ({
  duration: Math.random() * 3 + 2,
  delay: Math.random() * 5,
  top: `${Math.random() * 100}%`,
  left: `${Math.random() * 100}%`,
}));

export const CanvasBackground = () => {
  return (
    <div style={{
      position: 'absolute',
      top: 0,
      left: 0,
      width: '100%',
      height: '100%',
      zIndex: -1,
      background: 'radial-gradient(circle at center, #0B0418 0%, #000000 100%)',
      overflow: 'hidden',
      pointerEvents: 'none'
    }}>
      {/* Animated Grid */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(0,243,255,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(0,243,255,0.05)_1px,transparent_1px)] bg-[size:40px_40px] [mask-image:radial-gradient(ellipse_at_center,black,transparent_80%)]" />

      {/* Twinkling Stars */}
      {stars.map((star, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0 }}
          animate={{ opacity: [0, 1, 0] }}
          transition={{
            duration: star.duration,
            repeat: Infinity,
            delay: star.delay
          }}
          style={{
            position: 'absolute',
            top: star.top,
            left: star.left,
            width: '2px',
            height: '2px',
            background: '#FFFFFF',
            borderRadius: '50%',
            boxShadow: '0 0 4px #FFFFFF'
          }}
        />
      ))}
    </div>
  );
};
