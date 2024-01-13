import React from 'react';

export const TestimonialCard: React.FC<{ t: any; idx: number; }> = ({ t, idx }) => {
    const lorem = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.";
    const key = `testimonials.${idx}`;
    return (
        <div className="card mb-3">
            <div className="px-2 pt-2">
                <span className="testimonial-maintxt" dangerouslySetInnerHTML={{ __html: t(`${key}.message`) }}></span>
                <div className="d-flex pt-3">
                    {/* <div><img src="https://i.imgur.com/hczKIze.jpg" width="50" className="rounded-circle" /></div> */}
                    <div className="ms-2">
                        <span className="testimonial-name">{t(`${key}.author`)}</span>
                        <p className="testimonial-para">{t(`${key}.title`)}</p>
                    </div>
                </div>
            </div>
        </div>
    );
};
