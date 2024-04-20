import Plausible from 'plausible-tracker';
import { createContext, useContext, ReactNode, FunctionComponent } from 'react';

interface IPlausibleContext {
    trackEvent: (event: string) => void;
}

export const PlausibleContext = createContext<IPlausibleContext | undefined>(undefined);

export const usePlausibleContext = () => {
    const context = useContext(PlausibleContext);
    if (context === undefined) {
        throw new Error('usePlausibleContext must be used within a PlausibleContextProvider');
    }
    return context;
};

export const PlausibleProvider: FunctionComponent<{ children: ReactNode}> = ({ children }) => {
    const { enableAutoPageviews, trackEvent } = Plausible({
        domain: "calensync.live",
        trackLocalhost: false,
        apiHost: "https://calensync.live"
    })
    enableAutoPageviews();
    
    return (
        <PlausibleContext.Provider value={{ trackEvent }}>
            {children}
        </PlausibleContext.Provider>
    );
};