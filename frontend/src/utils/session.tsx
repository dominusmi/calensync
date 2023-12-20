import API, { PUBLIC_URL } from "./const";

export enum VerifySession {
  INVALID = 1,
  TOS = 2,
  LOGIN = 3
}

export interface User {
  customer_id: string | null;
  date_created: Date;
  subscription_id: string | null;
  transaction_id: string | null;
}

export async function whoami() {
  try {
    const response = await fetch(`${API}/whoami`, {
      method: 'GET',
      credentials: 'include'
    });

    if (response.status === 309) {
      return VerifySession.TOS;
    }
    else if (!response.ok) {
      if (response.status == 403) {
        removeLocalSession()
        return VerifySession.LOGIN;
      }
      removeLocalSession()
      return VerifySession.INVALID;
    }
    let user = await response.json();
    
    user.date_created = new Date(user.date_created);
    setLocalSession(user);
    return user;

  } catch (error) {
    removeLocalSession()
    return VerifySession.INVALID;
  }
}

export async function optimisticIsConnected(): Promise<boolean> {
  const session_id = getLocalSession();
  if(session_id == null) {
    let response = await whoami();
    if(typeof response === 'number'){
      return false;
    }
  }
  return true;
}

export function setLocalSession(user: User) {
  return sessionStorage.setItem("session-id", JSON.stringify(user))
}

export function getLocalSession() {
  // Implement the logic to retrieve the session ID from localStorage or wherever it is stored
  return sessionStorage.getItem("session-id")
}

export function removeLocalSession() {
  sessionStorage.removeItem("session-id")
}

export const getLoggedUser: () => Promise<User> = async () => {
  let result = await whoami();
  if (result == VerifySession.TOS) {
    window.location.href = `${PUBLIC_URL}/tos?logged=true`;
    result = {date_created: new Date()}
  } else if (result == VerifySession.LOGIN || result == VerifySession.INVALID) {
    window.location.replace(`${PUBLIC_URL}/login`);
    result = {date_created: new Date()} as User;
  }
  return result as User;
}

export async function logout() {
  removeLocalSession();
  return fetch(`${API}/logout`, {
    method: 'GET',
    credentials: 'include'
  });
}
