import React, { useEffect, useState } from 'react';
import 'bootstrap/dist/css/bootstrap.min.css';


interface Window {
  Tally: any; // Adjust the type accordingly based on the Tally library
  TallyConfig: any;
}


const ContactButton: React.FC<{onClick: () => void}> = ({onClick}) => {
  return (
    <div
      style={{
        position: 'fixed',
        bottom: '20px',
        right: '20px',
        zIndex: '1000',
      }}
    >
      <button onClick={onClick} style={{padding: "4px", borderRadius: '15px', backgroundColor: 'rgba(87, 124, 255, 0.3)', borderWidth: '0px'}} className="d-flex btn btn-primary justify-content-center">
        <img style={{padding: '5px'}} width={'40px'} height={'40px'} src="question.png"></img>
    </button>
    </div>
  );
};

export const TallyComponent = () => {
  const [tallyReady, setTallyReady] = useState(false);
  
  function showPopup(options: null | any = null) {
    if(options == null){
      options = {
        hideTitle: true,
        emoji: {
          text: '👋',
          animation: 'wave'
        }
      };
    }
    if(tallyReady){
      // Initialize Tally popup
      let win = (window as unknown) as Window;
      const tallyPopup = new win.Tally.openPopup("nroQgv", options);
      sessionStorage.setItem("feedback-shown", "true");
    }
  }

  useEffect(() => {
    // Dynamically create and append the script tag
    const script = document.createElement('script');
    script.src = 'https://tally.so/widgets/embed.js';
    script.async = true;
    document.head.appendChild(script);


    script.onload = () => {
      setTallyReady(true);
    }
  }, []);

  useEffect(() => {
    const feedbackShown = sessionStorage.getItem("feedback-shown");
    if(feedbackShown != null && feedbackShown === "true"){
      return
    }
    else{
      // Set up Tally configuration after script has loaded
      showPopup({
        hideTitle: true,
        emoji: {
          text: '👋',
          animation: 'wave'
        }
        ,
        open: {
          trigger: "time",
          ms: 15000
        }
      });
    }
  }, [tallyReady])

  return (
    <div id="tally-popup-container">
      {<ContactButton onClick={() => showPopup()}/>}
    </div>
  );
};

export default TallyComponent;