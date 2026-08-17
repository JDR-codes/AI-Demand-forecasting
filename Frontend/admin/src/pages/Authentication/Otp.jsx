import React, { useState, useEffect, useRef } from "react";
import AuthBg from "../../assets/Before-Login/Auth.png";
import { showToast } from "../../components/Toast";
import { ArrowLeft } from "lucide-react";
import { useNavigate, useLocation } from "react-router-dom";
import api from "../../utils/axiosConfig";

const OTP = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const email = location.state?.email || sessionStorage.getItem('reset_email') || "";
    
    const [otp, setOtp] = useState(["", "", "", "", ""]);
    const [isLoading, setIsLoading] = useState(false);
    const [timeLeft, setTimeLeft] = useState(30);
    const [isTimerActive, setIsTimerActive] = useState(true);
    const [canResend, setCanResend] = useState(false);
    const [otpError, setOtpError] = useState(false);
    const [resetToken, setResetToken] = useState(null);
    const [resendAttempts, setResendAttempts] = useState(0);
    const [isResendLoading, setIsResendLoading] = useState(false);

    // State for counting animation
    const [counts, setCounts] = useState({
        accuracy: 0,
        growth: 0,
        inventory: 0
    });
    const intervalRef = useRef(null);
    const timerRef = useRef(null);

    // Redirect if no email is available
    useEffect(() => {
        if (!email) {
            showToast.error("Session expired. Please try again.");
            setTimeout(() => {
                navigate("/forgot-password");
            }, 1500);
        }
    }, [email, navigate]);

    // Check for existing reset token in session storage
    useEffect(() => {
        const savedToken = sessionStorage.getItem('reset_token');
        if (savedToken) {
            setResetToken(savedToken);
        }
    }, []);

    const handleOtpChange = (index, value) => {
        if (value.length > 1) return;
        const newOtp = [...otp];
        newOtp[index] = value;
        setOtp(newOtp);
        
        // Clear error when user starts typing
        setOtpError(false);
        
        // Auto-focus next input
        if (value && index < 4) {
            document.getElementById(`otp-${index + 1}`)?.focus();
        }
    };

    const handleVerifyOtp = async (e) => {
        e.preventDefault();
        const otpValue = otp.join("");
        
        // Check if OTP is complete
        if (otpValue.length < 5) {
            setOtpError(true);
            showToast.warning("Please enter complete OTP!");
            
            // Focus the first empty input
            const firstEmptyIndex = otp.findIndex(digit => digit === "");
            if (firstEmptyIndex !== -1) {
                document.getElementById(`otp-${firstEmptyIndex}`)?.focus();
            }
            return;
        }

        setIsLoading(true);
        const toastId = showToast.loading("Verifying OTP...");

        try {
            console.log("Verifying OTP for email:", email);
            console.log("OTP Code:", otpValue);
            console.log("Before API");

            // Call the backend API to verify OTP
            const response = await api.post("/auth/verify-otp", {
                email: email,
                otp_code: otpValue
            });
            console.log("After API");

            console.log("Verify OTP Response:", response.data);

            if (response.data && response.data.reset_token) {
                // Store the reset token for the password reset step
                setResetToken(response.data.reset_token);
                sessionStorage.setItem('reset_token', response.data.reset_token);
                
                showToast.update(toastId, {
                    render: "✅ OTP verified successfully!",
                    type: "success",
                    isLoading: false,
                    autoClose: 3000,
                });

                // Navigate to reset password page with email and reset token
                setTimeout(() => {
                    navigate("/reset-password", { 
                        state: { 
                            email: email,
                            reset_token: response.data.reset_token 
                        } 
                    });
                }, 2000);
            } else {
                throw new Error("Invalid response from server");
            }

        } catch (error) {
            console.error("Verify OTP Error:", error);
            
            let errorMessage = "❌ Invalid OTP. Please try again.";
            
            if (error.response) {
                console.error("Error response:", error.response.data);
                if (error.response.status === 400) {
                    errorMessage = `❌ ${error.response.data.detail || "Invalid OTP. Please try again."}`;
                } else if (error.response.status === 429) {
                    errorMessage = "⚠️ Too many attempts. Please wait a moment and try again.";
                } else if (error.response.data && error.response.data.detail) {
                    errorMessage = `❌ ${error.response.data.detail}`;
                }
            } else if (error.request) {
                errorMessage = "❌ Server is not responding. Please check your connection.";
            } else {
                errorMessage = `❌ ${error.message}`;
            }
            
            // Set error state to show red borders
            setOtpError(true);
            
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

    const handleBackToForgotPassword = () => {
        navigate("/forgot-password");
    };

    const handleResendOTP = async () => {
        // Check if user can resend
        if (!canResend) {
            showToast.warning("Please wait for the timer to expire before resending.");
            return;
        }

        // Check if max resend attempts reached (3 attempts)
        if (resendAttempts >= 3) {
            showToast.error("Maximum resend attempts reached. Please try again later.");
            return;
        }

        setIsResendLoading(true);
        const toastId = showToast.loading("Resending OTP...");

        try {
            console.log("Resending OTP for email:", email);
            
            // Call the backend API to resend OTP using the dedicated endpoint
            const response = await api.post("/auth/resend-otp", {
                email: email
            });

            console.log("Resend OTP Response:", response.data);

            if (response.data && response.data.message) {
                // Increment resend attempts
                setResendAttempts(prev => prev + 1);
                
                showToast.update(toastId, {
                    render: `✅ ${response.data.message}`,
                    type: "success",
                    isLoading: false,
                    autoClose: 3000,
                });

                // Reset timer
                setTimeLeft(30);
                setIsTimerActive(true);
                setCanResend(false);
                setOtpError(false);
                setOtp(["", "", "", "", ""]); // Clear OTP inputs
                
                // Focus first input
                setTimeout(() => {
                    document.getElementById(`otp-0`)?.focus();
                }, 100);

                // Store in session storage that OTP was resent
                sessionStorage.setItem('reset_email', email);
                
            } else {
                throw new Error("Invalid response from server");
            }

        } catch (error) {
            console.error("Resend OTP Error:", error);
            
            let errorMessage = "❌ Failed to resend OTP. Please try again.";
            
            if (error.response) {
                console.error("Error response:", error.response.data);
                if (error.response.status === 429) {
                    errorMessage = "⚠️ Too many resend requests. Please wait a moment and try again.";
                    // If rate limited, add extra time to timer
                    setTimeLeft(60);
                    setIsTimerActive(true);
                    setCanResend(false);
                } else if (error.response.status === 400) {
                    errorMessage = `❌ ${error.response.data.detail || "Invalid request. Please try again."}`;
                } else if (error.response.data && error.response.data.detail) {
                    errorMessage = `❌ ${error.response.data.detail}`;
                }
            } else if (error.request) {
                errorMessage = "❌ Server is not responding. Please check your connection.";
            } else {
                errorMessage = `❌ ${error.message}`;
            }
            
            showToast.update(toastId, {
                render: errorMessage,
                type: "error",
                isLoading: false,
                autoClose: 4000,
            });
        } finally {
            setIsResendLoading(false);
        }
    };

    // Handle paste functionality for OTP
    const handlePaste = (e) => {
        e.preventDefault();
        const pastedData = e.clipboardData.getData('text');
        const digits = pastedData.replace(/\D/g, '').slice(0, 5);
        
        if (digits.length === 5) {
            const newOtp = digits.split('');
            setOtp(newOtp);
            setOtpError(false);
            
            // Focus the last input
            document.getElementById(`otp-4`)?.focus();
        } else {
            showToast.warning("Please paste a valid 5-digit OTP");
        }
    };

    // Timer effect
    useEffect(() => {
        if (isTimerActive && timeLeft > 0) {
            timerRef.current = setInterval(() => {
                setTimeLeft((prev) => {
                    if (prev <= 1) {
                        clearInterval(timerRef.current);
                        setIsTimerActive(false);
                        setCanResend(true);
                        return 0;
                    }
                    return prev - 1;
                });
            }, 1000);
        }

        return () => {
            if (timerRef.current) {
                clearInterval(timerRef.current);
            }
        };
    }, [isTimerActive]);

    // Check if user has reached max resend attempts
    const isMaxAttemptsReached = resendAttempts >= 3;

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

            {/* OTP Form */}
            <div
                className="mr-[24px] rounded-[20px] p-10 backdrop-blur-md flex flex-col relative z-10 otp-form"
                style={{
                    background:
                        "linear-gradient(322.91deg, rgba(255, 106, 0, 0.15) 0.68%, rgba(20, 184, 166, 0.15) 99.32%)",
                    boxShadow: "0px 0px 6px 0px #14B8A6, 0px 0px 2px 0px #FF6A00",
                    width: "481px",
                }}
            >
                {/* Back Button */}
                <button
                    onClick={handleBackToForgotPassword}
                    className="flex items-center gap-2 text-white/60 hover:text-white transition mb-2 cursor-pointer"
                    disabled={isLoading || isResendLoading}
                >
                    <ArrowLeft size={20} />
                    <span className="text-sm">Back to Forgot Password</span>
                </button>

                {/* Top */}
                <div className="form-header">
                    <p className="mt-2 text-[14px] font-normal leading-[21px] tracking-[1px] text-[#FAB51B] welcome-subtitle">
                        We sent a reset link to{" "}
                        <span className="text-white font-medium">{email}</span>
                        <br />
                        Enter 5 digit code that mentioned in the email
                    </p>
                </div>

                {/* Form */}
                <form onSubmit={handleVerifyOtp} className="form-container">
                    {/* OTP Input */}
                    <div className="form-group">
                        <div className="flex gap-3 justify-center" onPaste={handlePaste}>
                            {otp.map((digit, index) => (
                                <input
                                    key={index}
                                    id={`otp-${index}`}
                                    type="text"
                                    maxLength="1"
                                    value={digit}
                                    onChange={(e) => handleOtpChange(index, e.target.value)}
                                    className={`w-14 h-14 text-center text-2xl font-bold rounded-lg border transition otp-input
                                        ${otpError && !digit ? 'border-red-500 bg-red-500/10' : 'border-white/20 bg-white/10'}
                                        ${!otpError && 'border-white/20 bg-white/10'}
                                        text-white outline-none focus:border-[#14B8A6] focus:bg-white/20`}
                                    autoFocus={index === 0}
                                    disabled={isLoading || isResendLoading}
                                    onKeyDown={(e) => {
                                        // Handle backspace to move to previous input
                                        if (e.key === 'Backspace' && !digit && index > 0) {
                                            document.getElementById(`otp-${index - 1}`)?.focus();
                                        }
                                    }}
                                />
                            ))}
                        </div>
                        {/* Error message */}
                        {otpError && (
                            <p className="text-red-500 text-xs mt-2 text-center">
                                Please enter all 5 digits of the OTP
                            </p>
                        )}
                    </div>

                    {/* Resend OTP and Timer - Bottom of OTP box */}
                    <div className="flex items-center justify-between mt-2">
                        <div className="flex items-center gap-3">
                            <button
                                type="button"
                                onClick={handleResendOTP}
                                disabled={!canResend || isLoading || isResendLoading || isMaxAttemptsReached}
                                className={`text-sm transition cursor-pointer ${
                                    canResend && !isLoading && !isResendLoading && !isMaxAttemptsReached
                                        ? "text-[#FF6A00] hover:text-[#FF7A1A] hover:underline"
                                        : "text-white/40 cursor-not-allowed"
                                }`}
                            >
                                {isResendLoading ? (
                                    <span className="flex items-center gap-2">
                                        <svg
                                            className="animate-spin h-4 w-4"
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
                                        Sending...
                                    </span>
                                ) : isMaxAttemptsReached ? (
                                    "Max attempts reached"
                                ) : (
                                    "Resend OTP"
                                )}
                            </button>
                            {isMaxAttemptsReached && (
                                <span className="text-xs text-red-400">
                                    (3/3 attempts used)
                                </span>
                            )}
                        </div>
                        <div className="text-sm text-white/60 flex items-center gap-1">
                            {isTimerActive ? (
                                <span>00:{String(timeLeft).padStart(2, '0')}</span>
                            ) : (
                                <span className="text-green-400">Ready to resend</span>
                            )}
                        </div>
                    </div>

                    {/* Resend attempts remaining info */}
                    {!isMaxAttemptsReached && (
                        <div className="text-xs text-white/40 text-center -mt-1">
                            {3 - resendAttempts} resend{3 - resendAttempts !== 1 ? 's' : ''} remaining
                        </div>
                    )}

                    {/* Verify OTP Button */}
                    <button
                        type="submit"
                        disabled={isLoading || isResendLoading}
                        className="w-full cursor-pointer rounded-lg py-3 font-semibold text-white transition duration-300 hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 otp-button mt-2"
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
                                Verifying...
                            </>
                        ) : (
                            <>
                                Verify OTP
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

                    .otp-form {
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

                    .otp-input {
                        width: 52px !important;
                        height: 52px !important;
                        font-size: 20px !important;
                    }

                    .otp-button {
                        padding-top: 10px !important;
                        padding-bottom: 10px !important;
                        font-size: 14px !important;
                    }

                    .otp-form .flex.items-center.justify-between {
                        font-size: 12px !important;
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

                    .otp-form {
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

                    .otp-input {
                        width: 44px !important;
                        height: 44px !important;
                        font-size: 16px !important;
                    }

                    .otp-button {
                        font-size: 13px !important;
                        padding-top: 8px !important;
                        padding-bottom: 8px !important;
                    }
                }

                /* For mobile devices */
                @media (max-width: 768px) {
                    .metric-card {
                        display: none !important;
                    }

                    .otp-form {
                        width: 300px !important;
                        padding: 16px !important;
                        margin-right: 12px !important;
                    }

                    .welcome-title {
                        font-size: 18px !important;
                        line-height: 24px !important;
                    }

                    .welcome-subtitle {
                        font-size: 10px !important;
                        line-height: 14px !important;
                    }

                    .otp-input {
                        width: 38px !important;
                        height: 38px !important;
                        font-size: 14px !important;
                    }

                    .otp-button {
                        font-size: 12px !important;
                        padding-top: 6px !important;
                        padding-bottom: 6px !important;
                    }

                    .form-container {
                        gap: 12px !important;
                        margin-top: 20px !important;
                    }

                    .otp-form .gap-3 {
                        gap: 6px !important;
                    }

                    .otp-form .flex.items-center.justify-between {
                        font-size: 10px !important;
                        flex-wrap: wrap;
                        gap: 8px;
                    }
                }
            `}</style>
        </section>
    );
};

export default OTP;