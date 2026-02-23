/**
 * API client for the Currency MVP backend.
 * Uses the web API at /api/reports.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface DashboardData {
  server_time: string;
  balances: Record<string, number>;
  daily_profits: Record<string, number>;
  debts: DebtItem[];
  recent_entries: EntryItem[];
}

export interface DebtItem {
  client: string;
  currency: string;
  amount: number;
  last_updated: string | null;
}

export interface EntryItem {
  id: number;
  amount: number;
  currency_code: string;
  flow_direction: "INFLOW" | "OUTFLOW";
  client_name: string;
  note: string | null;
  created_at: string;
}

/**
 * Get the Telegram initData string from the Web App SDK.
 * Returns empty string if not running inside Telegram.
 */
function getInitData(): string {
  if (typeof window !== "undefined" && window.Telegram?.WebApp?.initData) {
    return window.Telegram.WebApp.initData;
  }
  return "";
}

/**
 * Fetch dashboard reports from the backend.
 */
export async function fetchDashboard(): Promise<DashboardData> {
  const initData = getInitData();
  
  const res = await fetch(`${API_BASE_URL}/api/reports`, {
    headers: {
      "Content-Type": "application/json",
      ...(initData ? { "X-TG-Init-Data": initData } : {}),
    },
  });

  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }

  return res.json();
}

/**
 * Format a number as currency display.
 */
export function formatAmount(value: number, currency: string): string {
  const formatted = Math.abs(value)
    .toFixed(2)
    .replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  return `${value < 0 ? "-" : ""}${formatted} ${currency}`;
}
