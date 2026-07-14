/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Sidebar
        sidebar: {
          bg:     "#0F172A",   // slate-900
          hover:  "#1E293B",   // slate-800
          active: "#1D4ED8",   // blue-700
          text:   "#94A3B8",   // slate-400
          textActive: "#F8FAFC", // slate-50
          border: "#1E293B",
        },
        // Page
        page: "#F8FAFC",       // slate-50
        // Surface (cards, panels)
        surface: "#FFFFFF",
        surfaceMuted: "#F1F5F9", // slate-100
        // Borders
        border: "#E2E8F0",      // slate-200
        borderMuted: "#CBD5E1", // slate-300
        // Text
        textPrimary:   "#0F172A",  // slate-900
        textSecondary: "#475569",  // slate-500
        textMuted:     "#94A3B8",  // slate-400
        // Brand primary
        primary: {
          DEFAULT: "#1D4ED8",  // blue-700
          hover:   "#1E40AF",  // blue-800
          light:   "#EFF6FF",  // blue-50
          border:  "#BFDBFE",  // blue-200
          text:    "#1D4ED8",
        },
        // Status — semantic, not decorative
        approve: {
          DEFAULT: "#16A34A",  // green-600
          bg:      "#F0FDF4",  // green-50
          border:  "#BBF7D0",  // green-200
          text:    "#15803D",  // green-700
        },
        refer: {
          DEFAULT: "#D97706",  // amber-600
          bg:      "#FFFBEB",  // amber-50
          border:  "#FDE68A",  // amber-200
          text:    "#B45309",  // amber-700
        },
        decline: {
          DEFAULT: "#DC2626",  // red-600
          bg:      "#FEF2F2",  // red-50
          border:  "#FECACA",  // red-200
          text:    "#B91C1C",  // red-700
        },
        warning: {
          DEFAULT: "#F59E0B",
          bg:      "#FFFBEB",
          border:  "#FDE68A",
          text:    "#92400E",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
      },
      fontSize: {
        "2xs": ["0.65rem", "1rem"],
      },
      boxShadow: {
        card: "0 1px 3px 0 rgb(0 0 0 / 0.07), 0 1px 2px -1px rgb(0 0 0 / 0.07)",
        cardHover: "0 4px 6px -1px rgb(0 0 0 / 0.08), 0 2px 4px -2px rgb(0 0 0 / 0.08)",
        sidebar: "1px 0 0 0 #1E293B",
      },
    },
  },
  plugins: [],
};
