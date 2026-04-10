import type { Config } from 'tailwindcss';

const config: Config = {
  darkMode: false, // Light mode only
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // === Surface Colors (Backgrounds) ===
        'surface-bright': '#f5f7f9',
        'surface': '#f5f7f9',
        'surface-container': '#e5e9eb',
        'surface-container-low': '#eef1f3',
        'surface-container-lowest': '#ffffff',
        'surface-container-high': '#dfe3e6',
        'surface-container-highest': '#d9dde0',
        'surface-dim': '#d0d5d8',
        'surface-variant': '#d9dde0',
        'surface-tint': '#475569',
        
        // === Primary Colors (Slate Gray) ===
        'primary': '#475569',
        'primary-dim': '#334155',
        'primary-fixed': '#94a3b8',
        'primary-fixed-dim': '#64748b',
        'primary-container': '#94a3b8',
        'on-primary': '#f8fafc',
        'on-primary-container': '#1e293b',
        'on-primary-fixed': '#0f172a',
        'on-primary-fixed-variant': '#1e293b',
        'inverse-primary': '#94a3b8',
        
        // === Secondary Colors (Creative Purple) ===
        'secondary': '#702ae1',
        'secondary-dim': '#6411d5',
        'secondary-fixed': '#dcc9ff',
        'secondary-fixed-dim': '#d0b8ff',
        'secondary-container': '#dcc9ff',
        'on-secondary': '#f8f0ff',
        'on-secondary-container': '#5b00c7',
        'on-secondary-fixed': '#430097',
        'on-secondary-fixed-variant': '#6514d6',
        
        // === Tertiary Colors ===
        'tertiary': '#4e5a81',
        'tertiary-dim': '#424e74',
        'tertiary-fixed': '#c4d0fd',
        'tertiary-fixed-dim': '#b6c2ef',
        'tertiary-container': '#c4d0fd',
        'on-tertiary': '#f1f2ff',
        'on-tertiary-container': '#3a466b',
        'on-tertiary-fixed': '#263357',
        'on-tertiary-fixed-variant': '#434f75',
        
        // === Text Colors ===
        'on-surface': '#2c2f31',
        'on-surface-variant': '#595c5e',
        'on-background': '#2c2f31',
        'inverse-surface': '#0b0f10',
        'inverse-on-surface': '#9a9d9f',
        
        // === Outline Colors ===
        'outline': '#747779',
        'outline-variant': '#abadaf',
        
        // === Error Colors ===
        'error': '#b41340',
        'error-dim': '#a70138',
        'error-container': '#f74b6d',
        'on-error': '#ffefef',
        'on-error-container': '#510017',
        
        // === Agent Role Colors ===
        'agent': {
          manager: '#475569',      // Slate Gray
          developer: '#10b981',    // Emerald Green
          designer: '#702ae1',     // Secondary Purple
          researcher: '#f59e0b',   // Amber
        },
        
        // === Background ===
        'background': '#f5f7f9',
      },
      
      fontFamily: {
        'headline': ['Manrope', 'sans-serif'],
        'body': ['Inter', 'sans-serif'],
        'label': ['Inter', 'sans-serif'],
      },
      
      fontSize: {
        // Display - Large (3.5rem / 56px)
        'display-lg': ['3.5rem', { lineHeight: '1.1', fontWeight: '800', letterSpacing: '-0.02em' }],
        // Headline - Medium (1.75rem / 28px)
        'headline-md': ['1.75rem', { lineHeight: '1.3', fontWeight: '700', letterSpacing: '-0.01em' }],
        // Headline - Small (1.25rem / 20px)
        'headline-sm': ['1.25rem', { lineHeight: '1.4', fontWeight: '600' }],
        // Title - Medium (1rem / 16px)
        'title-md': ['1rem', { lineHeight: '1.5', fontWeight: '600' }],
        // Title - Small (0.875rem / 14px)
        'title-sm': ['0.875rem', { lineHeight: '1.4', fontWeight: '600' }],
        // Body - Large (1rem / 16px)
        'body-lg': ['1rem', { lineHeight: '1.6', fontWeight: '400' }],
        // Body - Medium (0.875rem / 14px)
        'body-md': ['0.875rem', { lineHeight: '1.5', fontWeight: '400' }],
        // Body - Small (0.75rem / 12px)
        'body-sm': ['0.75rem', { lineHeight: '1.4', fontWeight: '400' }],
        // Label - Small (0.6875rem / 11px)
        'label-sm': ['0.6875rem', { lineHeight: '1.3', fontWeight: '500', letterSpacing: '0.02em' }],
        // Label - Extra Small (0.625rem / 10px)
        'label-xs': ['0.625rem', { lineHeight: '1.2', fontWeight: '700', letterSpacing: '0.05em' }],
      },
      
      borderRadius: {
        'DEFAULT': '0.25rem',
        'sm': '0.375rem',
        'md': '0.5rem',
        'lg': '0.75rem',
        'xl': '1rem',
        '2xl': '1.5rem',
        '3xl': '2rem',
        'full': '9999px',
      },
      
      boxShadow: {
        'sm': '0 1px 2px rgba(0, 0, 0, 0.04)',
        'md': '0 2px 4px rgba(0, 0, 0, 0.06)',
        'lg': '0 4px 8px rgba(0, 0, 0, 0.08)',
        'xl': '0 8px 16px rgba(0, 0, 0, 0.1)',
        '2xl': '0 16px 32px rgba(0, 0, 0, 0.12)',
        'glass': '0px 20px 40px rgba(71, 85, 105, 0.08)',
        'primary': '0 4px 12px rgba(71, 85, 105, 0.2)',
        'card': '0 1px 3px rgba(0, 0, 0, 0.05), 0 1px 2px rgba(0, 0, 0, 0.1)',
      },
      
      backdropBlur: {
        'glass': '16px',
      },
      
      spacing: {
        '18': '4.5rem',
        '22': '5.5rem',
        '72': '18rem',
        '80': '20rem',
        '88': '22rem',
        '96': '24rem',
        'sidebar': '280px',
        'panel': '320px',
      },
      
      width: {
        'sidebar': '280px',
        'panel': '320px',
      },
      
      maxWidth: {
        'chat': '42rem', // ~672px - max-w-2xl equivalent
        'input': '56rem', // ~896px - max-w-4xl
      },
      
      animation: {
        'fade-in': 'fadeIn 250ms cubic-bezier(0.4, 0, 0.2, 1)',
        'fade-in-up': 'fadeInUp 300ms cubic-bezier(0.4, 0, 0.2, 1)',
        'slide-up': 'slideUp 200ms cubic-bezier(0.4, 0, 0.2, 1)',
        'bounce-in': 'bounceIn 500ms cubic-bezier(0.4, 0, 0.2, 1)',
        'pulse-dot': 'pulseDot 1.4s ease-in-out infinite',
        'typing-bounce': 'typingBounce 1.4s ease-in-out infinite',
      },
      
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        fadeInUp: {
          '0%': { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideUp: {
          '0%': { transform: 'translateY(8px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        bounceIn: {
          '0%': { opacity: '0', transform: 'scale(0.3)' },
          '50%': { transform: 'scale(1.05)' },
          '70%': { transform: 'scale(0.9)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        pulseDot: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.5' },
        },
        typingBounce: {
          '0%, 80%, 100%': { transform: 'translateY(0)' },
          '40%': { transform: 'translateY(-6px)' },
        },
      },
      
      transitionDuration: {
        '250': '250ms',
      },
      
      transitionTimingFunction: {
        'standard': 'cubic-bezier(0.4, 0, 0.2, 1)',
      },
    },
  },
  plugins: [],
  future: {
    hoverOnlyWhenSupported: true,
  },
};

export default config;
