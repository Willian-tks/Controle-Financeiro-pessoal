import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/auth": "http://127.0.0.1:8000",
      "/me": "http://127.0.0.1:8000",
      "/workspaces": "http://127.0.0.1:8000",
      "/admin": "http://127.0.0.1:8000",
      "/accounts": "http://127.0.0.1:8000",
      "/cards": "http://127.0.0.1:8000",
      "/card-invoices": "http://127.0.0.1:8000",
      "/categories": "http://127.0.0.1:8000",
      "/lists": "http://127.0.0.1:8000",
      "/items": "http://127.0.0.1:8000",
      "/dashboard": "http://127.0.0.1:8000",
      "/transactions": "http://127.0.0.1:8000",
      "/credit-commitments": "http://127.0.0.1:8000",
      "/invest": "http://127.0.0.1:8000",
      "/import": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
    },
  },
});
