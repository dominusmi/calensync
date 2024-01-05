import { createToast } from "../components/Toast";

export interface ApiError {
    message: string
}

export enum MessageKind {
    Info = 1,
    Error = 2,
    Success = 3
}

export function setMessage(msg: string, kind: MessageKind){
    if(kind == MessageKind.Info){
        sessionStorage.setItem("info-msg", msg);
    }
    else if(kind == MessageKind.Error){
        sessionStorage.setItem("error-msg", msg);
    }
    else if(kind == MessageKind.Success){
        sessionStorage.setItem("success-msg", msg);
    }
}

export function consumeMessages(){
    const err = sessionStorage.getItem("error-msg");
    if(err){
        createToast(err, MessageKind.Error);
        sessionStorage.removeItem("error-msg")
    }

    const info = sessionStorage.getItem("info-msg");
    if(info){
        createToast(info, MessageKind.Info);
        sessionStorage.removeItem("info-msg")
    }

    const success = sessionStorage.getItem("success-msg");
    if(success){
        createToast(success, MessageKind.Success);
        sessionStorage.removeItem("success-msg")
    }
}

export function refreshPage(){
    window.location.reload()
}

export function refactorCalendarName(name: string){
    return name.replace("@group.v.calendar.google.com", "")
}

export function sleep(ms: number) {
    return new Promise( resolve => setTimeout(resolve, ms) );
}