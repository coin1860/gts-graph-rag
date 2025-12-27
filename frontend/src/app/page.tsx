"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

// HSBC Logo SVG Component
const HSBCLogo = () => (
  <svg viewBox="0 0 100 50" style={{ height: 48, width: "auto" }}>
    <polygon points="50,0 75,12.5 75,37.5 50,50 25,37.5 25,12.5" fill="#DB0011" />
    <polygon points="50,0 62.5,6.25 62.5,18.75 50,25 37.5,18.75 37.5,6.25" fill="white" />
    <polygon points="50,25 62.5,31.25 62.5,43.75 50,50 37.5,43.75 37.5,31.25" fill="white" />
    <polygon points="25,12.5 37.5,18.75 37.5,31.25 25,37.5" fill="white" />
    <polygon points="75,12.5 62.5,18.75 62.5,31.25 75,37.5" fill="white" />
  </svg>
);

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await fetch("http://localhost:8000/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Login failed");
      }

      const { access_token } = await res.json();

      // Store token
      localStorage.setItem("token", access_token);
      document.cookie = `token=${access_token}; path=/`;

      // Redirect to chat
      router.push("/chat");
    } catch (err: any) {
      setError(err.message || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center p-4"
      style={{ background: "linear-gradient(135deg, #F5F5F5 0%, #E8E8E8 100%)" }}
    >
      <div className="card w-full max-w-md">
        <div className="text-center mb-8">
          <div className="flex justify-center mb-4">
            <HSBCLogo />
          </div>
          <h1 className="text-2xl font-bold mb-2" style={{ color: "#333333" }}>
            BOI Knowledge Assistant
          </h1>
          <p className="text-[var(--muted)]">Sign in to access your knowledge base</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div
              className="border rounded-lg p-3 text-sm"
              style={{
                background: "rgba(219, 0, 17, 0.1)",
                borderColor: "#DB0011",
                color: "#DB0011"
              }}
            >
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium mb-2" style={{ color: "#333333" }}>
              Username
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter username"
              required
              style={{ borderColor: "#D0D0D0" }}
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2" style={{ color: "#333333" }}>
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              required
              style={{ borderColor: "#D0D0D0" }}
            />
          </div>

          <button
            type="submit"
            className="w-full py-3 rounded-lg font-medium text-white transition-colors"
            disabled={loading}
            style={{
              background: loading ? "#D0D0D0" : "#DB0011",
              cursor: loading ? "not-allowed" : "pointer"
            }}
          >
            {loading ? "Signing in..." : "Sign In"}
          </button>
        </form>

        <div className="mt-6 pt-6 border-t text-center" style={{ borderColor: "#E8E8E8" }}>
          <p className="text-xs text-[var(--muted)]">
            Powered by HSBC Global Technology Services
          </p>
        </div>
      </div>
    </div>
  );
}
