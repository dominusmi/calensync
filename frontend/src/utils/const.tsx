export const API = import.meta.env.VITE_API_URL || ''; // Access the environment variable
export const ENV = import.meta.env.VITE_ENV!;

let url = ""
if(import.meta.env.VITE_PUBLIC_URL != null){
    url = import.meta.env.VITE_PUBLIC_URL;
}else{
    url = ENV === "development" ? '/dev' : '';
}
export const PUBLIC_URL = url;
export const PADDLE_CLIENT_TOKEN = import.meta.env.VITE_PADDLE_CLIENT_TOKEN!;
export const PADDLE_PRICING = import.meta.env.VITE_PADDLE_PRICING;

console.log(import.meta.env)
export default API