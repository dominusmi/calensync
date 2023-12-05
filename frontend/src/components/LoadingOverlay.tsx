import { TailSpin } from 'react-loader-spinner';

const LoadingOverlay = () => {
  return (
    <div className='loading-overlay'>
    <div className='loading-spinner-container'>
      <TailSpin
        height="80"
        width="80"
        color="#4fa94d"
        ariaLabel="tail-spin-loading"
        radius="1"
        wrapperStyle={{}}
        wrapperClass=""
        visible={true}
      />
    </div>
    </div>
  );
};

export default LoadingOverlay;
