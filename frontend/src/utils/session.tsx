import API from "./const";

export enum VerifySession {
    OK = 0,
    INVALID = 1,
    TOS = 2
  }

export async function verify_session_id(): Promise<VerifySession> {
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

    console.log(response)
    if(response.status === 309){
      return VerifySession.TOS;
    }
    else if (!response.ok) {
      return VerifySession.INVALID;
    }
    return VerifySession.OK;
  } catch (error) {
    console.log(error)
    return VerifySession.INVALID;
  }
}

export function get_session_id() {
  // Implement the logic to retrieve the session ID from localStorage or wherever it is stored
  return localStorage.getItem("session-id")
}

export default verify_session_id;
