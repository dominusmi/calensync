import API, { PUBLIC_URL } from "./const";

export enum VerifySession {
  MISSING = 1,
  TOS = 2,
  EXPIRED = 3
}

export interface User {
  uuid: string;
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
      removeLocalSession()
      if (response.status == 403) {
        return VerifySession.EXPIRED;
      }
      return VerifySession.MISSING;
    }
    let user = await response.json();
    
    user.date_created = new Date(user.date_created);
    setLocalSession(user);
    return user;

  } catch (error) {
    removeLocalSession()
    return VerifySession.MISSING;
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
  sessionStorage.setItem("user-id", user.uuid)
  return sessionStorage.setItem("session-id", JSON.stringify(user))
}

export function getLocalSession() {
  // Implement the logic to retrieve the session ID from localStorage or wherever it is stored
  return sessionStorage.getItem("session-id")
}

export function getLocalUserId(){
  return sessionStorage.getItem("user-id")
}

export function removeLocalSession() {
  sessionStorage.removeItem("user-id")
  sessionStorage.removeItem("session-id")
}

export const getLoggedUser: () => Promise<User | null> = async () => {
  let result = await whoami();
  if (result == VerifySession.TOS) {
    window.location.href = `${PUBLIC_URL}/tos?logged=true`;
    result = {date_created: new Date()}
  } else if (result == VerifySession.MISSING) {
    return null;
  }else if (result == VerifySession.EXPIRED){
    window.location.replace(`${PUBLIC_URL}/login?login=true&msg=${btoa("Session expired")}`);
    return null;
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
