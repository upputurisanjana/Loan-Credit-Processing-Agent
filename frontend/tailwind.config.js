/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      // ── Palette from UI_UX_DESIGN.md §1 ──────────────────────────────
      colors: {
        // Primary / structure
        ink:    "#12213A",   // deep ink navy — primary bg, headings
        paper:  "#FAF8F3",   // warm off-white — page background
        // Accent — used ONLY for things requiring human attention
        amber:  "#C48A2A",
        // Status
        approve: "#3A6B4C",  // muted forest green
        refer:   "#C48A2A",  // amber (same as accent)
        decline: "#8C3B2E",  // muted brick red
        // UI chrome
        border:  "#D6D0C4",
        muted:   "#8A8072",
        surface: "#F2EFE8",  // slightly darker than paper, for card backgrounds
      },
      fontFamily: {
        serif:  ["Lora", "Georgia", "serif"],
        sans:   ["Inter", "system-ui", "sans-serif"],
      },
      fontVariantNumeric: {
        tabular: "tabular-nums",
      },
      fontSize: {
        "2xs": ["0.65rem", "1rem"],
      },
    },
  },
  plugins: [],
};
