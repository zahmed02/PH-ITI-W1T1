/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // ---- PRIMARY: deep crimson - brand color, CTAs, active nav, headers ----
        "primary": "#8c0021",
        "on-primary": "#ffffff",
        "primary-container": "#a3001f",
        "on-primary-container": "#ffd9d7",
        "primary-fixed": "#ffdad9",
        "on-primary-fixed": "#410008",
        "primary-fixed-dim": "#ffb3ae",
        "on-primary-fixed-variant": "#73000e",
        "inverse-primary": "#ffb3ae",
        "surface-tint": "#8c0021",

        // ---- SECONDARY: dusty rose - softer/muted, used for positive/available states ----
        "secondary": "#8e4b5b",
        "on-secondary": "#ffffff",
        "secondary-container": "#ffd9e0",
        "on-secondary-container": "#5e1b2c",
        "secondary-fixed": "#ffd9e0",
        "on-secondary-fixed": "#3a0716",
        "secondary-fixed-dim": "#ffb1c2",
        "on-secondary-fixed-variant": "#6f293a",

        // ---- TERTIARY: terracotta/rust - warmer orange-red, used for warnings/booked states ----
        "tertiary": "#9c4a17",
        "on-tertiary": "#ffffff",
        "tertiary-container": "#a14c19",
        "on-tertiary-container": "#ffdbc7",
        "tertiary-fixed": "#ffdbc7",
        "on-tertiary-fixed": "#341100",
        "tertiary-fixed-dim": "#ffb68c",
        "on-tertiary-fixed-variant": "#7c3710",

        // ---- ERROR: standard alert red, distinct enough from primary crimson ----
        "error": "#ba1a1a",
        "on-error": "#ffffff",
        "error-container": "#ffdad6",
        "on-error-container": "#93000a",

        // ---- NEUTRAL SURFACES: true near-white / warm near-black, zero blue tint ----
        "background": "#fffbff",
        "on-background": "#201a1a",
        "surface": "#fffbff",
        "on-surface": "#201a1a",
        "surface-dim": "#e7d6d5",
        "surface-bright": "#fff8f7",
        "surface-container-lowest": "#ffffff",
        "surface-container-low": "#fff1ef",
        "surface-container": "#fceae8",
        "surface-container-high": "#f7e4e2",
        "surface-container-highest": "#f1dedc",
        "surface-variant": "#f4ddda",
        "on-surface-variant": "#534342",
        "outline": "#736361",
        "outline-variant": "#b38981",
        "inverse-surface": "#362f2e",
        "inverse-on-surface": "#ffedea",
      },
      borderRadius: {
        DEFAULT: "0.25rem",
        lg: "0.5rem",
        xl: "0.75rem",
        full: "9999px",
      },
      spacing: {
        "margin-mobile": "16px",
        "margin-desktop": "32px",
        "container-max": "1280px",
        "gutter": "24px",
      },
      fontFamily: {
        'title-lg': ['Inter', 'sans-serif'],
        'label-md': ['Inter', 'sans-serif'],
        'headline-lg': ['Inter', 'sans-serif'],
        'headline-md': ['Inter', 'sans-serif'],
        'body-md': ['Inter', 'sans-serif'],
        'body-sm': ['Inter', 'sans-serif'],
      },
      fontSize: {
        'title-lg': ['20px', { lineHeight: '28px', fontWeight: '600' }],
        'label-md': ['12px', { lineHeight: '16px', letterSpacing: '0.05em', fontWeight: '600' }],
        'headline-lg': ['32px', { lineHeight: '40px', letterSpacing: '-0.01em', fontWeight: '600' }],
        'headline-md': ['24px', { lineHeight: '32px', fontWeight: '600' }],
        'body-md': ['16px', { lineHeight: '24px', fontWeight: '400' }],
        'body-sm': ['14px', { lineHeight: '20px', fontWeight: '400' }],
      },
    },
  },
  plugins: [],
}