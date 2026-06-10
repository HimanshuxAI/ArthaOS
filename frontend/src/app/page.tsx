"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { ArrowDownToLine, Bot, FileText, LogOut, Send, ShieldCheck, Upload, WalletCards } from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { api, AuthResponse, Dashboard } from "@/lib/api";
import { formatInr } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const emptyDashboard: Dashboard = {
  metrics: { revenue: 0, expenses: 0, profit: 0, tax_estimate: 0 },
  revenue_trend: [],
  expense_breakdown: {},
  monthly_profit: [],
  transactions: [],
};

const chartColors = ["#0f766e", "#f59e0b", "#2563eb", "#db2777", "#64748b", "#9333ea"];

export default function Home() {
  const [authMode, setAuthMode] = useState<"register" | "login">("register");
  const [token, setToken] = useState<string>("");
  const [userName, setUserName] = useState<string>("");
  const [dashboard, setDashboard] = useState<Dashboard>(emptyDashboard);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [chatAnswer, setChatAnswer] = useState("Ask your CFO anything about your uploaded transactions.");
  const [status, setStatus] = useState("");

  const expensePie = useMemo(
    () => Object.entries(dashboard.expense_breakdown).map(([name, value]) => ({ name, value })),
    [dashboard.expense_breakdown],
  );

  const refresh = useCallback(async (activeToken = token) => {
    if (!activeToken) return;
    const data = await api.dashboard(activeToken);
    setDashboard(data);
  }, [token]);

  useEffect(() => {
    const stored = localStorage.getItem("arthaos-auth");
    if (stored) {
      const parsed = JSON.parse(stored) as AuthResponse;
      setToken(parsed.access_token);
      setUserName(parsed.user.name);
      void refresh(parsed.access_token);
    }
  }, [refresh]);

  async function handleAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setStatus("");
    const form = new FormData(event.currentTarget);
    try {
      const payload =
        authMode === "register"
          ? await api.register({
              name: String(form.get("name")),
              email: String(form.get("email")),
              password: String(form.get("password")),
            })
          : await api.login({
              email: String(form.get("email")),
              password: String(form.get("password")),
            });
      localStorage.setItem("arthaos-auth", JSON.stringify(payload));
      setToken(payload.access_token);
      setUserName(payload.user.name);
      await refresh(payload.access_token);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Authentication failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const file = form.get("file");
    const bank = String(form.get("bank"));
    if (!(file instanceof File) || !file.size) return;
    setBusy(true);
    setStatus("Processing statement...");
    try {
      const result = await api.upload(token, file, bank);
      await refresh();
      setStatus(`Imported ${result.imported} transactions.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleChat(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!message.trim()) return;
    setBusy(true);
    try {
      const result = await api.chat(token, message);
      setChatAnswer(result.answer);
      setMessage("");
    } catch (error) {
      setChatAnswer(error instanceof Error ? error.message : "Chat failed");
    } finally {
      setBusy(false);
    }
  }

  function logout() {
    localStorage.removeItem("arthaos-auth");
    setToken("");
    setUserName("");
    setDashboard(emptyDashboard);
  }

  return (
    <main className="min-h-screen fintech-grid">
      <section className="border-b border-border bg-white/80 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-950 text-white">
              <WalletCards size={20} />
            </div>
            <div>
              <p className="text-base font-bold">ArthaOS</p>
              <p className="text-xs text-slate-500">Financial OS for independent India</p>
            </div>
          </div>
          {token ? (
            <Button variant="outline" onClick={logout}>
              <LogOut size={16} /> Sign out
            </Button>
          ) : null}
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-8 px-5 py-10 lg:grid-cols-[0.9fr_1.1fr]">
        <div className="flex flex-col justify-center">
          <div className="mb-5 inline-flex w-fit items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-sm font-medium text-emerald-800">
            <ShieldCheck size={16} /> Built for HDFC, SBI, ICICI and Axis statements
          </div>
          <h1 className="max-w-3xl text-4xl font-bold tracking-normal text-slate-950 md:text-6xl">
            Understand Your Business Finances in 60 Seconds
          </h1>
          <p className="mt-5 max-w-2xl text-lg leading-8 text-slate-600">
            Upload a bank statement and get categorized transactions, profit and loss, tax estimates, and CFO-style answers without wrangling spreadsheets.
          </p>
          <div className="mt-7 flex flex-wrap gap-3">
            <Button asChild>
              <a href={token ? "#upload" : "#auth"}>
                <Upload size={18} /> Upload Statement
              </a>
            </Button>
            {token ? (
              <Button variant="outline" asChild>
                <a href={api.reportPdfUrl()} target="_blank" rel="noreferrer">
                  <FileText size={18} /> Export P&L
                </a>
              </Button>
            ) : null}
          </div>
        </div>

        {!token ? (
          <Card id="auth" className="shadow-soft">
            <CardHeader>
              <CardTitle>{authMode === "register" ? "Create your account" : "Log in to ArthaOS"}</CardTitle>
            </CardHeader>
            <CardContent>
              <form className="space-y-4" onSubmit={handleAuth}>
                {authMode === "register" ? (
                  <div className="space-y-2">
                    <Label htmlFor="name">Name</Label>
                    <Input id="name" name="name" required placeholder="Aarav Mehta" />
                  </div>
                ) : null}
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input id="email" name="email" type="email" required placeholder="you@business.in" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="password">Password</Label>
                  <Input id="password" name="password" type="password" required minLength={8} maxLength={72} placeholder="At least 8 characters" />
                </div>
                <Button className="w-full" disabled={busy}>
                  {authMode === "register" ? "Create account" : "Log in"}
                </Button>
              </form>
              <button className="mt-4 text-sm font-medium text-primary" onClick={() => setAuthMode(authMode === "register" ? "login" : "register")}>
                {authMode === "register" ? "Already have an account? Log in" : "New to ArthaOS? Create account"}
              </button>
              {status ? <p className="mt-4 text-sm text-destructive">{status}</p> : null}
            </CardContent>
          </Card>
        ) : (
          <UploadPanel busy={busy} status={status} userName={userName} onUpload={handleUpload} />
        )}
      </section>

      <section className="mx-auto max-w-7xl px-5 pb-12">
        <div className="grid gap-4 md:grid-cols-4">
          <Metric title="Revenue" value={dashboard.metrics.revenue} />
          <Metric title="Expenses" value={dashboard.metrics.expenses} />
          <Metric title="Profit" value={dashboard.metrics.profit} />
          <Metric title="Estimated Tax" value={dashboard.metrics.tax_estimate} />
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-3">
          <ChartCard title="Revenue Trend">
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={dashboard.revenue_trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="month" />
                <YAxis tickFormatter={(value) => `${Number(value) / 1000}k`} />
                <Tooltip formatter={(value) => formatInr(Number(value))} />
                <Area type="monotone" dataKey="revenue" stroke="#0f766e" fill="#99f6e4" />
              </AreaChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title="Expense Breakdown">
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie data={expensePie} dataKey="value" nameKey="name" outerRadius={82} label>
                  {expensePie.map((_, index) => (
                    <Cell key={index} fill={chartColors[index % chartColors.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value) => formatInr(Number(value))} />
              </PieChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title="Monthly Profit">
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={dashboard.monthly_profit}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="month" />
                <YAxis tickFormatter={(value) => `${Number(value) / 1000}k`} />
                <Tooltip formatter={(value) => formatInr(Number(value))} />
                <Bar dataKey="profit" fill="#f59e0b" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-[1.35fr_0.65fr]">
          <Card>
            <CardHeader>
              <CardTitle>Transactions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[720px] text-left text-sm">
                  <thead className="text-slate-500">
                    <tr>
                      <th className="py-3">Date</th>
                      <th>Description</th>
                      <th>Category</th>
                      <th>Type</th>
                      <th className="text-right">Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dashboard.transactions.map((tx) => (
                      <tr key={tx.id} className="border-t border-border">
                        <td className="py-3">{tx.date}</td>
                        <td className="font-medium">{tx.description}</td>
                        <td>{tx.category}</td>
                        <td className={tx.type === "income" ? "text-emerald-700" : "text-rose-700"}>{tx.type}</td>
                        <td className="text-right font-semibold">{formatInr(tx.amount)}</td>
                      </tr>
                    ))}
                    {!dashboard.transactions.length ? (
                      <tr>
                        <td colSpan={5} className="py-10 text-center text-slate-500">
                          Upload a statement to populate your ledger.
                        </td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Bot size={18} /> AI CFO Chat
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="rounded-lg bg-muted p-4 text-sm leading-6 text-slate-700">{chatAnswer}</div>
              <form className="mt-4 flex gap-2" onSubmit={handleChat}>
                <Input value={message} onChange={(event) => setMessage(event.target.value)} placeholder="What was my biggest expense?" />
                <Button size="icon" disabled={busy} aria-label="Ask CFO">
                  <Send size={17} />
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>
      </section>
    </main>
  );
}

function UploadPanel({
  busy,
  status,
  userName,
  onUpload,
}: {
  busy: boolean;
  status: string;
  userName: string;
  onUpload: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <Card id="upload" className="shadow-soft">
      <CardHeader>
        <CardTitle>Welcome, {userName}. Upload your statement.</CardTitle>
      </CardHeader>
      <CardContent>
        <form className="space-y-4" onSubmit={onUpload}>
          <div className="space-y-2">
            <Label htmlFor="bank">Bank</Label>
            <select id="bank" name="bank" className="h-10 w-full rounded-md border border-border bg-white px-3 text-sm">
              <option>HDFC</option>
              <option>SBI</option>
              <option>ICICI</option>
              <option>Axis</option>
            </select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="file">PDF or CSV statement</Label>
            <Input id="file" name="file" type="file" accept=".csv,.pdf" required />
          </div>
          <Button className="w-full" disabled={busy}>
            <ArrowDownToLine size={18} /> Process Statement
          </Button>
        </form>
        {status ? <p className="mt-4 text-sm text-slate-600">{status}</p> : null}
      </CardContent>
    </Card>
  );
}

function Metric({ title, value }: { title: string; value: number }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-2xl font-bold text-slate-950">{formatInr(value)}</p>
      </CardContent>
    </Card>
  );
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}
