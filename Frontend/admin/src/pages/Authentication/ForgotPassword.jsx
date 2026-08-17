import React, { useState, useEffect, useRef } from "react";
import AuthBg from "../../assets/Before-Login/Auth.png";
import { showToast } from "../../components/Toast";
import { ArrowLeft } from "lucide-react";
import { useNavigate } from "react-router-dom";
import api from "../../utils/axiosConfig";

const ForgotPassword = () => {
    const navigate = useNavigate();
    const [email, setEmail] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [emailError, setEmailError] = useState(false);
    const [isSubmitted, setIsSubmitted] = useState(false);
    const [emailTouched, setEmailTouched] = useState(false);

    // State for counting animation
    const [counts, setCounts] = useState({
        accuracy: 0,
        growth: 0,
        inventory: 0
    });
    const intervalRef = useRef(null);

    // Validate email format
    const validateEmail = (email) => {
        const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
        return emailRegex.test(email);
    };

    const handleEmailChange = (e) => {
        const value = e.target.value;
        setEmail(value);
        setEmailTouched(true);
        if (value && !validateEmail(value)) {
            setEmailError(true);
        } else {
            setEmailError(false);
        }
    };

    const handleResetPassword = async (e) => {
        e.preventDefault();
        
        setEmailTouched(true);
        setEmailError(false);

        if (!email) {
            setEmailError(true);
            showToast.error("Please enter your email address");
            return;
        }

        if (!validateEmail(email)) {
            setEmailError(true);
            showToast.error("Please enter a valid email address with proper domain (e.g., .com, .in, .org)!");
            return;
        }

        setIsLoading(true);
        const toastId = showToast.loading("Sending OTP...");

        try {
            // Call the backend API to request password reset OTP
            const response = await api.post("/auth/forgot-password", {
                email: email
            });

            // Check if OTP was sent successfully
            if (response.data && response.data.message) {
                setIsSubmitted(true);
                
                // Store email in session storage for OTP verification
                sessionStorage.setItem('reset_email', email);
                
                showToast.update(toastId, {
                    render: `✅ ${response.data.message}`,
                    type: "success",
                    isLoading: false,
                    autoClose: 2000,
                });

                // Redirect to OTP page after 2 seconds
                setTimeout(() => {
                    navigate("/otp", { state: { email: email } });
                }, 2000);
            } else {
                throw new Error("Invalid response from server");
            }

        } catch (error) {
            // Handle different error scenarios
            let errorMessage = "❌ Failed to send OTP. Please try again.";
            
            if (error.response) {
                // The request was made and the server responded with a status code
                if (error.response.status === 400) {
                    errorMessage = `❌ ${error.response.data.detail || "Invalid email address. Please check and try again."}`;
                } else if (error.response.status === 429) {
                    errorMessage = "⚠️ Too many requests. Please wait a moment and try again.";
                } else if (error.response.status === 404) {
                    errorMessage = "❌ Email address not found. Please check your email or sign up.";
                } else if (error.response.data && error.response.data.detail) {
                    errorMessage = `❌ ${error.response.data.detail}`;
                }
            } else if (error.request) {
                // The request was made but no response was received
                errorMessage = "❌ Server is not responding. Please check your connection.";
            } else {
                // Something happened in setting up the request
                errorMessage = `❌ ${error.message}`;
            }
            
            setIsSubmitted(false);
            
            showToast.update(toastId, {
                render: errorMessage,
                type: "error",
                isLoading: false,
                autoClose: 4000,
            });
        } finally {
            setIsLoading(false);
        }
    };

    const handleBackToLogin = () => {
        navigate("/login");
    };

    // Handle resend OTP
    const handleResendOTP = async () => {
        if (!email) {
            setEmailError(true);
            setEmailTouched(true);
            showToast.warning("Please enter your email address first!");
            return;
        }
        
        if (!validateEmail(email)) {
            setEmailError(true);
            showToast.error("Please enter a valid email address!");
            return;
        }
        
        const toastId = showToast.loading("Resending OTP...");
        
        try {
            // Call the backend API to resend OTP
            const response = await api.post("/auth/forgot-password", {
                email: email
            });
            
            if (response.data && response.data.message) {
                showToast.update(toastId, {
                    render: `✅ ${response.data.message}`,
                    type: "success",
                    isLoading: false,
                    autoClose: 3000,
                });
                
                // Update the session storage
                sessionStorage.setItem('reset_email', email);
            } else {
                throw new Error("Invalid response from server");
            }
        } catch (error) {
            let errorMessage = "❌ Failed to resend OTP. Please try again.";
            
            if (error.response && error.response.data && error.response.data.detail) {
                errorMessage = `❌ ${error.response.data.detail}`;
            } else if (error.response && error.response.status === 429) {
                errorMessage = "⚠️ Too many requests. Please wait a moment and try again.";
            }
            
            showToast.update(toastId, {
                render: errorMessage,
                type: "error",
                isLoading: false,
                autoClose: 4000,
            });
        }
    };

    // Counting animation effect
    useEffect(() => {
        const targetValues = {
            accuracy: 95,
            growth: 20.3,
            inventory: 21.3
        };

        const startDelay = setTimeout(() => {
            const duration = 2000;
            const steps = 60;
            const stepDuration = duration / steps;
            let currentStep = 0;

            const increments = {
                accuracy: targetValues.accuracy / steps,
                growth: targetValues.growth / steps,
                inventory: targetValues.inventory / steps
            };

            intervalRef.current = setInterval(() => {
                currentStep++;
                
                if (currentStep >= steps) {
                    setCounts({
                        accuracy: targetValues.accuracy,
                        growth: targetValues.growth,
                        inventory: targetValues.inventory
                    });
                    clearInterval(intervalRef.current);
                } else {
                    setCounts(prev => ({
                        accuracy: Math.min(prev.accuracy + increments.accuracy, targetValues.accuracy),
                        growth: Math.min(prev.growth + increments.growth, targetValues.growth),
                        inventory: Math.min(prev.inventory + increments.inventory, targetValues.inventory)
                    }));
                }
            }, stepDuration);
        }, 500);

        return () => {
            clearTimeout(startDelay);
            if (intervalRef.current) {
                clearInterval(intervalRef.current);
            }
        };
    }, []);

    // Format the display values
    const formatValue = (value, type) => {
        if (type === 'accuracy') {
            return `> ${Math.round(value)}%`;
        }
        if (type === 'growth') {
            return `+${value.toFixed(1)}%`;
        }
        if (type === 'inventory') {
            return `-${value.toFixed(1)}%`;
        }
        return value;
    };

    // Metric data with SVG icons
    const metrics = [
        {
            id: 1,
            value: formatValue(counts.accuracy, 'accuracy'),
            label: "Forecast Accuracy",
            color: "#4ADE80",
            bgColor: "rgba(74, 222, 128, 0.12)",
            borderColor: "rgba(74, 222, 128, 0.25)",
            zigZagOffset: 230,
            verticalOffset: -30,
            svg: (
                <svg width="50" height="50" viewBox="0 0 120 120" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="60" cy="60" r="42" stroke="#4ADE80" strokeWidth="6"/>
                    <circle cx="60" cy="60" r="22" stroke="#4ADE80" strokeWidth="6"/>
                    <circle cx="60" cy="60" r="8" fill="#4ADE80"/>
                    <path
                        d="M3 102L36 69"
                        stroke="#4ADE80"
                        strokeWidth="6"
                        strokeLinecap="round"
                    />
                    <path
                        d="M3 102H18"
                        stroke="#4ADE80"
                        strokeWidth="6"
                        strokeLinecap="round"
                    />
                    <path
                        d="M3 102V87"
                        stroke="#4ADE80"
                        strokeWidth="6"
                        strokeLinecap="round"
                    />
                </svg>
            )
        },
        {
            id: 2,
            value: formatValue(counts.growth, 'growth'),
            label: "Revenue Growth",
            color: "#FAB51B",
            bgColor: "rgba(250, 181, 27, 0.12)",
            borderColor: "rgba(250, 181, 27, 0.25)",
            zigZagOffset: -50,
            verticalOffset: 0,
            svg: (
                <svg width="50" height="35" viewBox="0 0 140 92" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path
                        d="M4 88L55 37L80 62L132 10M94 10H132V48"
                        stroke="#FAB51B"
                        strokeWidth="8"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                    />
                </svg>
            )
        },
        {
            id: 3,
            value: formatValue(counts.inventory, 'inventory'),
            label: "Excess Inventory",
            color: "#14B8A6",
            bgColor: "rgba(20, 184, 166, 0.12)",
            borderColor: "rgba(20, 184, 166, 0.25)",
            zigZagOffset: 380,
            verticalOffset: 30,
            svg: (
                <svg width="50" height="35" viewBox="0 0 140 92" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path
                        d="M4 4L55 55L80 30L132 82H94M132 82V44"
                        stroke="#14B8A6"
                        strokeWidth="8"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                    />
                </svg>
            )
        }
    ];

    return (
        <section
            className="h-screen w-full bg-cover bg-center bg-no-repeat flex items-center justify-end relative"
            style={{ backgroundImage: `url(${AuthBg})` }}
        >
            {/* Logo - Fixed positioning to show in top-left */}
            <div className="absolute top-8 left-8 z-50 flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-[#FF6A00] flex items-center justify-center">
                    <svg
                        width="18"
                        height="18"
                        viewBox="0 0 24 24"
                        fill="none"
                        xmlns="http://www.w3.org/2000/svg"
                    >
                        <rect x="3" y="13" width="4" height="8" rx="1" fill="white" />
                        <rect x="10" y="8" width="4" height="13" rx="1" fill="white" />
                        <rect x="17" y="3" width="4" height="18" rx="1" fill="white" />
                    </svg>
                </div>

                <span className="w-[114px] h-6 font-inter font-bold text-[16px] leading-6 tracking-[0.64px]">
                    <span className="text-white">AI </span>
                    <span className="text-[#FF6A00]">FORECAST</span>
                </span>
            </div>

            {/* Metric Boxes - Zig Zag Pattern on Left Side */}
            <div className="absolute left-[80px] top-1/2 -translate-y-1/2 flex flex-col gap-6 metric-container">
                {metrics.map((metric, index) => (
                    <div
                        key={metric.id}
                        className="relative transition-all duration-300 hover:scale-105 hover:shadow-2xl metric-item"
                        style={{
                            transform: `translateX(${metric.zigZagOffset}px) translateY(${metric.verticalOffset || 0}px)`,
                        }}
                    >
                        <div
                            className="rounded-2xl px-6 py-3 backdrop-blur-sm metric-card flex items-center justify-between"
                            style={{
                                background: `linear-gradient(135deg, ${metric.bgColor}, rgba(255,255,255,0.05))`,
                                border: `1px solid ${metric.borderColor}`,
                                boxShadow: `0 8px 32px rgba(0,0,0,0.15), inset 0 1px 0 rgba(255,255,255,0.1)`,
                                width: "260px",
                                minHeight: "70px",
                            }}
                        >
                            <div className="flex flex-col">
                                <span
                                    className="text-2xl font-bold metric-value transition-all duration-300"
                                    style={{ color: metric.color }}
                                >
                                    {metric.value}
                                </span>
                                <span className="text-xs text-white/70 mt-0.5 font-medium tracking-wide metric-label">
                                    {metric.label}
                                </span>
                            </div>
                            <div className="metric-svg ml-4">
                                {metric.svg}
                            </div>
                        </div>

                        {/* Zig-zag connecting dots between metrics */}
                        {index < metrics.length - 1 && (
                            <div
                                className="absolute -bottom-4 left-1/2 transform -translate-x-1/2 w-0.5 h-6"
                                style={{
                                    background: `linear-gradient(to bottom, ${metric.color}, ${metrics[index + 1].color})`,
                                    opacity: 0.3,
                                }}
                            />
                        )}
                    </div>
                ))}
            </div>

            {/* Forgot Password Form */}
            <div
                className="mr-[24px] rounded-[20px] p-10 backdrop-blur-md flex flex-col relative z-10 forgot-form"
                style={{
                    background:
                        "linear-gradient(322.91deg, rgba(255, 106, 0, 0.15) 0.68%, rgba(20, 184, 166, 0.15) 99.32%)",
                    boxShadow: "0px 0px 6px 0px #14B8A6, 0px 0px 2px 0px #FF6A00",
                    width: "481px",
                }}
            >
                {/* Back Button */}
                <button
                    onClick={handleBackToLogin}
                    className="flex items-center gap-2 text-white/60 hover:text-white transition mb-2 cursor-pointer"
                >
                    <ArrowLeft size={20} />
                    <span className="text-sm">Back to Login</span>
                </button>

                {/* Top */}
                <div className="form-header">
                    <h1 className="text-[26px] font-bold leading-[39px] tracking-[0px] text-white welcome-title">
                        Forgot Password
                    </h1>
                    <p className="mt-2 text-[14px] font-normal leading-[21px] tracking-[1px] text-[#FAB51B] welcome-subtitle">
                        Please enter your email to reset the password
                    </p>
                </div>

                {/* Form */}
                <form onSubmit={handleResetPassword} className="form-container">
                    {/* Email Input */}
                    <div className="form-group">
                        <label className="block text-sm font-medium text-white/80 mb-2 input-label">
                            Email Address
                        </label>
                        <div className="relative">
                            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                <svg
                                    width="20"
                                    height="20"
                                    viewBox="0 0 24 24"
                                    fill="none"
                                    stroke="white"
                                    strokeWidth="1.5"
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    className="opacity-60 input-icon"
                                >
                                    <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                                    <polyline points="22,6 12,13 2,6" />
                                </svg>
                            </div>
                            <input
                                type="email"
                                placeholder="admin@demandai.pro"
                                value={email}
                                onChange={handleEmailChange}
                                onBlur={() => {
                                    setEmailTouched(true);
                                    if (email && !validateEmail(email)) {
                                        setEmailError(true);
                                    }
                                }}
                                className={`w-full rounded-lg border ${emailError && emailTouched ? "border-red-500" : "border-white/20"} 
                                    bg-white/10 pl-10 pr-4 py-3 text-white placeholder:text-white/60 
                                    outline-none focus:border-[#14B8A6] transition form-input`}
                                disabled={isLoading || isSubmitted}
                            />
                        </div>
                        {emailError && emailTouched && !email && (
                            <p className="text-red-500 text-xs mt-1 error-text">
                                Email required
                            </p>
                        )}
                        {emailError && emailTouched && email && !validateEmail(email) && (
                            <p className="text-red-500 text-xs mt-1 error-text">
                                Please enter a valid email (e.g., user@domain.com)
                            </p>
                        )}
                    </div>

                    {/* Success Message - Show when OTP is sent */}
                    {isSubmitted && (
                        <div className="bg-green-500/20 border border-green-500/50 rounded-lg p-3 text-green-400 text-sm text-center">
                            ✅ OTP sent successfully! Redirecting to verification...
                        </div>
                    )}

                    {/* Reset Password Button */}
                    <button
                        type="submit"
                        disabled={isLoading || isSubmitted}
                        className="w-full cursor-pointer rounded-lg py-3 font-semibold text-white transition duration-300 hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 reset-button"
                        style={{
                            background: "linear-gradient(135deg, #FF6A00 0%, #FF7A1A 100%)",
                        }}
                    >
                        {isLoading ? (
                            <>
                                <svg
                                    className="animate-spin h-5 w-5"
                                    xmlns="http://www.w3.org/2000/svg"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                >
                                    <circle
                                        className="opacity-25"
                                        cx="12"
                                        cy="12"
                                        r="10"
                                        stroke="currentColor"
                                        strokeWidth="4"
                                    />
                                    <path
                                        className="opacity-75"
                                        fill="currentColor"
                                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                                    />
                                </svg>
                                Sending OTP...
                            </>
                        ) : isSubmitted ? (
                            "OTP Sent ✓"
                        ) : (
                            <>
                                Send OTP
                                <svg
                                    width="20"
                                    height="20"
                                    viewBox="0 0 24 24"
                                    fill="none"
                                    stroke="currentColor"
                                    strokeWidth="2"
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                >
                                    <path d="M5 12h14" />
                                    <path d="M12 5l7 7-7 7" />
                                </svg>
                            </>
                        )}
                    </button>

                    {/* Resend OTP - Show when OTP is sent */}
                    {isSubmitted && (
                        <button
                            type="button"
                            onClick={handleResendOTP}
                            className="text-center text-sm text-[#FAB51B] hover:text-[#FF6A00] transition cursor-pointer w-full"
                            disabled={isLoading}
                        >
                            Didn't receive OTP? Resend OTP
                        </button>
                    )}

                    {/* Terms */}
                    <div className="text-center text-sm text-white/70 terms-text">
                        Remember your password?{" "}
                        <span 
                            onClick={handleBackToLogin}
                            className="text-[#FF6A00] hover:underline cursor-pointer"
                        >
                            Back to Login
                        </span>
                    </div>
                </form>
            </div>

            <style jsx>{`
                /* Form container */
                .form-container {
                    display: flex;
                    flex-direction: column;
                    gap: 20px;
                    margin-top: 40px;
                }

                /* Individual form group spacing */
                .form-group {
                    display: flex;
                    flex-direction: column;
                    gap: 0px;
                }

                /* Terms text */
                .terms-text {
                    margin-top: 0;
                }

                /* Metric SVG styling */
                .metric-svg {
                    opacity: 0.6;
                    flex-shrink: 0;
                    display: flex;
                    align-items: center;
                }

                /* Responsive styles for < 1280px */
                @media (max-width: 1280px) {
                    .metric-card {
                        width: 200px !important;
                        min-height: 60px !important;
                        padding: 10px 16px !important;
                    }

                    .metric-value {
                        font-size: 18px !important;
                    }

                    .metric-label {
                        font-size: 10px !important;
                    }

                    .metric-svg svg {
                        width: 40px !important;
                        height: 30px !important;
                    }

                    .metric-item:first-child {
                        transform: translateX(290px) translateY(-100px) !important;
                    }

                    .metric-item:last-child {
                        transform: translateX(460px) translateY(140px) !important;
                    }

                    .metric-container {
                        gap: 4px !important;
                    }

                    .forgot-form {
                        width: 400px !important;
                        padding: 24px !important;
                    }

                    .form-container {
                        gap: 16px !important;
                        margin-top: 32px !important;
                    }

                    .welcome-title {
                        font-size: 22px !important;
                        line-height: 32px !important;
                    }

                    .welcome-subtitle {
                        font-size: 12px !important;
                        line-height: 18px !important;
                        margin-top: 6px !important;
                    }

                    .input-label {
                        font-size: 12px !important;
                        margin-bottom: 4px !important;
                    }

                    .form-input {
                        padding-top: 10px !important;
                        padding-bottom: 10px !important;
                        font-size: 13px !important;
                        padding-left: 36px !important;
                    }

                    .input-icon {
                        width: 16px !important;
                        height: 16px !important;
                    }

                    .reset-button {
                        padding-top: 10px !important;
                        padding-bottom: 10px !important;
                        font-size: 14px !important;
                    }

                    .terms-text {
                        font-size: 11px !important;
                    }

                    .error-text {
                        font-size: 10px !important;
                        margin-top: 2px !important;
                    }
                }

                /* Further reduce for tablets */
                @media (max-width: 1024px) {
                    .metric-card {
                        width: 160px !important;
                        min-height: 50px !important;
                        padding: 8px 12px !important;
                    }

                    .metric-value {
                        font-size: 16px !important;
                    }

                    .metric-label {
                        font-size: 9px !important;
                    }

                    .metric-svg svg {
                        width: 30px !important;
                        height: 25px !important;
                    }

                    .metric-item:first-child {
                        transform: translateX(230px) translateY(-70px) !important;
                    }

                    .metric-item:last-child {
                        transform: translateX(280px) translateY(90px) !important;
                    }

                    .forgot-form {
                        width: 340px !important;
                        padding: 20px !important;
                    }

                    .form-container {
                        gap: 14px !important;
                        margin-top: 28px !important;
                    }

                    .welcome-title {
                        font-size: 20px !important;
                        line-height: 28px !important;
                    }

                    .welcome-subtitle {
                        font-size: 11px !important;
                    }

                    .form-input {
                        font-size: 12px !important;
                        padding-top: 8px !important;
                        padding-bottom: 8px !important;
                    }

                    .reset-button {
                        font-size: 13px !important;
                        padding-top: 8px !important;
                        padding-bottom: 8px !important;
                    }

                    .terms-text {
                        font-size: 10px !important;
                    }
                }

                /* Mobile */
                @media (max-width: 768px) {
                    .metric-card {
                        display: none !important;
                    }

                    .forgot-form {
                        width: 300px !important;
                        padding: 16px !important;
                        margin-right: 12px !important;
                    }

                    .welcome-title {
                        font-size: 18px !important;
                        line-height: 24px !important;
                    }

                    .welcome-subtitle {
                        font-size: 11px !important;
                    }

                    .form-container {
                        gap: 12px !important;
                        margin-top: 24px !important;
                    }
                }
            `}</style>
        </section>
    );
};

export default ForgotPassword;