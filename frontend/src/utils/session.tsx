import { MessageKind, setMessage } from "./common";
import API, { PUBLIC_URL } from "./const";

export enum VerifySession {
  INVALID = 1,
  TOS = 2,
  LOGIN = 3
}

export interface User {
  customer_id: string;
  date_created: Date;
  subscription_id: string | null;
}

export async function verify_session_id(): Promise<VerifySession | User> {
  const session_id = get_session_id();

  if (session_id == null) {
    return VerifySession.INVALID;
  }

  try {
    const response = await fetch(`${API}/whoami`, {
      method: 'GET',
      headers: {
        Authorization: session_id,
      },
    });

    if (response.status === 309) {
      return VerifySession.TOS;
    }
    else if (!response.ok) {
      if (response.status == 403) {
        localStorage.removeItem("session-id")
        return VerifySession.LOGIN;
      }
      return VerifySession.INVALID;
    }
    let user = await response.json();
    user.date_created = new Date(user.date_created);
    return user;

  } catch (error) {
    return VerifySession.INVALID;
  }
}

export function get_session_id() {
  // Implement the logic to retrieve the session ID from localStorage or wherever it is stored
  return localStorage.getItem("session-id")
}


export const getLoggedUser: () => Promise<User> = async () => {
  const result = await verify_session_id();
  if (result == VerifySession.TOS) {
    setMessage("Must accept Terms of Use", MessageKind.Info)
    window.location.href = `${PUBLIC_URL}/tos`;
  } else if (result == VerifySession.LOGIN || result === VerifySession.INVALID) {
    window.location.href = `${PUBLIC_URL}/login`;
  }
  return result as User;
}

export default verify_session_id;
