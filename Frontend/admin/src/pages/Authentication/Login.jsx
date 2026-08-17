// src/pages/Login/Login.jsx
import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import AuthBg from "../../assets/Before-Login/Auth.png";
import { showToast } from "../../components/Toast";
import api, { loginUser } from "../../utils/axiosConfig";

const Login = () => {
    const navigate = useNavigate();
    const [showPassword, setShowPassword] = useState(false);
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [rememberMe, setRememberMe] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    
    // Validation states for red borders
    const [emailError, setEmailError] = useState(false);
    const [passwordError, setPasswordError] = useState(false);
    const [emailTouched, setEmailTouched] = useState(false);
    const [passwordTouched, setPasswordTouched] = useState(false);

    // State for counting animation
    const [counts, setCounts] = useState({
        accuracy: 0,
        growth: 0,
        inventory: 0
    });
    const [isCounting, setIsCounting] = useState(false);
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

    const handlePasswordChange = (e) => {
        const value = e.target.value;
        setPassword(value);
        setPasswordTouched(true);
        if (value && value.length < 6) {
            setPasswordError(true);
        } else {
            setPasswordError(false);
        }
    };

    const handleLogin = async (e) => {
        e.preventDefault();
        
        setEmailTouched(true);
        setPasswordTouched(true);
        setEmailError(false);
        setPasswordError(false);

        let hasError = false;

        if (!email) {
            setEmailError(true);
            hasError = true;
        }

        if (!password) {
            setPasswordError(true);
            hasError = true;
        }

        if (hasError) {
            showToast.error("Please fill in all fields");
            return;
        }

        if (!validateEmail(email)) {
            setEmailError(true);
            showToast.error("Please enter a valid email address with proper domain (e.g., .com, .in, .org)!");
            return;
        }

        if (password.length < 6) {
            setPasswordError(true);
            showToast.error("Password must be at least 6 characters long!");
            return;
        }

        setIsLoading(true);
        const toastId = showToast.loading("Logging in...");

        try {
            // Use the loginUser helper from axiosConfig
            const response = await loginUser(email, password);

            if (response && response.user) {
                // If remember me is checked, store email for convenience
                if (rememberMe) {
                    localStorage.setItem('admin_email', email);
                } else {
                    localStorage.removeItem('admin_email');
                }

                setEmailError(false);
                setPasswordError(false);
                
                showToast.update(toastId, {
                    render: `✅ Welcome back, ${response.user.name || 'Admin'}!`,
                    type: "success",
                    isLoading: false,
                    autoClose: 3000,
                });

                // Navigate to dashboard after successful login
                setTimeout(() => {
                    navigate('/admin/dashboard');
                }, 500);
            } else {
                throw new Error("Invalid response from server");
            }

        } catch (error) {
            // Handle different error scenarios
            let errorMessage = "❌ Invalid email or password! Please try again.";
            
            if (error.response) {
                // The request was made and the server responded with a status code
                // that falls out of the range of 2xx
                if (error.response.status === 401) {
                    errorMessage = "❌ Invalid email or password! Please try again.";
                } else if (error.response.status === 429) {
                    errorMessage = "⚠️ Too many login attempts. Please try again later.";
                } else if (error.response.status === 405) {
                    errorMessage = "⚠️ Server configuration error. Please contact support.";
                } else if (error.response.data && error.response.data.detail) {
                    errorMessage = `❌ ${error.response.data.detail}`;
                }
            } else if (error.request) {
                // The request was made but no response was received
                errorMessage = "❌ Server is not responding. Please check your connection.";
            } else {
                // Something happened in setting up the request that triggered an Error
                errorMessage = `❌ ${error.message}`;
            }
            
            setEmailError(true);
            setPasswordError(true);
            
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

    // Check for saved email on component mount
    useEffect(() => {
        const savedEmail = localStorage.getItem('admin_email');
        if (savedEmail) {
            setEmail(savedEmail);
            setRememberMe(true);
        }
    }, []);

    const handleForgotPassword = () => {
        navigate('/forgot-password');
    };

    // Counting animation effect
    useEffect(() => {
        const targetValues = {
            accuracy: 95,
            growth: 20.3,
            inventory: 21.3
        };

        const startDelay = setTimeout(() => {
            setIsCounting(true);
            
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
                    setIsCounting(false);
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

    // Metric data with SVG icons - updated layout
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

        {/* Login Form */}
        <div
          className="mr-[24px] rounded-[20px] p-10 backdrop-blur-md flex flex-col relative z-10 login-form"
          style={{
            background:
              "linear-gradient(322.91deg, rgba(255, 106, 0, 0.15) 0.68%, rgba(20, 184, 166, 0.15) 99.32%)",
            boxShadow: "0px 0px 6px 0px #14B8A6, 0px 0px 2px 0px #FF6A00",
            width: "481px",
            height: "560px",
          }}
        >
          {/* Top */}
          <div className="form-header">
            <h1 className="text-[26px] font-bold leading-[39px] tracking-[0px] text-white welcome-title">
              Welcome Back
            </h1>
            <p className="mt-2 text-[14px] font-normal leading-[21px] tracking-[1px] text-[#FAB51B] welcome-subtitle">
              Enter your credentials to access the platform
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleLogin} className="form-container">
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

            {/* Password Input */}
            <div className="form-group">
              <label className="block text-sm font-medium text-white/80 mb-2 input-label">
                Password
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
                  placeholder="password123"
                  value={password}
                  onChange={handlePasswordChange}
                  onBlur={() => {
                    setPasswordTouched(true);
                    if (password && password.length < 6) {
                      setPasswordError(true);
                    }
                  }}
                  className={`w-full rounded-lg border ${passwordError && passwordTouched ? "border-red-500" : "border-white/20"} 
                                    bg-white/10 pl-10 pr-12 py-3 text-white placeholder:text-white/60 
                                    outline-none focus:border-[#14B8A6] transition form-input`}
                />

                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-white/60 hover:text-white transition password-toggle"
                >
                  {showPassword ? (
                    <svg
                      width="20"
                      height="20"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.8"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                      <line x1="1" y1="1" x2="23" y2="23" />
                    </svg>
                  ) : (
                    <svg
                      width="20"
                      height="20"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.8"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  )}
                </button>
              </div>
              {passwordError && passwordTouched && !password && (
                <p className="text-red-500 text-xs mt-1 error-text">
                  Password required
                </p>
              )}
              {passwordError && passwordTouched && password && password.length < 6 && (
                <p className="text-red-500 text-xs mt-1 error-text">
                  Password must be at least 6 characters
                </p>
              )}
            </div>

            {/* Remember Me & Forgot Password */}
            <div className="flex items-center justify-between form-actions">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="remember"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="h-4 w-4 accent-[#14B8A6] rounded border-white/20 bg-white/10 checked:bg-[#14B8A6] remember-checkbox cursor-pointer"
                />
                <label
                  htmlFor="remember"
                  className="text-sm text-white/70 remember-label cursor-pointer"
                >
                  Remember me
                </label>
              </div>
              <button
                type="button"
                onClick={handleForgotPassword}
                className="text-sm text-[#FAB51B] hover:text-[#FF6A00] transition forgot-link cursor-pointer"
              >
                Forgot Password?
              </button>
            </div>

            {/* Login Button */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full cursor-pointer rounded-lg py-3 font-semibold text-white transition duration-300 hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 login-button"
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
                  Logging in...
                </>
              ) : (
                <>
                  Enter Platform
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
              By signing in, you agree to our{" "}
              <span className="text-[#FF6A00] hover:underline cursor-pointer">
                Terms of Service
              </span>{" "}
              and{" "}
              <span className="text-[#FF6A00] hover:underline cursor-pointer">
                Privacy Policy
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
            margin-top: 60px;
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

          /* Responsive styles for < 1280px */
          @media (max-width: 1280px) {
            /* Reduce metric box size */
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

            /* Move 1st metric more up on smaller screens */
            .metric-item:first-child {
              transform: translateX(290px) translateY(-100px) !important;
            }

            /* Move 3rd metric more down on smaller screens */
            .metric-item:last-child {
              transform: translateX(460px) translateY(140px) !important;
            }

            .metric-container {
              gap: 4px !important;
            }

            /* Reduce login form size */
            .login-form {
              width: 400px !important;
              height: 500px !important;
              padding: 24px !important;
            }

            /* Reduce form spacing */
            .form-container {
              gap: 16px !important;
              margin-top: 48px !important;
            }

            /* Move terms text further down */
            .terms-text {
              margin-top: 12px !important;
              padding-top: 8px !important;
              border-top: 1px solid rgba(255, 255, 255, 0.08) !important;
            }

            /* Reduce text sizes */
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

            .forgot-link {
              font-size: 12px !important;
            }

            .remember-checkbox {
              width: 14px !important;
              height: 14px !important;
            }

            .login-button {
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

            /* Move 1st metric even more up on tablets */
            .metric-item:first-child {
              transform: translateX(230px) translateY(-70px) !important;
            }

            /* Move 3rd metric even more down on tablets */
            .metric-item:last-child {
              transform: translateX(280px) translateY(90px) !important;
            }

            .login-form {
              width: 340px !important;
              height: 460px !important;
              padding: 20px !important;
            }

            .form-container {
              gap: 14px !important;
              margin-top: 40px !important;
            }

            .terms-text {
              margin-top: 16px !important;
              padding-top: 10px !important;
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

            .login-button {
              font-size: 13px !important;
              padding-top: 8px !important;
              padding-bottom: 8px !important;
            }

            .terms-text {
              font-size: 10px !important;
            }
          }
        `}</style>
      </section>
    );
  };

export default Login;