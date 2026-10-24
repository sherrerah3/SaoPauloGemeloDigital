import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    // En Docker sobre Windows o Mac los volúmenes no avisan de cambios: VITE_POLLING=1 activa el sondeo.
    watch: { usePolling: process.env.VITE_POLLING === "1" },
  },
});
