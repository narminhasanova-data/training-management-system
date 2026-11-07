import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development the API, the public survey pages, the mock OAuth screen and the admin are served by
// Django on :8000; proxying keeps everything on one origin, as nginx does in docker-compose.
const backend = process.env.BACKEND_URL || "http://127.0.0.1:8000";
const proxied = ["/api", "/s/", "/oauth", "/admin", "/static", "/media"];

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: Object.fromEntries(proxied.map((p) => [p, { target: backend, changeOrigin: false }])) },
  preview: { port: 4173 },
});
