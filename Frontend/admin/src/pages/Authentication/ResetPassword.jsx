import React, { useState, useEffect, useRef } from "react";
import AuthBg from "../../assets/Before-Login/Auth.png";
import { showToast } from "../../components/Toast";
import { ArrowLeft, Eye, EyeOff, Check } from "lucide-react";
import { useNavigate, useLocation } from "react-router-dom";
import api from "../../utils/axiosConfig";

const ResetPassword = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const email = location.state?.email || sessionStorage.getItem('reset_email') || "";
    const resetToken = location.state?.reset_token || sessionStorage.getItem('reset_token') || "";
    
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [showPassword, setShowPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);
    const [rememberMe, setRememberMe] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [passwordError, setPasswordError] = useState(false);
    const [confirmPasswordError, setConfirmPasswordError] = useState(false);
    const [passwordTouched, setPasswordTouched] = useState(false);
    const [confirmPasswordTouched, setConfirmPasswordTouched] = useState(false);
    const [isSuccess, setIsSuccess] = useState(false);

    // State for counting animation
    const [counts, setCounts] = useState({
        accuracy: 0,
        growth: 0,
        inventory: 0
    });
    const intervalRef = useRef(null);

    // Redirect if no email or reset token is available
    useEffect(() => {
        if (!email || !resetToken) {
            showToast.error("Session expired or invalid reset link. Please try again.");
            setTimeout(() => {
                navigate("/forgot-password");
            }, 1500);
        }
    }, [email, resetToken, navigate]);

    // Calculate password strength percentage
    const getPasswordStrength = (pass) => {
        let strength = 0;
        if (pass.length >= 8) strength += 20;
        if (/[A-Z]/.test(pass)) strength += 20;
        if (/[a-z]/.test(pass)) strength += 20;
        if (/[!@#$%^&*(),.?":{}|<>]/.test(pass)) strength += 20;
        if (/[0-9]/.test(pass)) strength += 20;
        return strength;
    };

    // Get color based on strength
    const getStrengthColor = (strength) => {
        if (strength === 0) return 'bg-white/20';
        if (strength <= 20) return 'bg-red-500';
        if (strength <= 40) return 'bg-orange-500';
        if (strength <= 60) return 'bg-yellow-500';
        if (strength <= 80) return 'bg-blue-500';
        return 'bg-green-500';
    };

    const validatePassword = (pass) => {
        return pass.length >= 8 && 
               /[A-Z]/.test(pass) && 
               /[a-z]/.test(pass) && 
               /[!@#$%^&*(),.?":{}|<>]/.test(pass) && 
               /[0-9]/.test(pass);
    };

    const handlePasswordChange = (e) => {
        const value = e.target.value;
        setPassword(value);
        setPasswordTouched(true);
        
        if (value && !validatePassword(value)) {
            setPasswordError(true);
        } else {
            setPasswordError(false);
        }
        
        if (confirmPassword && confirmPassword !== value) {
            setConfirmPasswordError(true);
        } else if (confirmPassword && confirmPassword === value) {
            setConfirmPasswordError(false);
        }
    };

    const handleConfirmPasswordChange = (e) => {
        const value = e.target.value;
        setConfirmPassword(value);
        setConfirmPasswordTouched(true);
        if (value && value !== password) {
            setConfirmPasswordError(true);
        } else {
            setConfirmPasswordError(false);
        }
    };

    const handleResetPassword = async (e) => {
        e.preventDefault();
        
        setPasswordTouched(true);
        setConfirmPasswordTouched(true);
        setPasswordError(false);
        setConfirmPasswordError(false);

        let hasError = false;

        if (!password) {
            setPasswordError(true);
            hasError = true;
        }

        if (!confirmPassword) {
            setConfirmPasswordError(true);
            hasError = true;
        }

        if (hasError) {
            showToast.error("Please fill in all fields");
            return;
        }

        const isStrongPassword = validatePassword(password);
        if (!isStrongPassword) {
            setPasswordError(true);
            showToast.error("Password must be at least 8 characters with uppercase, lowercase, number, and special character!");
            return;
        }

        if (password !== confirmPassword) {
            setConfirmPasswordError(true);
            showToast.error("Passwords do not match!");
            return;
        }

        setIsLoading(true);
        const toastId = showToast.loading("Updating password...");

        try {
            // Call the backend API to reset password
            const response = await api.post("/auth/reset-password", {
                email: email,
                reset_token: resetToken,
                new_password: password,
                confirm_new_password: confirmPassword
            });

            if (response.data && response.data.message) {
                showToast.update(toastId, {
                    render: `✅ ${response.data.message}`,
                    type: "success",
                    isLoading: false,
                    autoClose: 1000,
                });

                // Show success state
                setIsSuccess(true);

                // Clear session storage
                sessionStorage.removeItem('reset_email');
                sessionStorage.removeItem('reset_token');

                // Redirect to login after 3 seconds
                setTimeout(() => {
                    navigate("/login");
                }, 3000);
            } else {
                throw new Error("Invalid response from server");
            }

        } catch (error) {
            let errorMessage = "❌ Failed to update password. Please try again.";
            
            if (error.response) {
                if (error.response.status === 400) {
                    errorMessage = `❌ ${error.response.data.detail || "Invalid request. Please check your password and try again."}`;
                } else if (error.response.status === 401) {
                    errorMessage = "❌ Reset token has expired. Please request a new password reset.";
                    // Redirect to forgot password after showing error
                    setTimeout(() => {
                        navigate("/forgot-password");
                    }, 3000);
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
            setIsLoading(false);
        }
    };

    const handleBackToLogin = () => {
        navigate("/login");
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
            {/* Logo - Hide on success */}
            <div className={`absolute top-8 left-8 z-50 flex items-center gap-3 transition-opacity duration-500 ${isSuccess ? 'opacity-0' : 'opacity-100'}`}>
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

            {/* Metric Boxes - Hide on success */}
            <div className={`absolute left-[80px] top-1/2 -translate-y-1/2 flex flex-col gap-6 metric-container transition-opacity duration-500 ${isSuccess ? 'opacity-0' : 'opacity-100'}`}>
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

            {/* Reset Password Form */}
            <div
                className={`mr-[24px] rounded-[20px] p-10 backdrop-blur-md flex flex-col relative z-10 reset-form transition-all duration-700 ${
                    isSuccess ? 'scale-95' : 'scale-100'
                }`}
                style={{
                    background:
                        "linear-gradient(322.91deg, rgba(255, 106, 0, 0.15) 0.68%, rgba(20, 184, 166, 0.15) 99.32%)",
                    boxShadow: "0px 0px 6px 0px #14B8A6, 0px 0px 2px 0px #FF6A00",
                    width: "481px",
                    minHeight: isSuccess ? "400px" : "auto",
                }}
            >
                {!isSuccess ? (
                    // Normal Form Content
                    <>
                        {/* Back Button */}
                        <button
                            onClick={handleBackToLogin}
                            className="flex items-center gap-2 text-white/60 hover:text-white transition mb-2 cursor-pointer"
                            disabled={isLoading}
                        >
                            <ArrowLeft size={20} />
                            <span className="text-sm">Back to Login</span>
                        </button>

                        {/* Top */}
                        <div className="form-header">
                            <h1 className="text-[26px] font-bold leading-[39px] tracking-[0px] text-white welcome-title">
                                Set a new password
                            </h1>
                            <p className="mt-2 text-[14px] font-normal leading-[21px] tracking-[1px] text-[#FAB51B] welcome-subtitle">
                                Create a new password. Ensure it differs from previous ones for security
                            </p>
                            {email && (
                                <p className="mt-1 text-xs text-white/40">
                                    Resetting password for: <span className="text-white/60">{email}</span>
                                </p>
                            )}
                        </div>

                        {/* Form */}
                        <form onSubmit={handleResetPassword} className="form-container">
                            {/* Password Input */}
                            <div className="form-group">
                                <label className="block text-sm font-medium text-white/80 mb-2 input-label">
                                    New Password
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
                                            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                                            <path d="M7 11V7a5 5 0 0110 0v4" />
                                        </svg>
                                    </div>

                                    <input
                                        type={showPassword ? "text" : "password"}
                                        placeholder="Enter your new password"
                                        value={password}
                                        onChange={handlePasswordChange}
                                        className={`w-full rounded-lg border ${
                                            passwordError && passwordTouched ? "border-red-500" : "border-white/20"
                                        } 
                                            bg-white/10 pl-10 pr-12 py-3 text-white placeholder:text-white/60 
                                            outline-none focus:border-[#14B8A6] transition form-input`}
                                        disabled={isLoading}
                                    />

                                    <button
                                        type="button"
                                        onClick={() => setShowPassword(!showPassword)}
                                        className="absolute inset-y-0 right-0 pr-3 flex items-center text-white/60 hover:text-white transition password-toggle"
                                        disabled={isLoading}
                                    >
                                        {showPassword ? (
                                            <EyeOff size={20} />
                                        ) : (
                                            <Eye size={20} />
                                        )}
                                    </button>
                                </div>

                                {passwordError && passwordTouched && !password && (
                                    <p className="text-red-500 text-xs mt-1 error-text">
                                        Password required
                                    </p>
                                )}

                                {password && (
                                    <div className="mt-2">
                                        <div className="w-full h-1 rounded-full bg-white/10 overflow-hidden">
                                            <div 
                                                className={`h-full rounded-full transition-all duration-500 ${getStrengthColor(getPasswordStrength(password))}`}
                                                style={{ 
                                                    width: `${getPasswordStrength(password)}%`,
                                                    transition: 'width 0.5s ease-in-out'
                                                }}
                                            />
                                        </div>
                                        <div className="flex justify-between mt-1">
                                            <span className="text-[10px] text-white/40">Weak</span>
                                            <span className="text-[10px] text-white/40">Strong</span>
                                        </div>
                                    </div>
                                )}

                                {passwordError && passwordTouched && password && !validatePassword(password) && (
                                    <p className="text-red-500 text-xs mt-1 error-text">
                                        Password must be at least 8 characters with uppercase, lowercase, number, and special character!
                                    </p>
                                )}
                            </div>

                            {/* Confirm Password Input */}
                            <div className="form-group">
                                <label className="block text-sm font-medium text-white/80 mb-2 input-label">
                                    Confirm Password
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
                                            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                                            <path d="M7 11V7a5 5 0 0110 0v4" />
                                        </svg>
                                    </div>

                                    <input
                                        type={showConfirmPassword ? "text" : "password"}
                                        placeholder="Re-enter password"
                                        value={confirmPassword}
                                        onChange={handleConfirmPasswordChange}
                                        className={`w-full rounded-lg border ${
                                            confirmPasswordError && confirmPasswordTouched ? "border-red-500" : 
                                            confirmPassword && confirmPassword === password && password ? "border-green-500" : "border-white/20"
                                        } 
                                            bg-white/10 pl-10 pr-12 py-3 text-white placeholder:text-white/60 
                                            outline-none focus:border-[#14B8A6] transition form-input`}
                                        disabled={isLoading}
                                    />

                                    <button
                                        type="button"
                                        onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                                        className="absolute inset-y-0 right-0 pr-3 flex items-center text-white/60 hover:text-white transition password-toggle"
                                        disabled={isLoading}
                                    >
                                        {showConfirmPassword ? (
                                            <EyeOff size={20} />
                                        ) : (
                                            <Eye size={20} />
                                        )}
                                    </button>
                                </div>

                                {confirmPasswordError && confirmPasswordTouched && !confirmPassword && (
                                    <p className="text-red-500 text-xs mt-1 error-text">
                                        Confirm password required
                                    </p>
                                )}

                                {confirmPasswordError && confirmPasswordTouched && confirmPassword && confirmPassword !== password && (
                                    <p className="text-red-500 text-xs mt-1 error-text">
                                        Passwords do not match
                                    </p>
                                )}

                                {confirmPassword && confirmPassword === password && password && (
                                    <p className="text-green-400 text-xs mt-1">
                                        ✓ Passwords match
                                    </p>
                                )}
                            </div>

                            {/* Remember Me */}
                            <div className="flex items-center gap-2 form-actions">
                                <input
                                    type="checkbox"
                                    id="remember"
                                    checked={rememberMe}
                                    onChange={(e) => setRememberMe(e.target.checked)}
                                    className="h-4 w-4 accent-[#14B8A6] rounded border-white/20 bg-white/10 checked:bg-[#14B8A6] remember-checkbox cursor-pointer"
                                    disabled={isLoading}
                                />
                                <label
                                    htmlFor="remember"
                                    className="text-sm text-white/70 remember-label cursor-pointer"
                                >
                                    Remember me
                                </label>
                            </div>

                            {/* Update Password Button */}
                            <button
                                type="submit"
                                disabled={isLoading}
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
                                        Updating...
                                    </>
                                ) : (
                                    <>
                                        Update Password
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
                    </>
                ) : (
                    // Success Content - Orange Tick Mark with Message
                    <div className="flex flex-col items-center justify-center h-full py-8 animate-fadeIn">
                        <div className="w-24 h-24 rounded-full bg-[#FF6A00]/20 border-4 border-[#FF6A00] flex items-center justify-center animate-bounceIn">
                            <Check className="w-12 h-12 text-[#FF6A00]" strokeWidth={3} />
                        </div>
                        <h2 className="text-2xl font-bold text-white mt-6 text-center">
                            Password Changed Successfully!
                        </h2>
                        <p className="text-sm text-white/70 mt-3 text-center max-w-[350px] leading-relaxed">
                            You can now login again with your new password
                        </p>
                        <div className="mt-6 flex items-center gap-2 text-white/40 text-xs">
                            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                            </svg>
                            Redirecting to login...
                        </div>
                    </div>
                )}
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

                /* Form actions spacing */
                .form-actions {
                    margin: 4px 0 0 0;
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

                /* Success Animations */
                @keyframes fadeIn {
                    from {
                        opacity: 0;
                        transform: translateY(20px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }

                @keyframes bounceIn {
                    0% {
                        transform: scale(0);
                        opacity: 0;
                    }
                    50% {
                        transform: scale(1.2);
                    }
                    70% {
                        transform: scale(0.9);
                    }
                    100% {
                        transform: scale(1);
                        opacity: 1;
                    }
                }

                .animate-fadeIn {
                    animation: fadeIn 0.6s ease-out forwards;
                }

                .animate-bounceIn {
                    animation: bounceIn 0.8s ease-out forwards;
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

                    .reset-form {
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

                    .form-actions {
                        margin: 2px 0 0 0 !important;
                    }

                    .remember-label {
                        font-size: 12px !important;
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

                    .password-toggle {
                        padding-right: 10px !important;
                    }

                    .password-toggle svg {
                        width: 16px !important;
                        height: 16px !important;
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

                    .reset-form {
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

                /* For mobile devices */
                @media (max-width: 768px) {
                    .metric-card {
                        display: none !important;
                    }

                    .reset-form {
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

                    .form-input {
                        font-size: 11px !important;
                        padding-top: 6px !important;
                        padding-bottom: 6px !important;
                    }

                    .reset-button {
                        font-size: 12px !important;
                        padding-top: 6px !important;
                        padding-bottom: 6px !important;
                    }

                    .terms-text {
                        font-size: 9px !important;
                    }

                    .w-24 {
                        width: 64px !important;
                        height: 64px !important;
                    }

                    .w-12 {
                        width: 32px !important;
                        height: 32px !important;
                    }
                }
            `}</style>
        </section>
    );
};

export default ResetPassword;