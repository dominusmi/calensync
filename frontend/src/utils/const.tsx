export const API = process.env.REACT_APP_API_URL || ''; // Access the environment variable
export const ENV = process.env.REACT_APP_ENV!;
export const PUBLIC_URL = ENV == "development" ? '/dev' : '';
export const PADDLE_CLIENT_TOKEN = process.env.REACT_APP_PADDLE_CLIENT_TOKEN!;
export const PADDLE_PRICING = process.env.REACT_APP_PADDLE_PRICING;

export default API