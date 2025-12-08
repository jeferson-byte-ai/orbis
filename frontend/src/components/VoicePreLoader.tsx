/**
 * VoicePreLoader Component
 * Beautiful loading screen while preparing cloned voice for meeting
 */
import React, { useState, useEffect } from 'react';
import { Loader, Check, Wand2, Download, Cpu, Sparkles } from 'lucide-react';
import { authenticatedFetch } from '../utils/api';

interface VoicePreLoaderProps {
    onComplete: () => void;
    onError: (error: string) => void;
}

interface LoadingStep {
    id: string;
    label: string;
    icon: any;
    progress: number;
}

const VoicePreLoader: React.FC<VoicePreLoaderProps> = ({ onComplete, onError }) => {
    const [currentStep, setCurrentStep] = useState(0);
    const [overallProgress, setOverallProgress] = useState(0);
    const [error, setError] = useState<string>('');

    const steps: LoadingStep[] = [
        {
            id: 'download',
            label: 'Downloading your voice profile',
            icon: Download,
            progress: 0
        },
        {
            id: 'processing',
            label: 'Processing AI voice model',
            icon: Cpu,
            progress: 0
        },
        {
            id: 'ready',
            label: 'Voice ready for translation',
            icon: Check,
            progress: 0
        }
    ];

    useEffect(() => {
        preloadVoice();
    }, []);

    const preloadVoice = async () => {
        try {
            // Step 1: Download voice profile
            setCurrentStep(0);
            await simulateProgress(0, 30, 1000);

            // Call backend to preload voice using centralized fetch helper
            const response = await authenticatedFetch('/api/voices/preload', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: 'Failed to load voice' }));
                throw new Error(errorData.detail || `Failed to preload voice (status ${response.status})`);
            }

            // Step 2: Processing
            setCurrentStep(1);
            await simulateProgress(30, 70, 1500);

            const data = await response.json();
            console.log('✅ Voice preloaded:', data);

            // Step 3: Ready
            setCurrentStep(2);
            await simulateProgress(70, 100, 800);

            // Complete
            setTimeout(() => {
                onComplete();
            }, 500);

        } catch (err: any) {
            console.error('❌ Voice preload error:', err);
            setError(err.message || 'Failed to prepare voice');
            onError(err.message || 'Failed to prepare voice');
        }
    };

    const simulateProgress = (from: number, to: number, duration: number): Promise<void> => {
        return new Promise((resolve) => {
            const steps = 20;
            const increment = (to - from) / steps;
            const interval = duration / steps;
            let current = from;

            const timer = setInterval(() => {
                current += increment;
                setOverallProgress(Math.min(current, to));

                if (current >= to) {
                    clearInterval(timer);
                    resolve();
                }
            }, interval);
        });
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-950 via-blue-950 to-slate-950 flex items-center justify-center px-6 relative overflow-hidden">
            {/* Animated background */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className="absolute top-20 left-20 w-96 h-96 bg-blue-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-float" />
                <div className="absolute bottom-20 right-20 w-96 h-96 bg-purple-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-float" style={{ animationDelay: '2s' }} />
            </div>

            <div className="max-w-2xl w-full glass-dark rounded-3xl p-10 shadow-2xl border border-white/20 relative z-10 animate-scale-in">
                {/* Icon */}
                <div className="relative inline-block mb-8 mx-auto block text-center">
                    <div className="bg-gradient-to-br from-blue-600 to-purple-600 rounded-3xl w-24 h-24 flex items-center justify-center shadow-2xl animate-float mx-auto">
                        <Wand2 size={48} className="text-white" />
                    </div>
                    <div className="absolute inset-0 bg-gradient-to-br from-blue-600 to-purple-600 rounded-3xl blur-2xl opacity-50" />
                </div>

                {/* Title */}
                <h2 className="text-4xl font-black text-white mb-3 text-center">
                    Setting Up Your Voice
                </h2>
                <div className="flex items-center justify-center gap-2 mb-8">
                    <Sparkles size={18} className="text-yellow-400" />
                    <p className="text-blue-400 font-semibold">AI Voice Cloning</p>
                    <Sparkles size={18} className="text-yellow-400" />
                </div>

                <p className="text-gray-300 text-lg mb-10 leading-relaxed text-center">
                    Please wait a moment while we prepare your cloned voice for real-time translation
                </p>

                {/* Progress Steps */}
                <div className="space-y-4 mb-8">
                    {steps.map((step, index) => {
                        const Icon = step.icon;
                        const isActive = index === currentStep;
                        const isComplete = index < currentStep;

                        return (
                            <div
                                key={step.id}
                                className={`flex items-center gap-4 p-4 rounded-xl transition-all ${isActive
                                        ? 'bg-blue-500/20 border border-blue-500/50'
                                        : isComplete
                                            ? 'bg-green-500/20 border border-green-500/50'
                                            : 'bg-white/5 border border-white/10'
                                    }`}
                            >
                                <div
                                    className={`p-3 rounded-xl ${isActive
                                            ? 'bg-blue-500 animate-pulse'
                                            : isComplete
                                                ? 'bg-green-500'
                                                : 'bg-gray-700'
                                        }`}
                                >
                                    {isActive ? (
                                        <Loader size={24} className="text-white animate-spin" />
                                    ) : isComplete ? (
                                        <Check size={24} className="text-white" />
                                    ) : (
                                        <Icon size={24} className="text-gray-400" />
                                    )}
                                </div>
                                <div className="flex-1">
                                    <p
                                        className={`font-semibold ${isActive || isComplete ? 'text-white' : 'text-gray-400'
                                            }`}
                                    >
                                        {step.label}
                                    </p>
                                </div>
                            </div>
                        );
                    })}
                </div>

                {/* Overall Progress Bar */}
                <div className="glass rounded-full h-4 mb-4 overflow-hidden">
                    <div
                        className="bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 h-4 rounded-full transition-all duration-300 shadow-lg relative"
                        style={{ width: `${overallProgress}%` }}
                    >
                        <div className="absolute inset-0 bg-white/30 shimmer" />
                    </div>
                </div>

                <p className="text-white text-2xl font-bold text-center">
                    {Math.round(overallProgress)}%
                </p>

                {/* Error Message */}
                {error && (
                    <div className="mt-6 p-4 bg-red-500/20 border border-red-500/50 rounded-xl text-red-300 text-center">
                        {error}
                    </div>
                )}

                {/* Info */}
                <div className="mt-8 p-4 glass rounded-xl">
                    <p className="text-gray-400 text-sm text-center">
                        💡 <span className="text-white font-semibold">Tip:</span> This happens only once per session.
                        Your voice will be ready for all translations!
                    </p>
                </div>
            </div>

            <style>{`
        @keyframes float {
          0%, 100% { transform: translateY(0) rotate(0deg); }
          50% { transform: translateY(-20px) rotate(5deg); }
        }
        
        @keyframes scale-in {
          from {
            opacity: 0;
            transform: scale(0.9);
          }
          to {
            opacity: 1;
            transform: scale(1);
          }
        }

        @keyframes shimmer {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }

        .animate-float {
          animation: float 6s ease-in-out infinite;
        }

        .animate-scale-in {
          animation: scale-in 0.3s ease-out;
        }

        .shimmer {
          animation: shimmer 2s infinite;
        }

        .glass-dark {
          background: rgba(0, 0, 0, 0.4);
          backdrop-filter: blur(10px);
          -webkit-backdrop-filter: blur(10px);
        }

        .glass {
          background: rgba(255, 255, 255, 0.05);
          backdrop-filter: blur(10px);
          -webkit-backdrop-filter: blur(10px);
        }
      `}</style>
        </div>
    );
};

export default VoicePreLoader;
