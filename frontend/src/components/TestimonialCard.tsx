import React from 'react';

export const TestimonialCard: React.FC<{ t: any; idx: number; }> = ({ t, idx }) => {
//     const idx_to_name = [
//         "brian",
//         "father",
//         "arjun",
//         "federico",
//         "frederik",
//         "elena"
//     ]
    const key = `testimonials.${idx}`;
    return (
        <div className="card mb-3 shadow">
            <div className="p-3">
                <span className="testimonial-maintxt" dangerouslySetInnerHTML={{ __html: t(`${key}.message`) }}></span>
                <div className="d-flex pt-3">
                    {/* <div>
                        <img src={`assets/testimonials/${idx_to_name[idx]}.jpg`} width="50" className="rounded-circle" />
                    </div> */}
                    <div className="ms-2">
                        <span className="testimonial-name">{t(`${key}.author`)}</span>
                        <p className="testimonial-para mb-0">{t(`${key}.title`)}</p>
                    </div>
                </div>
            </div>
        </div>
    );
};
