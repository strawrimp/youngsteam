import type { Config } from 'tailwindcss';

const config: Config = {
  darkMode: false,
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // Agent role colors - Toned down professional palette
        agent: {
          manager: '#0066CC',     // Leadership blue (toned down)
          developer: '#00AA44',   // Technical green (toned down)
          designer: '#8B5CF6',    // Creative purple (toned down)
          researcher: '#F59E0B',  // Analytical amber (toned down)
        },
        // Neutral colors
        neutral: {
          50: '#F7F9FC',   // Surface / Hover
          100: '#EDF2F7',  // Light hover
          200: '#E2E8F0',  // Active
          300: '#E1E7F0',  // Borders
          400: '#CBD5E0',  // Not used, for consistency
          600: '#718096',  // Text secondary
          700: '#4A5568',  // Not used, for consistency
          800: '#2D3748',  // Info / neutral
          900: '#1A202C',  // Text primary
        },
        // Semantic colors
        success: '#2F855A',
        warning: '#C05621',
        error: '#C53030',
        info: '#2D3748',
      },
      fontFamily: {
        geist: [
          'Geist',
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'Roboto',
          'Helvetica Neue',
          'sans-serif',
        ],
      },
      fontSize: {
        // H1: 32px, weight 600
        '3xl': ['32px', { lineHeight: '44px', fontWeight: '600' }],
        // H2: 24px, weight 600
        '2xl': ['24px', { lineHeight: '31px', fontWeight: '600' }],
        // H3: 20px, weight 600
        'xl': ['20px', { lineHeight: '26px', fontWeight: '600' }],
        // Body Large: 18px, weight 400
        'lg': ['18px', { lineHeight: '27px', fontWeight: '400' }],
        // Body: 16px, weight 400
        'base': ['16px', { lineHeight: '24px', fontWeight: '400' }],
        // Body Small: 14px, weight 400
        'sm': ['14px', { lineHeight: '21px', fontWeight: '400' }],
        // Label: 12px, weight 500
        'xs': ['12px', { lineHeight: '17px', fontWeight: '500' }],
        // Caption: 11px, weight 400
        'caption': ['11px', { lineHeight: '15px', fontWeight: '400' }],
      },
      spacing: {
        // 8px base grid
        xs: '4px',
        sm: '8px',
        md: '12px',
        lg: '16px',
        xl: '24px',
        '2xl': '32px',
        '3xl': '48px',
        '4xl': '64px',
      },
      borderRadius: {
        'xs': '2px',
        'sm': '4px',
        'md': '4px',
        'lg': '4px',
        'full': '9999px',
      },
      boxShadow: {
        'sm': '0 1px 3px rgba(0, 0, 0, 0.1)',
        'md': '0 2px 6px rgba(0, 0, 0, 0.08)',
        'lg': '0 4px 12px rgba(0, 0, 0, 0.1)',
        'inset': 'inset 0 1px 2px rgba(0, 0, 0, 0.05)',
        'focus-manager': '0 0 0 3px rgba(0, 102, 204, 0.1)',
        'focus-developer': '0 0 0 3px rgba(0, 170, 68, 0.1)',
        'focus-designer': '0 0 0 3px rgba(139, 92, 246, 0.1)',
        'focus-researcher': '0 0 0 3px rgba(245, 158, 11, 0.1)',
      },
      outlineColor: {
        'manager': '#4E7EBE',
        'developer': '#4A9B6F',
        'designer': '#7C6BA8',
        'researcher': '#D4A055',
      },
      outlineWidth: {
        '3': '3px',
      },
      outlineOffset: {
        '2': '2px',
      },
      animation: {
        'spin-slow': 'spin 1s linear infinite',
        'pulse-subtle': 'pulse 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.2s ease-out',
        'slide-up': 'slideUp 0.2s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(16px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
      },
      transitionDuration: {
        '150': '150ms',
        '200': '200ms',
        '300': '300ms',
      },
      transitionTimingFunction: {
        'ease-in-out-standard': 'cubic-bezier(0.4, 0, 0.2, 1)',
      },
      minHeight: {
        'touch': '44px',
      },
      minWidth: {
        'touch': '44px',
      },
      width: {
        'sidebar-left': '280px',
        'sidebar-right': '300px',
      },
      maxWidth: {
        'message': '75%',
      },
    },
  },
  plugins: [
    // Focus visible plugin for better keyboard navigation
    require('@tailwindcss/forms'),
  ],
  future: {
    hoverOnlyWhenSupported: true,
  },
};

export default config;
