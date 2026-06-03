import path from 'node:path';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  root: 'audit-ui',
  plugins: [react()],
  resolve: {
    alias: {
      '@audit': path.resolve(__dirname, 'src/components/audit'),
    },
  },
  server: {
    port: 5173,
    strictPort: false,
    fs: {
      allow: [path.resolve(__dirname)],
    },
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
    },
  },
  preview: {
    port: 4173,
  },
  build: {
    outDir: '../dist/audit-ui',
    emptyOutDir: true,
  },
});
