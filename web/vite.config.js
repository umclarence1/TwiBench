import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development (npm run dev) API calls go to the Python server.
// It prints its address on start (first free port from 7860); change this if it differs.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://127.0.0.1:7860" } },
});
