import axios from "axios";
import { createToast } from "../components/Toast";
import { useTranslation } from "react-i18next";
import { MessageKind } from "./common";
import { ENV } from "./const";

export const sendErrorToH2E = async (ev: any) => {
    if(ENV === "local"){ return }
    try {
        await axios.post(
            `https://api.hook2email.com/hook/4b262ccb-a724-4bf7-b362-092b7407dba0/send`,
            { error: JSON.stringify(ev, ["message", "arguments", "type", "name"]) },
            {
                headers: {
                    'Content-Type': 'application/json',
                },
            }
        );
    } catch (e) { }
}

export const handleApiError = async (response: Response, t: any) => {
    console.log("Handling error")
    const error = await response.json();
    createToast(error.message || t("common.internal-server-error"), MessageKind.Error);
}

export const getSearchParam = (name: string): string | null => {
    const params = new URLSearchParams(window.location.search)
    return params.get(name)
}