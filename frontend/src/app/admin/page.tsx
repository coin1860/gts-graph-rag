"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

interface Stats {
    organizations: number;
    users: number;
    documents: number;
}

export default function AdminDashboard() {
    const [stats, setStats] = useState<Stats>({ organizations: 0, users: 0, documents: 0 });

    useEffect(() => {
        const token = localStorage.getItem("token");
        if (!token) return;

        const headers = { Authorization: `Bearer ${token}` };

        Promise.all([
            fetch("http://localhost:8000/api/admin/organizations", { headers }).then(r => r.json()),
            fetch("http://localhost:8000/api/admin/users", { headers }).then(r => r.json()),
            fetch("http://localhost:8000/api/admin/documents", { headers }).then(r => r.json()),
        ]).then(([orgs, users, docs]) => {
            setStats({
                organizations: orgs.length,
                users: users.length,
                documents: docs.length,
            });
        }).catch(console.error);
    }, []);

    return (
        <div>
            <h1 className="text-2xl font-bold mb-6">Dashboard</h1>

            <div className="grid grid-cols-3 gap-6 mb-8">
                <Link href="/admin/organizations" className="card hover:shadow-md transition-shadow block">
                    <div className="text-3xl font-bold text-[var(--primary)]">{stats.organizations}</div>
                    <div className="text-[var(--muted)]">Organizations</div>
                </Link>
                <Link href="/admin/users" className="card hover:shadow-md transition-shadow block">
                    <div className="text-3xl font-bold text-[var(--accent)]">{stats.users}</div>
                    <div className="text-[var(--muted)]">Users</div>
                </Link>
                <Link href="/admin/documents" className="card hover:shadow-md transition-shadow block">
                    <div className="text-3xl font-bold text-[var(--success)]">{stats.documents}</div>
                    <div className="text-[var(--muted)]">Documents</div>
                </Link>
            </div>

            <div className="grid grid-cols-2 gap-6">
                <Link href="/admin/organizations" className="card hover:border-[var(--primary)] transition-colors">
                    <h3 className="font-semibold mb-2">🏢 Manage Organizations</h3>
                    <p className="text-sm text-[var(--muted)]">Create and configure organizations with GraphRAG settings</p>
                </Link>
                <Link href="/admin/users" className="card hover:border-[var(--primary)] transition-colors">
                    <h3 className="font-semibold mb-2">👥 Manage Users</h3>
                    <p className="text-sm text-[var(--muted)]">Add users and assign organization access</p>
                </Link>
                <Link href="/admin/documents" className="card hover:border-[var(--primary)] transition-colors">
                    <h3 className="font-semibold mb-2">📄 Manage Documents</h3>
                    <p className="text-sm text-[var(--muted)]">Upload and manage knowledge base documents</p>
                </Link>
                <Link href="/chat" className="card hover:border-[var(--primary)] transition-colors">
                    <h3 className="font-semibold mb-2">💬 Go to Chat</h3>
                    <p className="text-sm text-[var(--muted)]">Test the RAG system with queries</p>
                </Link>
            </div>
        </div>
    );
}
