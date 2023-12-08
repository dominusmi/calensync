import React, { useEffect, useState } from 'react';
import API, { PADDLE_CLIENT_TOKEN, PUBLIC_URL } from '../utils/const';
import { CheckoutEventNames, Paddle, PaddleEventData, initializePaddle } from '@paddle/paddle-js';
import Layout from '../components/Layout';
import { LineItem } from '@paddle/paddle-js/types/price-preview/price-preview';
import LoadingOverlay from '../components/LoadingOverlay';
import { get_session_id, getLoggedUser, User } from '../utils/session';
import { MessageKind, setMessage } from '../utils/common';
import { toast } from 'react-toastify';
import { toast_msg } from '../components/Toast';

interface PaddleSubscription {
  status: string;
  next_billed_at: Date;
  management_urls: {
    update_payment_method: string;
    cancel: string;
  };
  is_active: boolean;
  items: {
    price: {
      description: string;
      unit_price: {
        amount: number;
      };
    };
  }[];
}

const Plan: React.FC = () => {
  const [prices, setPrices] = useState<LineItem[]>([]);
  const [currentPrice, setCurrentPrice] = useState<number>(0);
  const [isChecked, setIsChecked] = useState(false);
  const [paddle, setPaddle] = useState<Paddle | null>(null);
  const [IP, setIP] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [sessionChecked, setSessionChecked] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [subscription, setSubscription] = useState<PaddleSubscription | null>(null);

  const changePricingSwitch = () => {
    if (isChecked) {
      setCurrentPrice(0);
    } else {
      setCurrentPrice(1);
    }
    setIsChecked(!isChecked);
  }

  async function paddleCallback(event: PaddleEventData) {
    if (event.name == CheckoutEventNames.CHECKOUT_COMPLETED) {

      paddle?.Checkout.close();
      setIsLoading(true);
      try {
        const data = event.data!;
        const transaction_id = data.transaction_id;

        const response = await fetch(`${API}/paddle/verify_transaction?transaction_id=${transaction_id}`, {
          method: 'GET',
          headers: {
            Authorization: get_session_id()!,
          }
        });

        if (!response.ok) {
          toast.error(`Failed to verify transaction ${transaction_id} - this should mean no payment was made. If you believe there was, please email at support@calensync.live`, {
            position: 'top-center',
            autoClose: false,
            hideProgressBar: false,
            closeOnClick: true,
            pauseOnHover: true,
            draggable: true,
          })
          return
        }
      } finally {
        setIsLoading(false);
      }
      setMessage("You have succesfully subscribed!", MessageKind.Success);
      window.location.href = `${PUBLIC_URL}/plan`
    }
  }

  function buy() {
    let args: any = {
      items: [{ priceId: prices[currentPrice].price.id, quantity: 1 }]
    }
    if(user!.customer_id !== null){
      args.customer = {id: user!.customer_id}
    }
    paddle?.Checkout.open(args);
  }

  async function setupPaddle() {
    const paddleInstance = await initializePaddle({ environment: 'sandbox', token: PADDLE_CLIENT_TOKEN, eventCallback: paddleCallback });
    if (paddleInstance) {
      setPaddle(paddleInstance);
    }
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

  async function getPricing() {
    try {
      // Make sure both state updates have taken place before calling paddle?.PricePreview
      if (paddle && IP) {
        return paddle.PricePreview({
          items: [
            { priceId: "pri_01hgz5b0s7qtqt28zt4b5tp4s9", quantity: 1 },
            { priceId: "pri_01hgz5ahsecaqtrc7sxe6z23wy", quantity: 1 }
          ],
          customerIpAddress: IP
        });
      }
    } catch (error) {
      console.error('Error in getPricing:', error);
    }
  }

  useEffect(() => {
    Promise.all([
      getIP(),
      setupPaddle(),
      getLoggedUser().then((user) => {
        setSessionChecked(true);
        setUser(user);
      })
    ])
  }, []);

  const getPricingOrSubscription = async () => {
    if(user == null){
      return
    }
    if (user!.subscription_id !== null) {
      try {
        const response = await fetch(`${API}/paddle/subscription`, {
          method: 'GET',
          headers: {
            Authorization: get_session_id()!,
          }
        });
        
        if(!response.ok){
          toast_msg("Error occured while fetching your subscription. If this continues, please contact support.", MessageKind.Error);
          return ;
        }
        let data: PaddleSubscription = await response.json();
        data.next_billed_at = new Date(data.next_billed_at);
        setSubscription(data)
      } finally {
        setIsLoading(false);
      }
    }
    else {
      return getPricing().then((t) => {
        if (t) {
          t.data.details.lineItems.sort((a, b) => parseInt(a.price.unitPrice.amount) - parseInt(b.price.unitPrice.amount))
          setPrices(t!.data.details.lineItems);
          setIsLoading(false);
        }
      });
    }
  }

  useEffect(() => {
    getPricingOrSubscription()
  }, [IP, paddle, user]);

  return (
    <Layout>
      {isLoading &&
        <LoadingOverlay />
      }
      <div className='content mt-4 pt-4'>
        { subscription != null && 
          <div className='container-sm card pt-3 px-4'>
            <h3>{subscription.items[0].price.description}</h3>
            <p>Next billing date: {subscription.next_billed_at.toLocaleDateString(undefined, { year: "numeric",  month: "long",  day: "numeric" })}</p>
            <p className='text-muted'>Want to cancel? Contact us at support@calensync.live</p>
          </div>
        }
        {prices.length > 0 &&
          <div className="container centered content">
            <div className='container centered'>
              <div className='row mb-4'>
                <div className="feature col">
                  <h1>Pricing</h1>
                  <p className='lead'>Simple pricing for a simple product. 7 days free trial, no commitment, no credit card. Then..</p>
                </div>
              </div>
              <div className="d-flex justify-content-center">
                <h3 className="mb-0 mx-4">Monthly</h3>
                <div className="pricing-switch form-check form-switch mx-4">
                  <input className="form-check-input" type="checkbox" role="switch" id="flexSwitchCheckDefault" checked={isChecked} onChange={changePricingSwitch} />
                </div>
                <h3 className="mb-0 ml-4">Yearly</h3><p className='text-muted mx-1 align-middle'>48% Off!</p>
              </div>
              <div className='row mt-3'>
                <h2 className='fw-bold display-6 mb-0'>
                  {prices[currentPrice].formattedTotals.subtotal}$
                </h2>
                <p className='text-muted small mb-4'>*Excluding {prices[currentPrice].formattedTotals.tax} VAT</p>
                <div className="d-grid gap-2 d-md-flex justify-content-md-center mt-1">
                  <button type="button" className="btn btn-primary btn-lg px-4 me-md-2" onClick={buy}>Buy</button>
                </div>
              </div>
            </div>
          </div>
        }
      </div>
    </Layout>
  );
};

export default Plan;