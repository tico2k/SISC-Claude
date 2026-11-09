import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import './index.css'
import './i18n' // i18n 초기화
import App from './App.tsx'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false, // 창 포커스 시 자동 재요청 방지
      retry: 1,
    },
  },
});

// Entra(MSAL)는 연동이 설정된 경우에만 로그인 화면에서 초기화한다 (config/msal.ts)
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
);
