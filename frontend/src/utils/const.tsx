export const API = process.env.REACT_APP_API_URL || ''; // Access the environment variable
export const ENV = process.env.REACT_APP_ENV!;

let url = ""
if(process.env.REACT_APP_PUBLIC_URL != null){
    url = process.env.REACT_APP_PUBLIC_URL;
}else{
    url = ENV === "development" ? '/dev' : '';
}
export const PUBLIC_URL = url;
console.log(PUBLIC_URL);
export const PADDLE_CLIENT_TOKEN = process.env.REACT_APP_PADDLE_CLIENT_TOKEN!;
export const PADDLE_PRICING = process.env.REACT_APP_PADDLE_PRICING;

export default API