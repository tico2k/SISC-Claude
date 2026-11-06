import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { PublicClientApplication } from "@azure/msal-browser";
import { MsalProvider } from "@azure/msal-react";
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { msalConfig } from "./config/msal";
import './index.css'
import './i18n' // i18n 초기화
import App from './App.tsx'

const msalInstance = new PublicClientApplication(msalConfig);
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false, // 창 포커스 시 자동 재요청 방지
      retry: 1,
    },
  },
});

// MSALv3 이상은 초기화가 필수입니다.
msalInstance.initialize().then(() => {
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <QueryClientProvider client={queryClient}>
        <MsalProvider instance={msalInstance}>
          <App />
        </MsalProvider>
      </QueryClientProvider>
    </StrictMode>,
  );
});
