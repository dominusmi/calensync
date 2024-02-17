import { Paddle } from "@paddle/paddle-js";
import { LineItem, Price } from "@paddle/paddle-js/types/price-preview/price-preview";
import { useEffect, useState } from "react";
import { TailSpin } from "react-loader-spinner";
import { PADDLE_PRICING } from "../utils/const";
import { useTranslation } from "react-i18next";


export const PaddlePricing: React.FC<{ paddle: Paddle | null, isHome: boolean, clickedBuy?: (price: Price) => void, isReady?: () => void }> = ({ isHome, clickedBuy, paddle, isReady }) => {
    const { t } = useTranslation();
    const [prices, setPrices] = useState<LineItem[]>([]);
    const [currentPrice, setCurrentPrice] = useState<number>(0);
    const [isChecked, setIsChecked] = useState(false);
    const [IP, setIP] = useState<string | null>(null)

    function onClick() {
        clickedBuy!(prices[currentPrice].price)
    }

    async function getIP() {
        try {
            const response = await fetch('https://api64.ipify.org?format=json');
            const data = await response.json();
            setIP(data.ip);
        } catch (error) {
            console.log(error);
        }
    }

    const getPricing = async () => {
        const pricings = PADDLE_PRICING!.split("|")
        try {
            // Make sure both state updates have taken place before calling paddle?.PricePreview
            if (paddle && IP) {
                return paddle.PricePreview({
                    items: [
                        { priceId: pricings[0], quantity: 1 },
                        { priceId: pricings[1], quantity: 1 }
                    ],
                    customerIpAddress: IP
                });
            }
        } catch (error) {
            console.error('Error in getPricing:', error);
        }
    }

    useEffect(() => {
        getIP();
    }, [])

    useEffect(() => {
        getPricing().then((pricings) => {
            if (pricings) {
                pricings.data.details.lineItems.sort((a, b) => parseInt(a.price.unitPrice.amount) - parseInt(b.price.unitPrice.amount))
                setPrices(pricings!.data.details.lineItems);
                if(isReady){
                    isReady();
                }
            }
        });
    // Disable lint because it's asking getPricing to be added (why?)
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [IP, isReady])


    const changePricingSwitch = () => {
        if (isChecked) {
            setCurrentPrice(0);
        } else {
            setCurrentPrice(1);
        }
        setIsChecked(!isChecked);
    }

    return (
        <div className="container centered content">
            <div className='row mb-4'>
                <div className="feature col">
                    <h2 className="display-4">Pricing</h2>
                    <p className='lead'>{t('paddle_pricing.free_trial')}</p>
                </div>
            </div>
            {isHome && prices.length === 0 && 
                <div className='d-flex justify-content-center'>
                <TailSpin
                height="80"
                width="80"
                color="#577CFF"
                ariaLabel="tail-spin-loading"
                radius="1"
                wrapperStyle={{}}
                wrapperClass=""
                visible={true}
              />
              </div>
            }
            {prices.length > 0 &&
                <div>
                    <div className="d-flex justify-content-center">
                        <h3 className="mb-0 mx-4">{t('paddle_pricing.monthly')}</h3>
                        <div className="pricing-switch form-check form-switch mx-4">
                            <input className="form-check-input" type="checkbox" role="switch" id="flexSwitchCheckDefault" checked={isChecked} onChange={changePricingSwitch} />
                        </div>
                        <h3 className="mb-0 ml-4">{t('paddle_pricing.yearly')}</h3><p className='text-muted mx-1 align-middle'>48% Off!</p>
                    </div>
                    <div className='row mt-3'>
                        <h2 className='fw-bold display-6 mb-0'>
                            {prices[currentPrice].formattedTotals.subtotal}
                        </h2>
                        <div>
                            {isHome &&
                                <p className='text-muted small mb-4'>{t('paddle_pricing.excluding_vat')}</p>
                            }
                        </div>

                        {!isHome &&
                            <div>
                                <p className='text-muted small mb-4'>{t('paddle_pricing.excluding_vat')} {prices[currentPrice].formattedTotals.tax}</p>
                                <div className="d-grid gap-2 d-md-flex justify-content-md-center mt-1">
                                    <button type="button" className="btn btn-primary btn-lg px-4 me-md-2" onClick={onClick}>{t('paddle_pricing.buy')}</button>
                                </div>
                            </div>
                        }
                    </div>
                </div>
            }
        </div>
    )
};
