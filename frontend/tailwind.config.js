/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // REQ-5.2 risk scale. Shared with the PDF renderer's palette so the
        // web view and the export cannot drift apart.
        safe: { bg: "#EAF5EE", fg: "#1B7F4B", border: "#A8D8BC" },
        caution: { bg: "#FDF3E3", fg: "#B26A00", border: "#EFD09B" },
        danger: { bg: "#FBEAE8", fg: "#B3261E", border: "#EEB4AE" },
        muted: { bg: "#F1F3F4", fg: "#5F6368", border: "#DADCE0" },
      },
    },
  },
  plugins: [],
};
