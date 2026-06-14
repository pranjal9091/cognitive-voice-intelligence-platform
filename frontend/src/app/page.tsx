"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Search, Activity, User, Calendar, ShieldAlert, FileText, ArrowRight, Loader } from "lucide-react";
import { fetchSessions } from "./services/api";
import { SessionListItem } from "./types";

export default function ClinicianPortal() {
  const router = useRouter();
  const [sessions, setSessions] = useState<SessionListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchId, setSearchId] = useState("");
  const [searchError, setSearchError] = useState<string | null>(null);

  useEffect(() => {
    async function loadSessions() {
      try {
        setLoading(true);
        const data = await fetchSessions();
        setSessions(data.items || []);
        setError(null);
      } catch (err: any) {
        console.error(err);
        setError("Unable to connect to the backend services. Please make sure the API server is active.");
      } finally {
        setLoading(false);
      }
    }
    loadSessions();
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchError(null);

    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    const cleanId = searchId.trim();

    if (!cleanId) {
      setSearchError("Please enter a Session ID.");
      return;
    }

    if (!uuidRegex.test(cleanId)) {
      setSearchError("Please enter a valid UUID format (e.g. 8cd0098f-f90d-4ed0-bc77-cc2338c8c777).");
      return;
    }

    router.push(`/session/${cleanId}`);
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case "scored":
        return "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20";
      case "analyzed":
        return "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20";
      case "transcribed":
        return "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20";
      case "uploaded":
        return "bg-amber-500/10 text-amber-400 border border-amber-500/20";
      default:
        return "bg-slate-500/10 text-slate-400 border border-slate-500/20";
    }
  };

  const getRiskColor = (risk: string) => {
    switch (risk.toUpperCase()) {
      case "HIGH_RISK":
        return "text-rose-400 bg-rose-500/10 border border-rose-500/20 font-semibold";
      case "MEDIUM_RISK":
        return "text-amber-400 bg-amber-500/10 border border-amber-500/20 font-semibold";
      case "LOW_RISK":
        return "text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 font-semibold";
      default:
        return "text-slate-400 bg-slate-500/10 border border-slate-500/20";
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col relative overflow-hidden">
      {/* Background visual graphics */}
      <div className="absolute top-[-300px] left-[-300px] w-[600px] h-[600px] bg-indigo-500/5 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-300px] right-[-300px] w-[600px] h-[600px] bg-cyan-500/5 rounded-full blur-[120px] pointer-events-none" />

      {/* Main Header */}
      <header className="border-b border-slate-900 bg-slate-950/80 backdrop-blur-md sticky top-0 z-50 px-6 py-4">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row justify-between items-center gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-indigo-500 flex items-center justify-center shadow-lg shadow-indigo-500/10">
              <Activity className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white">Cognitive Voice Intelligence</h1>
              <p className="text-xs text-slate-400">Clinician Assessment Portal</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/assess"
              className="px-4 py-2 bg-gradient-to-r from-cyan-500 to-indigo-500 hover:opacity-90 text-white text-xs font-bold rounded-xl shadow-md transition-opacity"
            >
              Start Subject Assessment
            </Link>
            <div className="flex items-center gap-2 text-xs text-slate-400 bg-slate-900/50 px-3 py-1.5 rounded-full border border-slate-800">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span>Service Connected</span>
            </div>
          </div>
        </div>
      </header>

      {/* Hero / Search Section */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-12 flex flex-col gap-10 z-10">
        <section className="text-center max-w-2xl mx-auto flex flex-col gap-6">
          <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white leading-tight">
            Analyze Speech and Acoustic <span className="text-gradient-cyan">Biomarkers</span>
          </h2>
          <p className="text-slate-400 text-sm sm:text-base leading-relaxed">
            Enter a Session ID to open the detailed cognitive risk dashboard, review computed linguistic patterns, and inspect acoustic pauses.
          </p>

          <form onSubmit={handleSearch} className="w-full mt-4 flex flex-col gap-2 relative">
            <div className="relative flex items-center">
              <Search className="absolute left-4 w-5 h-5 text-slate-500" />
              <input
                type="text"
                placeholder="Enter Session UUID (e.g. 2785c0f4-b075-4eb9-9233-80d80ca14485)"
                value={searchId}
                onChange={(e) => setSearchId(e.target.value)}
                className="w-full bg-slate-900/60 border border-slate-800 rounded-2xl py-4 pl-12 pr-4 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500 backdrop-blur-sm transition-all duration-300"
              />
              <button
                type="submit"
                className="absolute right-2 px-4 py-2 bg-gradient-to-r from-cyan-500 to-indigo-500 text-white text-xs font-semibold rounded-xl hover:opacity-90 transition-opacity flex items-center gap-1.5"
              >
                <span>Assess</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
            {searchError && (
              <p className="text-left text-xs text-rose-400 px-3 flex items-center gap-1">
                <ShieldAlert className="w-3.5 h-3.5" />
                <span>{searchError}</span>
              </p>
            )}
          </form>
        </section>

        {/* Sessions Grid */}
        <section className="flex flex-col gap-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold text-white tracking-tight flex items-center gap-2">
              <FileText className="w-4 h-4 text-cyan-400" />
              <span>Assessment Sessions</span>
            </h3>
            <span className="text-xs text-slate-500 font-medium">Showing latest database records</span>
          </div>

          {loading ? (
            <div className="flex flex-col items-center justify-center py-20 gap-3 bg-slate-900/20 rounded-2xl border border-slate-900/80">
              <Loader className="w-8 h-8 text-cyan-400 animate-spin" />
              <p className="text-slate-400 text-sm">Querying active sessions...</p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center text-center py-16 px-6 gap-4 bg-rose-950/10 rounded-2xl border border-rose-950/20">
              <ShieldAlert className="w-10 h-10 text-rose-400" />
              <div>
                <h4 className="text-white font-medium">Server Connection Refused</h4>
                <p className="text-slate-400 text-xs mt-1 max-w-md">{error}</p>
              </div>
            </div>
          ) : sessions.length === 0 ? (
            <div className="flex flex-col items-center text-center py-20 px-6 gap-4 bg-slate-900/20 rounded-2xl border border-slate-900/80">
              <Activity className="w-12 h-12 text-slate-600" />
              <div>
                <h4 className="text-white font-semibold text-base">No Sessions Found</h4>
                <p className="text-slate-400 text-xs mt-1 max-w-sm">
                  There are no speech records in the database yet. Run the backend CLI scripts or upload audio files to initialize sessions.
                </p>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {sessions.map((s) => (
                <Link
                  key={s.session_id}
                  href={`/session/${s.session_id}`}
                  className="group flex flex-col justify-between p-5 bg-slate-900/40 rounded-2xl border border-slate-900 hover:border-slate-800 hover:bg-slate-900/60 transition-all duration-300 relative overflow-hidden"
                >
                  <div className="flex justify-between items-start gap-4">
                    <div className="flex flex-col gap-2">
                      <span className="text-xs text-slate-500 font-medium flex items-center gap-1">
                        <User className="w-3 h-3" />
                        <span>Subject: {s.subject_reference}</span>
                      </span>
                      <h4 className="text-sm font-mono font-bold text-white tracking-tight break-all group-hover:text-cyan-400 transition-colors">
                        {s.session_id}
                      </h4>
                    </div>
                    <span className={`text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded-full ${getStatusColor(s.status)}`}>
                      {s.status}
                    </span>
                  </div>

                  <div className="flex justify-between items-center mt-6 pt-4 border-t border-slate-950">
                    <span className="text-[11px] text-slate-500 flex items-center gap-1">
                      <Calendar className="w-3.5 h-3.5" />
                      <span>
                        {s.created_at ? new Date(s.created_at).toLocaleDateString(undefined, {
                          dateStyle: "medium"
                        }) : "N/A"}
                      </span>
                    </span>
                    <span className={`text-[11px] px-2.5 py-0.5 rounded-full border ${getRiskColor(s.risk_classification)}`}>
                      {s.risk_classification.replace("_", " ")}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 py-6 text-center text-xs text-slate-500">
        <div className="max-w-6xl mx-auto px-6">
          <p>© 2026 Cognitive Voice Platform. Engineering Demonstration Only. Not for Clinical Diagnoses.</p>
        </div>
      </footer>
    </div>
  );
}
