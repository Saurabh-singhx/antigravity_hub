import { Platform } from 'react-native';

export const NeoColors = {
  // Light Neomorphic Palette
  background: '#e6ecf5',
  surface: '#e6ecf5',
  surfaceLight: '#f2f6fc',
  surfaceDark: '#d9e2ef',
  
  // Shadows & Highlights
  highlight: '#ffffff',
  shadowDark: '#b4c2d4',
  shadowSoft: 'rgba(164, 178, 198, 0.45)',
  borderLight: '#ffffff',
  borderDark: '#c7d3e3',
  
  // Brand & Accents
  primary: '#4338ca',         // Indigo
  primaryLight: '#6366f1',
  primaryBg: 'rgba(79, 70, 229, 0.08)',
  accentTeal: '#0d9488',
  
  // Status Colors
  success: '#10b981',         // Emerald Green
  successBg: 'rgba(16, 185, 129, 0.12)',
  warning: '#f59e0b',         // Amber
  warningBg: 'rgba(245, 158, 11, 0.12)',
  error: '#ef4444',           // Rose Red
  errorBg: 'rgba(239, 68, 68, 0.12)',
  info: '#3b82f6',            // Blue
  infoBg: 'rgba(59, 130, 246, 0.12)',
  
  // Typography
  textPrimary: '#1e293b',     // Deep Slate
  textSecondary: '#475569',   // Mid Slate
  textMuted: '#64748b',       // Soft Slate
  textLight: '#94a3b8',
  white: '#ffffff',
};

export const NeoStyles = {
  // Raised convex element (buttons, cards)
  card: {
    backgroundColor: NeoColors.surface,
    borderRadius: 16,
    borderWidth: 1,
    borderTopColor: '#ffffff',
    borderLeftColor: '#ffffff',
    borderBottomColor: '#c5d2e3',
    borderRightColor: '#c5d2e3',
    ...Platform.select({
      ios: {
        shadowColor: '#96a7be',
        shadowOffset: { width: 5, height: 5 },
        shadowOpacity: 0.6,
        shadowRadius: 7,
      },
      android: {
        elevation: 4,
      },
      web: {
        boxShadow: '6px 6px 14px #bccadc, -6px -6px 14px #ffffff',
      },
    }),
  },

  // Soft button state
  button: {
    backgroundColor: NeoColors.surface,
    borderRadius: 12,
    borderWidth: 1,
    borderTopColor: '#ffffff',
    borderLeftColor: '#ffffff',
    borderBottomColor: '#c5d2e3',
    borderRightColor: '#c5d2e3',
    ...Platform.select({
      ios: {
        shadowColor: '#96a7be',
        shadowOffset: { width: 3, height: 3 },
        shadowOpacity: 0.5,
        shadowRadius: 5,
      },
      android: {
        elevation: 3,
      },
      web: {
        boxShadow: '4px 4px 8px #c1d0e2, -4px -4px 8px #ffffff',
      },
    }),
  },

  // Pressed / Inset state (active tabs, search inputs)
  inset: {
    backgroundColor: '#dee6f2',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#c5d2e3',
    ...Platform.select({
      ios: {
        shadowColor: '#8a9bb3',
        shadowOffset: { width: -2, height: -2 },
        shadowOpacity: 0.25,
        shadowRadius: 4,
      },
      android: {
        elevation: 0,
      },
    }),
  },
};
