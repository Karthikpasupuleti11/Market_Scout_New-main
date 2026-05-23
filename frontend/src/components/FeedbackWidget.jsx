import { useState } from "react";
import { HiOutlineChatAlt2, HiX } from "react-icons/hi";
import Skeleton from "react-loading-skeleton";
import 'react-loading-skeleton/dist/skeleton.css';
import "./FeedbackWidget.css";

export default function FeedbackWidget() {
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState("idle");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setStatus("submitting");

    const form = e.target;
    const data = new FormData(form);

    try {
      const endpoint = import.meta.env.VITE_FORMSPREE_ENDPOINT;
      const response = await fetch(endpoint, {
        method: "POST",
        body: data,
        headers: {
          Accept: "application/json",
        },
      });

      if (response.ok) {
        setStatus("success");
        form.reset();
        setTimeout(() => {
          setOpen(false);
          setStatus("idle");
        }, 3000);
      } else {
        setStatus("error");
      }
    } catch (error) {
      setStatus("error");
    }
  };

  return (
    <>
      <button
        className="feedback-btn"
        onClick={() => setOpen(!open)}
        aria-label="Toggle feedback form"
      >
        <HiOutlineChatAlt2 className="feedback-icon" /> Feedback
      </button>

      {open && (
        <div className="feedback-modal fade-in-up">
          <div className="feedback-header">
            <h3>Send Feedback</h3>
            <button className="feedback-close" onClick={() => setOpen(false)}>
              <HiX />
            </button>
          </div>

          {status === "success" ? (
            <div className="feedback-success fade-in-up">
              <svg className="feedback-success-icon" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="16" cy="16" r="14" stroke="var(--accent-primary)" strokeWidth="2" strokeDasharray="88" strokeDashoffset="88">
                  <animate attributeName="stroke-dashoffset" to="0" dur="0.5s" fill="freeze" />
                </circle>
                <path d="M10 16L14 20L22 12" stroke="var(--accent-primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" strokeDasharray="20" strokeDashoffset="20">
                  <animate attributeName="stroke-dashoffset" to="0" dur="0.4s" begin="0.4s" fill="freeze" />
                </path>
              </svg>
              <h4>Feedback Received</h4>
              <p>Thank you for your insights. Your input helps us refine the intelligence platform.</p>
            </div>
          ) : status === "submitting" ? (
            <div className="feedback-submitting fade-in-up">
              <p className="feedback-desc">Submitting your feedback...</p>
              <Skeleton 
                height={100} 
                borderRadius={14} 
                style={{ marginBottom: 16 }}
                baseColor="var(--bg-input)"
                highlightColor="var(--bg-card)"
              />
              <Skeleton 
                height={42} 
                borderRadius={10} 
                baseColor="var(--bg-input)"
                highlightColor="var(--bg-card)"
              />
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="feedback-form fade-in-up">
              <p className="feedback-desc">
                Have a suggestion or found a bug? Let us know!
              </p>
              <textarea
                name="feedback"
                placeholder="Share your thoughts..."
                required
                className="feedback-textarea"
              />
              {status === "error" && (
                <p className="feedback-error">Failed to send. Please try again.</p>
              )}
              <button
                type="submit"
                className="btn btn-primary feedback-submit"
              >
                Submit Feedback
              </button>
            </form>
          )}
        </div>
      )}
    </>
  );
}
