"use client";

import { useEffect, useState, useCallback } from "react";
import { DashboardData, fetchDashboard, formatAmount } from "@/lib/api";

export default function Home() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [user, setUser] = useState<{ first_name: string; photo_url?: string } | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const dashboard = await fetchDashboard();
      setData(dashboard);
    } catch (err: any) {
      setError(err.message || "Failed to load data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Initialize Telegram WebApp
    if (typeof window !== "undefined" && window.Telegram?.WebApp) {
      window.Telegram.WebApp.ready();
      window.Telegram.WebApp.expand();
      const u = window.Telegram.WebApp.initDataUnsafe?.user;
      if (u) setUser({ first_name: u.first_name, photo_url: u.photo_url });
    }
    loadData();
  }, [loadData]);

  if (loading && !data) {
    return (
      <main className="min-h-screen bg-[#0f0f1a] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-3 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-gray-400 text-sm">Загрузка данных...</p>
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="min-h-screen bg-[#0f0f1a] flex items-center justify-center p-4">
        <div className="bg-red-950/50 border border-red-800/50 rounded-2xl p-6 text-center max-w-sm w-full">
          <div className="text-3xl mb-3">⚠️</div>
          <p className="text-red-300 text-sm mb-4">{error}</p>
          <button
            onClick={loadData}
            className="px-4 py-2 bg-red-600/30 hover:bg-red-600/50 text-red-200 rounded-lg text-sm transition-colors"
          >
            Повторить
          </button>
        </div>
      </main>
    );
  }

  if (!data) return null;

  const currencies = Object.keys(data.balances).sort();
  const serverTime = new Date(data.server_time);

  return (
    <main className="min-h-screen bg-[#09090b] text-white pb-24 overflow-x-hidden selection:bg-indigo-500/30">
      {/* Premium ambient background blur */}
      <div className="fixed top-[-10%] left-[-10%] w-[60%] h-[40%] rounded-full bg-indigo-600/15 blur-[100px] pointer-events-none" />
      <div className="fixed bottom-[-10%] right-[-10%] w-[60%] h-[40%] rounded-full bg-fuchsia-600/15 blur-[100px] pointer-events-none" />

      {/* Header */}
      <header className="sticky top-0 z-50 glass px-4 py-3 sm:px-5 sm:py-4 flex justify-between items-center rounded-b-[1.5rem] shadow-xl shadow-black/30 mb-5">
        <div className="flex flex-col">
          <h1 className="text-lg sm:text-xl font-extrabold tracking-tight text-gradient-premium">
            Currency MVP
          </h1>
          <div className="flex items-center gap-1.5 mt-0.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <p className="text-[10px] sm:text-[11px] font-medium text-zinc-400 tracking-wide uppercase">
              {user ? user.first_name : "Dashboard"} • {serverTime.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })}
            </p>
          </div>
        </div>
        <button
          onClick={loadData}
          className="w-9 h-9 sm:w-10 sm:h-10 rounded-full bg-white/5 border border-white/10 flex items-center justify-center hover:bg-white/10 active:scale-95 transition-all duration-200"
          title="Обновить"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="text-zinc-300 sm:w-[18px] sm:h-[18px]">
            <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
            <path d="M3 3v5h5"/>
            <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/>
            <path d="M16 16h5v5"/>
          </svg>
        </button>
      </header>

      <div className="px-4 space-y-6 relative z-10 w-full max-w-md mx-auto">
        {/* Balances Cards */}
        <section className="opacity-0 animate-slide-up stagger-1">
          <div className="flex items-center justify-between mb-2.5 px-1">
            <h2 className="text-[13px] font-bold text-zinc-100 tracking-wide">Ваши Балансы</h2>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {currencies.map((cur) => {
              const balance = data.balances[cur] || 0;
              const dailyProfit = data.daily_profits[cur] || 0;
              const isPositive = balance >= 0;
              return (
                <div
                  key={cur}
                  className="glass-card rounded-[1.25rem] p-3.5 relative group transition-transform active:scale-[0.98]"
                >
                  <div className="flex justify-between items-center mb-1.5">
                    <span className="px-2 py-0.5 rounded border border-white/10 bg-white/5 text-[10px] font-bold tracking-wider text-zinc-300">
                      {cur}
                    </span>
                  </div>
                  <div className="mt-1">
                    <p className={`text-lg sm:text-xl font-black tracking-tight ${isPositive ? "text-white" : "text-red-400"}`}>
                      {formatAmount(balance, "")}
                    </p>
                    <div className="h-4 mt-1">
                      {dailyProfit !== 0 && (
                        <span className={`inline-flex items-center px-1.5 py-0.5 rounded-sm text-[9px] font-bold ${
                          dailyProfit > 0 
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" 
                            : "bg-red-500/10 text-red-400 border border-red-500/20"
                        }`}>
                          {dailyProfit > 0 ? "↗" : "↘"} {dailyProfit > 0 ? "+" : ""}{formatAmount(dailyProfit, "")}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* Client Debts */}
        {data.debts.length > 0 && (
          <section className="opacity-0 animate-slide-up stagger-2">
            <div className="flex items-center justify-between mb-2.5 px-1">
              <h2 className="text-[13px] font-bold text-zinc-100 tracking-wide">Долги Клиентов</h2>
              <span className="text-[9px] font-bold px-1.5 py-0.5 bg-white/10 text-zinc-300 rounded border border-white/5">
                {data.debts.length}
              </span>
            </div>
            <div className="glass-card rounded-[1.25rem] overflow-hidden divide-y divide-white/5">
              {data.debts.slice(0, 5).map((debt, i) => (
                <div
                  key={`${debt.client}-${debt.currency}`}
                  className="flex justify-between items-center p-3 sm:p-4 hover:bg-white/[0.02] transition-colors"
                >
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 flex items-center justify-center border border-white/10">
                      <span className="text-xs font-bold text-indigo-300">{debt.client.charAt(0).toUpperCase()}</span>
                    </div>
                    <div>
                      <p className="text-[13px] font-semibold text-zinc-100">{debt.client}</p>
                      <p className="text-[10px] font-medium text-zinc-500">{debt.currency}</p>
                    </div>
                  </div>
                  <p className={`text-[13px] font-bold tracking-tight ${debt.amount > 0 ? "text-amber-400" : "text-emerald-400"}`}>
                    {formatAmount(debt.amount, debt.currency)}
                  </p>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Recent Entries */}
        <section className="opacity-0 animate-slide-up stagger-3">
          <div className="flex items-center justify-between mb-2.5 px-1">
            <h2 className="text-[13px] font-bold text-zinc-100 tracking-wide">Транзакции</h2>
          </div>
          <div className="glass-card rounded-[1.25rem] overflow-hidden divide-y divide-white/5">
            {data.recent_entries.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-10 px-4 text-center">
                <div className="w-12 h-12 mb-3 rounded-full bg-white/5 flex items-center justify-center">
                  <span className="text-xl">📭</span>
                </div>
                <p className="text-[13px] font-medium text-zinc-300">Пока нет транзакций</p>
                <p className="text-[11px] text-zinc-500 mt-0.5">Здесь появится история ваших операций.</p>
              </div>
            ) : (
              data.recent_entries.map((entry) => {
                const isInflow = entry.flow_direction === "INFLOW";
                const entryDate = new Date(entry.created_at);
                return (
                  <div
                    key={entry.id}
                    className="p-3 sm:p-4 hover:bg-white/[0.02] transition-colors"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <div className={`w-5 h-5 rounded-full flex items-center justify-center shrink-0 border ${
                          isInflow 
                            ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400" 
                            : "bg-rose-500/10 border-rose-500/20 text-rose-400"
                        }`}>
                          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-3 h-3">
                            {isInflow ? (
                              <path fillRule="evenodd" d="M10 17a.75.75 0 01-.75-.75V5.612L5.29 9.77a.75.75 0 01-1.08-1.04l5.25-5.5a.75.75 0 011.08 0l5.25 5.5a.75.75 0 11-1.08 1.04l-3.96-4.158V16.25A.75.75 0 0110 17z" clipRule="evenodd" />
                            ) : (
                              <path fillRule="evenodd" d="M10 3a.75.75 0 01.75.75v10.638l3.96-4.158a.75.75 0 111.08 1.04l-5.25 5.5a.75.75 0 01-1.08 0l-5.25-5.5a.75.75 0 111.08-1.04l3.96 4.158V3.75A.75.75 0 0110 3z" clipRule="evenodd" />
                            )}
                          </svg>
                        </div>
                        <p className="text-xs font-bold text-zinc-200 truncate">{entry.client_name}</p>
                      </div>
                      <p className={`text-[13px] font-black tracking-tight shrink-0 ${
                        isInflow ? "text-emerald-400" : "text-white"
                      }`}>
                        {isInflow ? "+" : "-"}{formatAmount(entry.amount, entry.currency_code)}
                      </p>
                    </div>
                    <div className="flex justify-between items-center pl-7">
                      <p className="text-[10px] font-medium text-zinc-500 truncate max-w-[70%] leading-tight">
                        {entry.note || "Без комментария"}
                      </p>
                      <p className="text-[9px] font-bold text-zinc-600 shrink-0 tracking-wider">
                        {entryDate.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })}
                      </p>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </section>
      </div>

      {/* Floating Bottom Navigation */}
      <div className="fixed bottom-0 left-0 right-0 p-4 pb-safe pointer-events-none z-50 flex justify-center">
        <nav className="w-full max-w-[280px] sm:max-w-[320px] pointer-events-auto glass rounded-full px-1.5 py-1.5 flex justify-between items-center shadow-2xl animate-slide-up stagger-3">
          <button className="flex-1 flex flex-col items-center justify-center py-2 relative group text-indigo-400">
            <div className="absolute inset-0 bg-indigo-500/15 rounded-full blur-[4px] pointer-events-none" />
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="w-[18px] h-[18px] relative z-10 transition-transform active:scale-95">
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
              <polyline points="9 22 9 12 15 12 15 22"/>
            </svg>
            <span className="text-[8px] font-extrabold mt-1 tracking-wider uppercase opacity-90">Главная</span>
          </button>
          
          <button className="flex-1 flex flex-col items-center justify-center py-2 text-zinc-500 hover:text-zinc-300 transition-colors">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="w-[18px] h-[18px] transition-transform active:scale-95">
              <path d="M12 2v20"/>
              <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
            </svg>
            <span className="text-[8px] font-extrabold mt-1 tracking-wider uppercase opacity-80">Переводы</span>
          </button>

          <button className="flex-1 flex flex-col items-center justify-center py-2 text-zinc-500 hover:text-zinc-300 transition-colors">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="w-[18px] h-[18px] transition-transform active:scale-95">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="7 10 12 15 17 10"/>
              <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            <span className="text-[8px] font-extrabold mt-1 tracking-wider uppercase opacity-80">Экспорт</span>
          </button>
        </nav>
      </div>
    </main>
  );
}
