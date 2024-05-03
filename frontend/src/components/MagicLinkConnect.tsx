import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { ActionIcon, Button, CopyButton, Flex, Input } from '@mantine/core';
import { IconClipboard } from '@tabler/icons-react';
import { createToast } from "./Toast";
import { MessageKind } from "../utils/common";
import { Text } from '@mantine/core'
import API from "../utils/const";
import { handleApiError } from "../utils/app";
import LoadingOverlay from "./LoadingOverlay";
function magicLinkFromUuid(uuid: string): string {
    return `https://calensync.live/dashboard?magic=${uuid}`
}

const MagicLinkConnect = () => {
    const { t } = useTranslation(["app"])
    const [clicked, setClicked] = useState(false);
    const [linkUuid, setLinkUuid] = useState(null)
    const [loading, setLoading] = useState(false);

    const copyToClipboard = () => {
        navigator.clipboard.writeText(magicLinkFromUuid(linkUuid));
        createToast(t("dashboard.link_copied"), MessageKind.Success);
    };

    const getMagicLink = async () => {
        try {
            const response = await fetch(`${API}/magic-link`,
                {
                    method: 'POST',
                    credentials: 'include'
                }
            )
            if(!response.ok){
                await handleApiError(response, t);
                setClicked(false);
                return
            }
            const content = await response.json()
            setLinkUuid(content.uuid)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        if (!clicked) { return; }
        getMagicLink();
    }, [clicked])

    const rightSection = (
        <ActionIcon variant="light" aria-label="Clibboard" onClick={copyToClipboard}>
            <IconClipboard style={{ width: '70%', height: '70%' }} stroke={1.5} />
        </ActionIcon>
    )

    return <>
        {loading && <LoadingOverlay/>}
        <div>
            {!clicked &&
                <Text size="sm" c="blue" td="underline" style={{ cursor: 'pointer' }} onClick={() => { setClicked(true) }}>{t("dashboard.connect_from_other_device")}</Text>

            }
            {linkUuid &&
                <>
                    <Input value={magicLinkFromUuid(linkUuid)} onChange={() => { }} rightSection={rightSection} rightSectionPointerEvents="all" />
                    <Text size="sm">{t("dashboard.connect_from_other_device_post")}</Text>
                </>
            }
        </div>
    </>
}

export default MagicLinkConnect;