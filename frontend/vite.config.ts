import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  server: {
    host: "::",
    port: 8080,
  },
  plugins: [
    react(),
    mode === 'development' &&
    componentTagger(),
  ].filter(Boolean),
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    outDir: "dist",
    assetsDir: "assets",
    // Garantir que dependências problemáticas sejam processadas corretamente
    commonjsOptions: {
      include: [/@stripe\/stripe-js/, /node_modules/],
    },
    // Configuração do Rollup para lidar com o Stripe
    rollupOptions: {
      external: [],
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          stripe: ['@stripe/stripe-js']
        }
      }
    }
  },
  optimizeDeps: {
    include: ['@stripe/stripe-js']
  }
}));
