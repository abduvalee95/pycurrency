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
    <main className="min-h-screen bg-[#0f0f1a] text-white pb-8">
      {/* Header */}
      <header className="sticky top-0 z-10 backdrop-blur-xl bg-[#0f0f1a]/80 border-b border-white/5 px-4 py-3">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-lg font-bold bg-gradient-to-r from-blue-400 to-violet-400 bg-clip-text text-transparent">
              💱 Currency MVP
            </h1>
            <p className="text-[11px] text-gray-500">
              {user ? `${user.first_name}` : ""} • {serverTime.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })}
            </p>
          </div>
          <button
            onClick={loadData}
            className="p-2 hover:bg-white/5 rounded-full transition-colors"
            title="Обновить"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-gray-400">
              <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
              <path d="M3 3v5h5"/>
              <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/>
              <path d="M16 16h5v5"/>
            </svg>
          </button>
        </div>
      </header>

      <div className="px-4 space-y-4 mt-4">
        {/* Balances Cards */}
        <section>
          <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 px-1">Балансы</h2>
          <div className="grid grid-cols-2 gap-3">
            {currencies.map((cur) => {
              const balance = data.balances[cur] || 0;
              const dailyProfit = data.daily_profits[cur] || 0;
              const isPositive = balance >= 0;
              return (
                <div
                  key={cur}
                  className="bg-gradient-to-br from-[#1a1a2e] to-[#16162a] border border-white/5 rounded-2xl p-4 relative overflow-hidden"
                >
                  <div className="absolute inset-0 bg-gradient-to-br from-blue-600/5 to-violet-600/5"></div>
                  <div className="relative">
                    <p className="text-xs text-gray-500 font-medium">{cur}</p>
                    <p className={`text-lg font-bold mt-1 ${isPositive ? "text-emerald-400" : "text-red-400"}`}>
                      {formatAmount(balance, "")}
                    </p>
                    {dailyProfit !== 0 && (
                      <p className={`text-[11px] mt-1 ${dailyProfit > 0 ? "text-emerald-500/70" : "text-red-500/70"}`}>
                        Сегодня: {dailyProfit > 0 ? "+" : ""}{formatAmount(dailyProfit, "")}
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* Client Debts */}
        {data.debts.length > 0 && (
          <section>
            <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 px-1">
              Долги клиентов
            </h2>
            <div className="bg-[#1a1a2e] border border-white/5 rounded-2xl overflow-hidden">
              {data.debts.slice(0, 10).map((debt, i) => (
                <div
                  key={`${debt.client}-${debt.currency}`}
                  className={`flex justify-between items-center px-4 py-3 ${
                    i !== Math.min(data.debts.length, 10) - 1 ? "border-b border-white/5" : ""
                  }`}
                >
                  <div>
                    <p className="text-sm font-medium text-gray-200">{debt.client}</p>
                    <p className="text-[11px] text-gray-600">{debt.currency}</p>
                  </div>
                  <p className={`text-sm font-semibold ${debt.amount > 0 ? "text-amber-400" : "text-emerald-400"}`}>
                    {formatAmount(debt.amount, debt.currency)}
                  </p>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Recent Entries */}
        <section>
          <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 px-1">
            Последние операции
          </h2>
          <div className="bg-[#1a1a2e] border border-white/5 rounded-2xl overflow-hidden">
            {data.recent_entries.length === 0 ? (
              <div className="flex flex-col items-center py-8 text-gray-600">
                <p className="text-sm">Нет операций</p>
              </div>
            ) : (
              data.recent_entries.map((entry, i) => {
                const isInflow = entry.flow_direction === "INFLOW";
                const entryDate = new Date(entry.created_at);
                return (
                  <div
                    key={entry.id}
                    className={`flex items-center gap-3 px-4 py-3 ${
                      i !== data.recent_entries.length - 1 ? "border-b border-white/5" : ""
                    }`}
                  >
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm shrink-0 ${
                      isInflow ? "bg-emerald-950/50 text-emerald-400" : "bg-red-950/50 text-red-400"
                    }`}>
                      {isInflow ? "↓" : "↑"}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex justify-between items-start">
                        <p className="text-sm font-medium text-gray-200 truncate">{entry.client_name}</p>
                        <p className={`text-sm font-semibold shrink-0 ml-2 ${
                          isInflow ? "text-emerald-400" : "text-red-400"
                        }`}>
                          {isInflow ? "+" : "-"}{formatAmount(entry.amount, entry.currency_code)}
                        </p>
                      </div>
                      <div className="flex justify-between items-center mt-0.5">
                        <p className="text-[11px] text-gray-600 truncate">
                          {entry.note || "—"}
                        </p>
                        <p className="text-[11px] text-gray-600 shrink-0 ml-2">
                          {entryDate.toLocaleDateString("ru-RU", { day: "2-digit", month: "2-digit" })}
                          {" "}
                          {entryDate.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })}
                        </p>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
