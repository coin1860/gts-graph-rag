"use client";

import { useEffect, useState } from "react";

interface User {
    id: number;
    username: string;
    email: string | null;
    role: string;
    is_active: boolean;
    organizations: { id: number; name: string }[];
}

interface Organization {
    id: number;
    name: string;
}

export default function UsersPage() {
    const [users, setUsers] = useState<User[]>([]);
    const [organizations, setOrganizations] = useState<Organization[]>([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [editingUser, setEditingUser] = useState<User | null>(null);

    // Form state
    const [username, setUsername] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [role, setRole] = useState("user");
    const [orgIds, setOrgIds] = useState<number[]>([]);

    const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
    const headers = { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };

    const fetchData = () => {
        Promise.all([
            fetch("http://localhost:8000/api/admin/users", { headers }).then((r) => r.json()),
            fetch("http://localhost:8000/api/admin/organizations", { headers }).then((r) => r.json()),
        ])
            .then(([usersData, orgsData]) => {
                setUsers(usersData);
                setOrganizations(orgsData);
            })
            .catch(console.error)
            .finally(() => setLoading(false));
    };

    useEffect(() => {
        fetchData();
    }, []);

    const openCreate = () => {
        setEditingUser(null);
        setUsername("");
        setEmail("");
        setPassword("");
        setRole("user");
        setOrgIds([]);
        setShowModal(true);
    };

    const openEdit = (user: User) => {
        setEditingUser(user);
        setUsername(user.username);
        setEmail(user.email || "");
        setPassword("");
        setRole(user.role);
        setOrgIds(user.organizations.map((o) => o.id));
        setShowModal(true);
    };

    const handleSubmit = async () => {
        const body: any = {
            username,
            email: email || null,
            role,
            organization_ids: orgIds,
        };

        if (password) {
            body.password = password;
        }

        const url = editingUser
            ? `http://localhost:8000/api/admin/users/${editingUser.id}`
            : "http://localhost:8000/api/admin/users";

        const method = editingUser ? "PUT" : "POST";

        const res = await fetch(url, { method, headers, body: JSON.stringify(body) });

        if (res.ok) {
            setShowModal(false);
            fetchData();
        } else {
            const data = await res.json();
            alert(data.detail || "Error saving user");
        }
    };

    const handleDelete = async (id: number) => {
        if (!confirm("Delete this user?")) return;

        const res = await fetch(`http://localhost:8000/api/admin/users/${id}`, {
            method: "DELETE",
            headers,
        });

        if (res.ok) {
            fetchData();
        } else {
            const data = await res.json();
            alert(data.detail || "Error deleting user");
        }
    };

    const toggleOrg = (orgId: number) => {
        setOrgIds((prev) =>
            prev.includes(orgId) ? prev.filter((id) => id !== orgId) : [...prev, orgId]
        );
    };

    if (loading) return <div>Loading...</div>;

    return (
        <div>
            <div className="flex justify-between items-center mb-6">
                <h1 className="text-2xl font-bold">Users</h1>
                <button onClick={openCreate} className="btn-primary">
                    + New User
                </button>
            </div>

            <div className="card">
                <table>
                    <thead>
                        <tr>
                            <th>Username</th>
                            <th>Email</th>
                            <th>Role</th>
                            <th>Organizations</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {users.map((user) => (
                            <tr key={user.id}>
                                <td className="font-medium">{user.username}</td>
                                <td className="text-[var(--muted)]">{user.email || "-"}</td>
                                <td>
                                    <span className={user.role === "admin" ? "text-[var(--primary)]" : ""}>
                                        {user.role}
                                    </span>
                                </td>
                                <td className="text-sm text-[var(--muted)]">
                                    {user.organizations.map((o) => o.name).join(", ") || "-"}
                                </td>
                                <td>
                                    <button onClick={() => openEdit(user)} className="text-[var(--primary)] mr-3">
                                        Edit
                                    </button>
                                    <button onClick={() => handleDelete(user.id)} className="text-[var(--error)]">
                                        Delete
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Modal */}
            {showModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
                    <div className="card w-full max-w-md">
                        <h2 className="text-xl font-bold mb-4">
                            {editingUser ? "Edit User" : "New User"}
                        </h2>

                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium mb-2">Username</label>
                                <input
                                    value={username}
                                    onChange={(e) => setUsername(e.target.value)}
                                    placeholder="Username"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium mb-2">Email</label>
                                <input
                                    type="email"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    placeholder="Optional email"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium mb-2">
                                    Password {editingUser && "(leave blank to keep current)"}
                                </label>
                                <input
                                    type="password"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    placeholder="Password"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium mb-2">Role</label>
                                <select value={role} onChange={(e) => setRole(e.target.value)}>
                                    <option value="user">User</option>
                                    <option value="admin">Admin</option>
                                </select>
                            </div>

                            <div>
                                <label className="block text-sm font-medium mb-2">Organizations</label>
                                <div className="checkbox-group max-h-32 overflow-y-auto">
                                    {organizations.map((org) => (
                                        <label key={org.id} className="checkbox-label">
                                            <input
                                                type="checkbox"
                                                checked={orgIds.includes(org.id)}
                                                onChange={() => toggleOrg(org.id)}
                                            />
                                            {org.name}
                                        </label>
                                    ))}
                                </div>
                            </div>
                        </div>

                        <div className="flex gap-3 mt-6">
                            <button onClick={() => setShowModal(false)} className="btn-secondary flex-1">
                                Cancel
                            </button>
                            <button onClick={handleSubmit} className="btn-primary flex-1">
                                {editingUser ? "Update" : "Create"}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
