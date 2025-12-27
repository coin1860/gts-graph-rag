"use client";

import { useEffect, useState } from "react";

interface Organization {
    id: number;
    name: string;
    description: string | null;
    graphrag_enabled: boolean;
    graph_schema: any;
}

export default function OrganizationsPage() {
    const [organizations, setOrganizations] = useState<Organization[]>([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [editingOrg, setEditingOrg] = useState<Organization | null>(null);

    // Form state
    const [name, setName] = useState("");
    const [description, setDescription] = useState("");
    const [graphragEnabled, setGraphragEnabled] = useState(false);

    const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
    const headers = { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };

    const fetchOrgs = () => {
        fetch("http://localhost:8000/api/admin/organizations", { headers })
            .then((res) => res.json())
            .then(setOrganizations)
            .catch(console.error)
            .finally(() => setLoading(false));
    };

    useEffect(() => {
        fetchOrgs();
    }, []);

    const openCreate = () => {
        setEditingOrg(null);
        setName("");
        setDescription("");
        setGraphragEnabled(false);
        setShowModal(true);
    };

    const openEdit = (org: Organization) => {
        setEditingOrg(org);
        setName(org.name);
        setDescription(org.description || "");
        setGraphragEnabled(org.graphrag_enabled);
        setShowModal(true);
    };

    const handleSubmit = async () => {
        const body = {
            name,
            description: description || null,
            graphrag_enabled: graphragEnabled,
        };

        const url = editingOrg
            ? `http://localhost:8000/api/admin/organizations/${editingOrg.id}`
            : "http://localhost:8000/api/admin/organizations";

        const method = editingOrg ? "PUT" : "POST";

        const res = await fetch(url, { method, headers, body: JSON.stringify(body) });

        if (res.ok) {
            setShowModal(false);
            fetchOrgs();
        } else {
            const data = await res.json();
            alert(data.detail || "Error saving organization");
        }
    };

    const handleDelete = async (id: number) => {
        if (!confirm("Delete this organization? This will also delete all documents.")) return;

        const res = await fetch(`http://localhost:8000/api/admin/organizations/${id}`, {
            method: "DELETE",
            headers,
        });

        if (res.ok) {
            fetchOrgs();
        }
    };

    if (loading) return <div>Loading...</div>;

    return (
        <div>
            <div className="flex justify-between items-center mb-6">
                <h1 className="text-2xl font-bold">Organizations</h1>
                <button onClick={openCreate} className="btn-primary">
                    + New Organization
                </button>
            </div>

            <div className="card">
                <table>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Description</th>
                            <th>GraphRAG</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {organizations.map((org) => (
                            <tr key={org.id}>
                                <td className="font-medium">{org.name}</td>
                                <td className="text-[var(--muted)]">{org.description || "-"}</td>
                                <td>
                                    {org.graphrag_enabled ? (
                                        <span className="text-[var(--success)]">✓ Enabled</span>
                                    ) : (
                                        <span className="text-[var(--muted)]">Disabled</span>
                                    )}
                                </td>
                                <td>
                                    <button onClick={() => openEdit(org)} className="text-[var(--primary)] mr-3">
                                        Edit
                                    </button>
                                    <button onClick={() => handleDelete(org.id)} className="text-[var(--error)]">
                                        Delete
                                    </button>
                                </td>
                            </tr>
                        ))}
                        {organizations.length === 0 && (
                            <tr>
                                <td colSpan={4} className="text-center text-[var(--muted)]">
                                    No organizations yet
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>

            {/* Modal */}
            {showModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
                    <div className="card w-full max-w-md">
                        <h2 className="text-xl font-bold mb-4">
                            {editingOrg ? "Edit Organization" : "New Organization"}
                        </h2>

                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium mb-2">Name</label>
                                <input
                                    value={name}
                                    onChange={(e) => setName(e.target.value)}
                                    placeholder="Organization name"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium mb-2">Description</label>
                                <textarea
                                    value={description}
                                    onChange={(e) => setDescription(e.target.value)}
                                    placeholder="Optional description"
                                    rows={2}
                                />
                            </div>

                            <div>
                                <label className="checkbox-label">
                                    <input
                                        type="checkbox"
                                        checked={graphragEnabled}
                                        onChange={(e) => setGraphragEnabled(e.target.checked)}
                                    />
                                    Enable GraphRAG (Knowledge Graph ingestion)
                                </label>
                            </div>
                        </div>

                        <div className="flex gap-3 mt-6">
                            <button onClick={() => setShowModal(false)} className="btn-secondary flex-1">
                                Cancel
                            </button>
                            <button onClick={handleSubmit} className="btn-primary flex-1">
                                {editingOrg ? "Update" : "Create"}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
