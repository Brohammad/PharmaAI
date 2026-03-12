/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter var', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      colors: {
        brand: {
          50:  '#eef9ff',
          100: '#d9f1ff',
          200: '#bbe6ff',
          300: '#8ad7ff',
          400: '#51bdff',
          500: '#299cff',
          600: '#0e7ef6',
          700: '#0a66e3',
          800: '#1051b8',
          900: '#134791',
          950: '#0f2d58',
        },
        slate: {
          850: '#131c2e',
          900: '#0d1424',
          950: '#070d1a',
        },
      },
      backgroundImage: {
        'glass-gradient':  'linear-gradient(135deg, rgba(255,255,255,0.06) 0%, rgba(255,255,255,0.02) 100%)',
        'brand-gradient':  'linear-gradient(135deg, #299cff 0%, #0a66e3 100%)',
        'hero-gradient':   'radial-gradient(ellipse 80% 50% at 50% -20%, rgba(14,126,246,0.25) 0%, transparent 70%)',
        'mesh-gradient':   'radial-gradient(at 27% 37%, rgba(14,126,246,0.12) 0, transparent 50%), radial-gradient(at 97% 21%, rgba(168,85,247,0.08) 0, transparent 50%)',
      },
      boxShadow: {
        'glass':    '0 4px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.06)',
        'glass-sm': '0 2px 12px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.05)',
        'glow-brand': '0 0 20px rgba(41,156,255,0.25)',
        'glow-emerald': '0 0 20px rgba(52,211,153,0.2)',
        'glow-red':   '0 0 20px rgba(248,113,113,0.2)',
        'inner-glow': 'inset 0 1px 0 rgba(255,255,255,0.08)',
      },
      animation: {
        'pulse-slow':   'pulse 3s cubic-bezier(0.4,0,0.6,1) infinite',
        'fade-in':      'fadeIn 0.35s ease-out',
        'slide-up':     'slideUp 0.35s cubic-bezier(0.16,1,0.3,1)',
        'slide-in-left':'slideInLeft 0.3s cubic-bezier(0.16,1,0.3,1)',
        'scale-in':     'scaleIn 0.2s ease-out',
        'shimmer':      'shimmer 2.5s linear infinite',
        'glow-pulse':   'glowPulse 3s ease-in-out infinite',
        'float':        'float 6s ease-in-out infinite',
        'spin-slow':    'spin 8s linear infinite',
      },
      keyframes: {
        fadeIn:      { from: { opacity: 0 },                                to: { opacity: 1 } },
        slideUp:     { from: { opacity: 0, transform: 'translateY(12px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
        slideInLeft: { from: { opacity: 0, transform: 'translateX(-12px)' },to: { opacity: 1, transform: 'translateX(0)' } },
        scaleIn:     { from: { opacity: 0, transform: 'scale(0.96)' },      to: { opacity: 1, transform: 'scale(1)' } },
        shimmer: {
          '0%':   { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition:  '200% 0' },
        },
        glowPulse: {
          '0%,100%': { opacity: 0.6 },
          '50%':     { opacity: 1 },
        },
        float: {
          '0%,100%': { transform: 'translateY(0px)' },
          '50%':     { transform: 'translateY(-6px)' },
        },
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
}

