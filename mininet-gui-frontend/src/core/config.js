const hostname = window.location.hostname;
const protocol = window.location.protocol;

export const backendHttpUrl = `${protocol}//${hostname}:4021`;
export const backendWsUrl = `ws://${hostname}:4021`;
