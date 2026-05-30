const hostname = window.location.hostname;
const protocol = window.location.protocol;

export const backendHttpUrl =
  import.meta.env.VITE_BACKEND_URL && import.meta.env.VITE_BACKEND_URL.length > 0
    ? import.meta.env.VITE_BACKEND_URL
    : `${protocol}//${hostname}:8000`;

export const backendWsUrl =
  import.meta.env.VITE_BACKEND_WS_URL && import.meta.env.VITE_BACKEND_WS_URL.length > 0
    ? import.meta.env.VITE_BACKEND_WS_URL
    : `ws://${hostname}:8000`;
