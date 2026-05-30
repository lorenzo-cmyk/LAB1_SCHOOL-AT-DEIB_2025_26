const hostname = window.location.hostname;
const protocol = window.location.protocol;

export const backendHttpUrl = `${protocol}//${hostname}:8000`;
export const backendWsUrl = `ws://${hostname}:8000`;
