import React, { useEffect, useMemo, useRef, useState } from 'react';
import { loginStart, resendTwoFactor, verifyTwoFactor } from '../services/authService';
import { saveToken } from '../services/tokenUtils';
import { Lock, User, Eye, EyeOff, Video, Mail, ShieldCheck } from 'lucide-react';

interface LoginScreenProps {
  onLogin: () => void;
}

export const LoginScreen: React.FC<LoginScreenProps> = ({ onLogin }) => {
  const OTP_LENGTH = 6;
  const [showPassword, setShowPassword] = useState(false);
  const [username, setUsername] = useState('');
  const [correo, setCorreo] = useState('');
  const [password, setPassword] = useState('');
  const [step, setStep] = useState<'credentials' | 'otp'>('credentials');
  const [tempToken, setTempToken] = useState('');
  const [maskedEmail, setMaskedEmail] = useState('');
  const [otpDigits, setOtpDigits] = useState<string[]>(Array(OTP_LENGTH).fill(''));
  const [secondsLeft, setSecondsLeft] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const otpInputRefs = useRef<Array<HTMLInputElement | null>>([]);

  const otpCode = useMemo(() => otpDigits.join(''), [otpDigits]);

  useEffect(() => {
    if (step !== 'otp' || secondsLeft <= 0) {
      return;
    }
    const timer = setInterval(() => {
      setSecondsLeft(prev => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, [step, secondsLeft]);

  useEffect(() => {
    if (step === 'otp') {
      otpInputRefs.current[0]?.focus();
    }
  }, [step]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      if (step === 'credentials') {
        const challenge = await loginStart(username, correo, password);
        setTempToken(challenge.temp_token);
        setMaskedEmail(challenge.masked_email || correo);
        setOtpDigits(Array(OTP_LENGTH).fill(''));
        setSecondsLeft(challenge.expires_in ?? 300);
        setStep('otp');
      } else {
        if (otpCode.length !== OTP_LENGTH) {
          throw new Error('Ingresa los 6 dígitos del código');
        }
        const data = await verifyTwoFactor(tempToken, otpCode);
        saveToken(data.access_token);
        onLogin();
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleOtpChange = (index: number, value: string) => {
    const digit = value.replace(/\D/g, '').slice(-1);
    const newDigits = [...otpDigits];
    newDigits[index] = digit;
    setOtpDigits(newDigits);
    if (digit && index < OTP_LENGTH - 1) {
      otpInputRefs.current[index + 1]?.focus();
    }
  };

  const handleOtpKeyDown = (index: number, event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Backspace' && !otpDigits[index] && index > 0) {
      otpInputRefs.current[index - 1]?.focus();
    }
  };

  const handleOtpPaste = (event: React.ClipboardEvent<HTMLInputElement>) => {
    event.preventDefault();
    const pasted = event.clipboardData.getData('text').replace(/\D/g, '').slice(0, OTP_LENGTH);
    if (!pasted) return;
    const filled = Array(OTP_LENGTH).fill('');
    pasted.split('').forEach((char, index) => {
      filled[index] = char;
    });
    setOtpDigits(filled);
    const focusIndex = Math.min(pasted.length, OTP_LENGTH - 1);
    otpInputRefs.current[focusIndex]?.focus();
  };

  const handleResendCode = async () => {
    if (!tempToken || secondsLeft > 0) return;
    setLoading(true);
    setError(null);
    try {
      const response = await resendTwoFactor(tempToken);
      setMaskedEmail(response.masked_email || maskedEmail);
      setOtpDigits(Array(OTP_LENGTH).fill(''));
      setSecondsLeft(response.expires_in ?? 300);
      otpInputRefs.current[0]?.focus();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen flex flex-col items-center justify-center p-4 overflow-hidden bg-background-light dark:bg-[#101922]">
      {/* Background Decoration */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-primary/20 blur-[120px] rounded-full mix-blend-screen opacity-40 animate-pulse"></div>
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-primary/10 blur-[100px] rounded-full mix-blend-screen opacity-30"></div>
        <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-5 brightness-100 contrast-150"></div>
      </div>

      <div className="relative z-10 w-full max-w-md transform rounded-xl border border-slate-200 bg-white p-8 shadow-2xl transition-all dark:border-slate-800 dark:bg-[#182430]">
        <div className="mb-8 text-center">
          <div className="mb-4 flex justify-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/20 text-primary">
              <Video size={28} />
            </div>
          </div>
          <h1 className="mb-2 text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            VERIFICADOR DE PRECIOS LUZ
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            BIENVENIDOS, POR FAVOR INGRESA TUS CREDENCIALES 
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          {step === 'credentials' ? (
            <>
              <div className="space-y-1.5">
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300" htmlFor="username">
                  NOMBRE DE USUARIO
                </label>
                <div className="relative">
                  <input
                    id="username"
                    type="text"
                    required
                    className="block w-full rounded-lg border-slate-300 bg-slate-50 p-2.5 text-slate-900 placeholder:text-slate-400 focus:border-primary focus:ring-primary dark:border-slate-700 dark:bg-[#111a22] dark:text-white dark:placeholder:text-slate-500 sm:text-sm sm:leading-6 h-12 pl-10"
                    placeholder="INGRESA TU USUARIO"
                    value={username}
                    onChange={e => setUsername(e.target.value)}
                  />
                  <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                    <User size={18} className="text-slate-400" />
                  </div>
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300" htmlFor="correo">
                  CORREO
                </label>
                <div className="relative">
                  <input
                    id="correo"
                    type="email"
                    required
                    className="block w-full rounded-lg border-slate-300 bg-slate-50 p-2.5 text-slate-900 placeholder:text-slate-400 focus:border-primary focus:ring-primary dark:border-slate-700 dark:bg-[#111a22] dark:text-white dark:placeholder:text-slate-500 sm:text-sm sm:leading-6 h-12 pl-10"
                    placeholder="INGRESA TU CORREO"
                    value={correo}
                    onChange={e => setCorreo(e.target.value)}
                  />
                  <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                    <Mail size={18} className="text-slate-400" />
                  </div>
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300" htmlFor="password">
                  CONTRASEÑA
                </label>
                <div className="relative">
                  <input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    required
                    className="block w-full rounded-lg border-slate-300 bg-slate-50 p-2.5 text-slate-900 placeholder:text-slate-400 focus:border-primary focus:ring-primary dark:border-slate-700 dark:bg-[#111a22] dark:text-white dark:placeholder:text-slate-500 sm:text-sm sm:leading-6 h-12 pr-10"
                    placeholder="••••••••"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                  />
                  <button
                    type="button"
                    className="absolute inset-y-0 right-0 flex items-center pr-3 text-slate-400 hover:text-slate-500 dark:hover:text-slate-300 focus:outline-none"
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </div>

              <div>
                <button
                  type="submit"
                  className="group relative flex w-full justify-center rounded-lg bg-primary px-3 py-3 text-sm font-semibold text-white shadow-sm hover:bg-blue-600 hover:scale-[1.01] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary transition-all duration-200"
                  disabled={loading}
                >
                  <span className="absolute inset-y-0 left-0 flex items-center pl-3">
                    <Lock className="h-5 w-5 text-blue-200 group-hover:text-blue-100" />
                  </span>
                  {loading ? 'Validando...' : 'Continuar'}
                </button>
              </div>
            </>
          ) : (
            <>
              <div className="text-center">
                <div className="mb-3 flex justify-center">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/15 text-primary">
                    <ShieldCheck size={24} />
                  </div>
                </div>
                <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Verificación en dos pasos</h2>
                <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
                  Ingresa el código de 6 dígitos enviado a <span className="font-medium">{maskedEmail}</span>
                </p>
              </div>

              <div className="flex items-center justify-between gap-2">
                {otpDigits.map((digit, index) => (
                  <input
                    key={index}
                    ref={ref => {
                      otpInputRefs.current[index] = ref;
                    }}
                    type="text"
                    inputMode="numeric"
                    maxLength={1}
                    value={digit}
                    onChange={e => handleOtpChange(index, e.target.value)}
                    onKeyDown={e => handleOtpKeyDown(index, e)}
                    onPaste={handleOtpPaste}
                    className="h-12 w-12 rounded-lg border border-slate-300 bg-slate-50 text-center text-lg font-semibold text-slate-900 focus:border-primary focus:ring-primary dark:border-slate-700 dark:bg-[#111a22] dark:text-white"
                  />
                ))}
              </div>

              <div>
                <button
                  type="submit"
                  className="group relative flex w-full justify-center rounded-lg bg-primary px-3 py-3 text-sm font-semibold text-white shadow-sm hover:bg-blue-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary transition-all duration-200"
                  disabled={loading}
                >
                  <span className="absolute inset-y-0 left-0 flex items-center pl-3">
                    <Lock className="h-5 w-5 text-blue-200 group-hover:text-blue-100" />
                  </span>
                  {loading ? 'Verificando...' : 'Verificar código'}
                </button>
              </div>

              <div className="flex items-center justify-between text-sm">
                <button
                  type="button"
                  className="text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
                  onClick={() => {
                    setStep('credentials');
                    setOtpDigits(Array(OTP_LENGTH).fill(''));
                    setError(null);
                  }}
                  disabled={loading}
                >
                  Volver
                </button>
                <button
                  type="button"
                  className="text-primary disabled:text-slate-400"
                  onClick={handleResendCode}
                  disabled={loading || secondsLeft > 0}
                >
                  {secondsLeft > 0 ? `Reenviar en ${secondsLeft}s` : 'Reenviar código'}
                </button>
              </div>
            </>
          )}

          {error && <div className="text-red-500 text-sm mt-2 text-center">{error}</div>}
        </form>

        {/*<div className="mt-6 border-t border-slate-200 pt-6 text-center dark:border-slate-700">
          <p className="text-xs text-slate-500 dark:text-slate-400">
            No Posee una Cuenta?{' '}
            <a href="#" className="font-medium text-primary hover:text-blue-500 hover:underline">
              Contacta a un Administrador
            </a>
          </p>
        </div>*/}
      </div>

      <p className="mt-8 text-center text-xs text-slate-400 dark:text-slate-600">
        © 2026 Verificador de Precios Luz. Todos los derechos reservados.
      </p>
    </div>
  );
};