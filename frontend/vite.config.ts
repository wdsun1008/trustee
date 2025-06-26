import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8081',
        changeOrigin: true,
      },
      // 代理阿里云通义千问 API
      '/proxy/dashscope': {
        target: 'https://dashscope.aliyuncs.com',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/proxy\/dashscope/, ''),
        headers: {
          'Origin': 'https://dashscope.aliyuncs.com',
        },
      },
      // 通用的 OpenAI 兼容 API 代理
      '/proxy/openai': {
        target: 'https://api.openai.com',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/proxy\/openai/, ''),
        headers: {
          'Origin': 'https://api.openai.com',
        },
      },
      // MCP 服务器代理
      '/mcp': {
        target: 'http://localhost:8085',
        changeOrigin: true,
        ws: true, // 支持WebSocket
        rewrite: (path) => {
          // 将 /mcp 重写为 /mcp/，保持路径结构
          const newPath = path.replace(/^\/mcp\/?/, '/mcp/');
          console.log('MCP代理路径重写:', path, '->', newPath);
          return newPath;
        },
        configure: (proxy, options) => {
          proxy.on('error', (err, req, res) => {
            console.log('MCP代理错误:', err);
          });
          proxy.on('proxyReq', (proxyReq, req, res) => {
            console.log('MCP代理请求:', req.method, req.url);
            // 添加MCP服务器需要的Accept头
            proxyReq.setHeader('Accept', 'application/json, text/event-stream');
            // 确保Content-Type正确
            if (req.headers['content-type']) {
              proxyReq.setHeader('Content-Type', req.headers['content-type']);
            }
          });
          proxy.on('proxyRes', (proxyRes, req, res) => {
            console.log('MCP代理响应:', proxyRes.statusCode, req.url);
          });
        },
      },
    },
  },
}) 