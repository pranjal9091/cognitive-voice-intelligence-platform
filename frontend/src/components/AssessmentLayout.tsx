import React from "react";
import { Activity } from "lucide-react";

interface AssessmentLayoutProps {
  currentStep: number;
  totalSteps: number;
  children: React.ReactNode;
}

export default function AssessmentLayout({
  currentStep,
  totalSteps,
  children,
}: AssessmentLayoutProps) {
  const steps = [
    { label: "Question 1" },
    { label: "Question 2" },
    { label: "Question 3" },
    { label: "Review & Submit" },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col relative overflow-hidden">
      {/* Background graphics */}
      <div className="absolute top-[-300px] left-[-300px] w-[600px] h-[600px] bg-indigo-500/5 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-300px] right-[-300px] w-[600px] h-[600px] bg-cyan-500/5 rounded-full blur-[120px] pointer-events-none" />

      {/* Header */}
      <header className="border-b border-slate-900 bg-slate-950/80 backdrop-blur-md sticky top-0 z-50 px-6 py-4">
        <div className="max-w-3xl mx-auto flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-500 to-indigo-500 flex items-center justify-center">
              <Activity className="w-4 h-4 text-white" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-white tracking-tight">Subject Voice Assessment</h1>
              <p className="text-[10px] text-slate-500">Cognitive Screening Platform</p>
            </div>
          </div>
          <a
            href="/"
            className="text-[11px] font-semibold text-slate-400 hover:text-rose-400 transition-colors px-3 py-1.5 bg-slate-900/50 rounded-xl border border-slate-800"
          >
            Exit Assessment
          </a>
        </div>
      </header>

      {/* Stepper indicator bar */}
      <div className="w-full bg-slate-950 border-b border-slate-900/40 py-4 px-6 z-10">
        <div className="max-w-md mx-auto flex justify-between items-center relative">
          {/* Progress bar line */}
          <div className="absolute left-0 right-0 top-1/2 h-[1px] bg-slate-900 -translate-y-1/2 z-0" />
          <div
            className="absolute left-0 top-1/2 h-[1px] bg-gradient-to-r from-cyan-500 to-indigo-500 -translate-y-1/2 z-0 transition-all duration-500"
            style={{ width: `${((currentStep - 1) / (totalSteps - 1)) * 100}%` }}
          />

          {steps.map((step, idx) => {
            const stepNum = idx + 1;
            const isCompleted = stepNum < currentStep;
            const isActive = stepNum === currentStep;

            return (
              <div key={idx} className="flex flex-col items-center gap-1.5 z-10 relative">
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all duration-300 ${
                    isCompleted
                      ? "bg-cyan-500 text-white shadow-lg shadow-cyan-500/20"
                      : isActive
                      ? "bg-indigo-500 text-white ring-4 ring-indigo-500/20 shadow-lg shadow-indigo-500/20"
                      : "bg-slate-900 border border-slate-800 text-slate-500"
                  }`}
                >
                  {stepNum}
                </div>
                <span
                  className={`text-[9px] font-semibold tracking-wider uppercase transition-colors duration-300 ${
                    isActive ? "text-indigo-400" : isCompleted ? "text-cyan-400" : "text-slate-600"
                  }`}
                >
                  {stepNum === 4 ? "Review" : `Q${stepNum}`}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Content wrapper */}
      <main className="flex-1 max-w-xl w-full mx-auto px-6 py-10 z-10 flex flex-col justify-center">
        {children}
      </main>

      {/* Footer */}
      <footer className="py-6 text-center text-[10px] text-slate-600 z-10 border-t border-slate-900/40">
        <p>© 2026 Cognitive Voice Platform. Clinical Assessment Sandbox.</p>
      </footer>
    </div>
  );
}
