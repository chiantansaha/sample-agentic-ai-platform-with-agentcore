import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0', // Docker 컨테이너에서 외부 접근 허용
    port: 5173,
    watch: {
      usePolling: true, // Docker volume mount에서 파일 변경 감지
    },
    proxy: {
      '/api': {
        target: process.env.VITE_API_BASE_URL || 'http://localhost:8000',
        changeOrigin: true,
        // SSE 스트리밍은 프론트엔드에서 직접 연결하므로 프록시는 일반 API만 처리
      }
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: undefined,
      },
    },
  },
  base: '/',
})
