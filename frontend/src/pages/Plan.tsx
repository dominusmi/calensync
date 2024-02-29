import React, { useEffect, useState } from 'react';
import API, { ENV, PADDLE_CLIENT_TOKEN, PUBLIC_URL } from '../utils/const';
import { CheckoutEventNames, Paddle, PaddleEventData, initializePaddle } from '@paddle/paddle-js';
import Layout from '../components/Layout';
import { Price } from '@paddle/paddle-js/types/price-preview/price-preview';
import LoadingOverlay from '../components/LoadingOverlay';
import { getLoggedUser, User } from '../utils/session';
import { MessageKind, setMessage } from '../utils/common';
import { toast } from 'react-toastify';
import { createToast } from '../components/Toast';
import { PaddlePricing } from '../components/PaddlePricing';

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
  const [paddle, setPaddle] = useState<Paddle | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [user, setUser] = useState<User | null>(null);
  const [subscription, setSubscription] = useState<PaddleSubscription | null>(null);
  const [pricingLoaded, setPricingLoaded] = useState<boolean>(false);
  const [showPricing, setShowPricing] = useState(false);

  const updateStatePricing = () => {
    setPricingLoaded(true);
  };

  async function verifyTransactionId(transaction_id: string) {
    const response = await fetch(`${API}/paddle/verify_transaction?transaction_id=${transaction_id}`, {
      method: 'GET',
      credentials: 'include'
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
  }

  async function paddleCallback(event: PaddleEventData) {
    if (event.name === CheckoutEventNames.CHECKOUT_COMPLETED) {

      paddle?.Checkout.close();
      setIsLoading(true);
      try {
        const data = event.data!;
        const transaction_id = data.transaction_id;

        await verifyTransactionId(transaction_id)
      } finally {
        setIsLoading(false);
      }
      setMessage("You have succesfully subscribed!", MessageKind.Success);
      window.location.href = `${PUBLIC_URL}/plan`
    }
  }

  function buy(price: Price) {
    let args: any = {
      items: [{ priceId: price.id, quantity: 1 }]
    }
    if (user!.customer_id !== null) {
      args.customer = { id: user!.customer_id }
    }
    paddle?.Checkout.open(args);
  }

  const setupPaddle = async () => {
    try {
      const paddleInstance = await initializePaddle({ environment: ENV === "production" ? "production" : "sandbox", token: PADDLE_CLIENT_TOKEN, eventCallback: paddleCallback });
      if (paddleInstance) {
        setPaddle(paddleInstance);
      }
    }catch(e){
      createToast("Failed to initialize Paddle.js", MessageKind.Error);
      setIsLoading(false);
    }
  }

  useEffect(() => {
    Promise.all([
      setupPaddle(),
      getLoggedUser().then((user) => {
        setUser(user);
      })
    ])
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const getPricingOrSubscription = async () => {
    if (user == null) {
      return
    }
    if (user!.subscription_id !== null) {
      try {
        const response = await fetch(`${API}/paddle/subscription`, {
          method: 'GET',
          credentials: 'include'
        });

        if (!response.ok) {
          createToast("Error occured while fetching your subscription. If this continues, please contact support.", MessageKind.Error);
          return;
        }
        let data: PaddleSubscription = await response.json();
        data.next_billed_at = new Date(data.next_billed_at);
        setSubscription(data)
      } finally {
        setIsLoading(false);
      }
    } else {
      setIsLoading(true);
      if (user!.transaction_id !== null) {
        let iteration = 0;
        createToast("Transaction confirmed, verifying your subscription", MessageKind.Info);
        while (iteration < 3) {
          await verifyTransactionId(user!.transaction_id);
          let updatedUser = await getLoggedUser() as User;
          if (updatedUser.subscription_id !== null) {
            setUser(updatedUser);
            return
          }
          // wait one second before trying again
          await new Promise(resolve => setTimeout(resolve, 1000));
          iteration += 1;
        }
        setIsLoading(false);
        createToast("We were unable to confirm your subscription, but the transaction is confirmed. Please check this page again later", MessageKind.Error);
      }
      else {
        setShowPricing(true);
      }
    }
  }


  useEffect(() => {
    getPricingOrSubscription()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  useEffect(() => {
    if (pricingLoaded === true) {
      setIsLoading(false);
    }
  }, [pricingLoaded])

  return (
    <Layout onlyRequired={true}>
      {isLoading &&
        <LoadingOverlay />
      }
      <div className='content mt-4 pt-4'>
        {subscription != null &&
          <div className='container-sm card pt-3 px-4'>
            <h3>{subscription.items[0].price.description}</h3>
            <p>Next billing date: {subscription.next_billed_at.toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" })}</p>
            <p className='text-muted'>Want to cancel? Contact us at support@calensync.live</p>
          </div>
        }
        {paddle != null && showPricing === true &&
          <PaddlePricing paddle={paddle} clickedBuy={buy} isHome={false} isReady={updateStatePricing} />
        }
      </div>
    </Layout>
  );
};

export default Plan;