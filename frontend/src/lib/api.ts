export type User = {
  id: number;
  name: string;
  email: string;
  created_at: string;
};

export type AuthResponse = {
  access_token: string;
  token_type: string;
  user: User;
};

export type Transaction = {
  id: number;
  date: string;
  description: string;
  amount: number;
  type: "income" | "expense";
  category: string;
  created_at: string;
};

export type Dashboard = {
  metrics: {
    revenue: number;
    expenses: number;
    profit: number;
    tax_estimate: number;
  };
  revenue_trend: Array<{ month: string; revenue: number }>;
  expense_breakdown: Record<string, number>;
  monthly_profit: Array<{ month: string; profit: number }>;
  transactions: Transaction[];
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, init: RequestInit = {}, token?: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      ...(init.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail ?? "Request failed");
  }
  return response.json() as Promise<T>;
}

export const api = {
  register: (payload: { name: string; email: string; password: string }) =>
    request<AuthResponse>("/auth/register", { method: "POST", body: JSON.stringify(payload) }),
  login: (payload: { email: string; password: string }) =>
    request<AuthResponse>("/auth/login", { method: "POST", body: JSON.stringify(payload) }),
  dashboard: (token: string) => request<Dashboard>("/dashboard", {}, token),
  upload: (token: string, file: File, bank: string) => {
    const form = new FormData();
    form.append("bank", bank);
    form.append("file", file);
    return request<{ imported: number }>("/upload", { method: "POST", body: form }, token);
  },
  chat: (token: string, message: string) =>
    request<{ answer: string }>("/chat", { method: "POST", body: JSON.stringify({ message }) }, token),
  reportPdfUrl: () => `${API_URL}/reports/latest.pdf`,
};
