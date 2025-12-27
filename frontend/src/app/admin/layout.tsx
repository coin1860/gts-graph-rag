"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

interface User {
    id: number;
    username: string;
    role: string;
}

// HSBC Logo SVG Component
const HSBCLogo = () => (
    <svg viewBox="0 0 100 50" style={{ height: 32, width: "auto" }}>
        <polygon points="50,0 75,12.5 75,37.5 50,50 25,37.5 25,12.5" fill="#DB0011" />
        <polygon points="50,0 62.5,6.25 62.5,18.75 50,25 37.5,18.75 37.5,6.25" fill="white" />
        <polygon points="50,25 62.5,31.25 62.5,43.75 50,50 37.5,43.75 37.5,31.25" fill="white" />
        <polygon points="25,12.5 37.5,18.75 37.5,31.25 25,37.5" fill="white" />
        <polygon points="75,12.5 62.5,18.75 62.5,31.25 75,37.5" fill="white" />
    </svg>
);

export default function AdminLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const pathname = usePathname();
    const router = useRouter();
    const [user, setUser] = useState<User | null>(null);

    useEffect(() => {
        const token = localStorage.getItem("token");
        if (!token) {
            router.push("/");
            return;
        }

        fetch("http://localhost:8000/api/auth/me", {
            headers: { Authorization: `Bearer ${token}` },
        })
            .then((res) => {
                if (!res.ok) throw new Error("Unauthorized");
                return res.json();
            })
            .then((data) => {
                if (data.role !== "admin") {
                    router.push("/chat");
                    return;
                }
                setUser(data);
            })
            .catch(() => {
                router.push("/");
            });
    }, [router]);

    const handleLogout = () => {
        localStorage.removeItem("token");
        document.cookie = "token=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT";
        router.push("/");
    };

    if (!user) {
        return (
            <div className="flex items-center justify-center h-screen">
                <div className="text-center">
                    <HSBCLogo />
                    <p className="mt-4 text-[var(--muted)]">Loading...</p>
                </div>
            </div>
        );
    }

    const navItems = [
        { href: "/admin", label: "Dashboard", icon: "📊" },
        { href: "/admin/organizations", label: "Organizations", icon: "🏢" },
        { href: "/admin/users", label: "Users", icon: "👥" },
        { href: "/admin/documents", label: "Documents", icon: "📄" },
    ];

    return (
        <div className="min-h-screen flex flex-col">
            {/* Header */}
            <header className="hsbc-header">
                <div className="hsbc-logo">
                    <HSBCLogo />
                    <span className="hsbc-logo-text">Admin Portal</span>
                </div>
                <div className="flex items-center gap-4">
                    <span className="text-sm text-[var(--muted)]">{user.username}</span>
                    <button
                        onClick={handleLogout}
                        className="text-sm text-[var(--muted)] hover:text-[var(--hsbc-red)]"
                    >
                        Logout
                    </button>
                </div>
            </header>

            <div className="admin-layout">
                <aside className="admin-sidebar">
                    <Link
                        href="/chat"
                        className="flex items-center gap-2 text-sm mb-4 px-3 py-2 rounded-lg"
                        style={{ color: "#DB0011" }}
                    >
                        ← Back to Chat
                    </Link>

                    <nav>
                        {navItems.map((item) => (
                            <Link
                                key={item.href}
                                href={item.href}
                                className={pathname === item.href ? "active" : ""}
                            >
                                <span>{item.icon}</span>
                                <span>{item.label}</span>
                            </Link>
                        ))}
                    </nav>
                </aside>

                <main className="admin-content">{children}</main>
            </div>
        </div>
    );
}
