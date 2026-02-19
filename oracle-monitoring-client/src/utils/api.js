export const DEFAULT_API_URL = 'http://localhost:8000';

export const getApiUrl = () => {
    return localStorage.getItem('server_url') || DEFAULT_API_URL;
};

export const getWsUrl = () => {
    const apiUrl = getApiUrl();
    const protocol = apiUrl.startsWith('https') ? 'wss' : 'ws';
    const host = apiUrl.replace(/^https?:\/\//, '');
    return `${protocol}://${host}`;
};
