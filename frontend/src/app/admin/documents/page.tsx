"use client";

import { useEffect, useState, useRef } from "react";

interface Document {
    id: number;
    name: string;
    doc_type: string;
    org_id: number;
    status: string;
    error_message: string | null;
    file_size: number | null;
    chunk_count: number | null;
}

interface Organization {
    id: number;
    name: string;
}

export default function DocumentsPage() {
    const [documents, setDocuments] = useState<Document[]>([]);
    const [organizations, setOrganizations] = useState<Organization[]>([]);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState<{ current: number, total: number } | null>(null);

    // Upload form state & Global Filter
    const [selectedOrgId, setSelectedOrgId] = useState<string>("all");
    const [uploadMode, setUploadMode] = useState<"file" | "confluence">("file");
    const [confluenceUrl, setConfluenceUrl] = useState("");
    const [confluenceName, setConfluenceName] = useState("");
    const fileInputRef = useRef<HTMLInputElement>(null);

    const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
    const headers = { Authorization: `Bearer ${token}` };

    const fetchData = () => {
        Promise.all([
            fetch("http://localhost:8000/api/admin/documents", { headers }).then((r) => r.json()),
            fetch("http://localhost:8000/api/admin/organizations", { headers }).then((r) => r.json()),
        ])
            .then(([docsData, orgsData]) => {
                setDocuments(Array.isArray(docsData) ? docsData : []);
                setOrganizations(Array.isArray(orgsData) ? orgsData : []);
            })
            .catch(console.error)
            .finally(() => setLoading(false));
    };

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 5000);
        return () => clearInterval(interval);
    }, []);

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = e.target.files;
        if (!files || files.length === 0 || selectedOrgId === "all") return;

        setUploading(true);
        setUploadProgress({ current: 0, total: files.length });

        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            setUploadProgress({ current: i + 1, total: files.length });

            const formData = new FormData();
            formData.append("file", file);
            formData.append("org_id", selectedOrgId);

            try {
                const res = await fetch("http://localhost:8000/api/admin/documents/upload", {
                    method: "POST",
                    headers: { Authorization: `Bearer ${token}` },
                    body: formData,
                });

                if (!res.ok) {
                    const data = await res.json();
                    console.error(`Upload failed for ${file.name}:`, data.detail);
                }
            } catch (error) {
                console.error(`Upload error for ${file.name}:`, error);
            }
        }

        setUploading(false);
        setUploadProgress(null);
        fetchData();
        if (fileInputRef.current) {
            fileInputRef.current.value = "";
        }
    };

    const handleConfluenceSubmit = async () => {
        if (!confluenceUrl || !confluenceName || selectedOrgId === "all") return;

        setUploading(true);
        try {
            const res = await fetch("http://localhost:8000/api/admin/documents/confluence", {
                method: "POST",
                headers: { ...headers, "Content-Type": "application/json" },
                body: JSON.stringify({
                    url: confluenceUrl,
                    name: confluenceName,
                    org_id: parseInt(selectedOrgId),
                }),
            });

            if (res.ok) {
                setConfluenceUrl("");
                setConfluenceName("");
                fetchData();
            } else {
                const data = await res.json();
                alert(data.detail || "Ingestion failed");
            }
        } catch (error) {
            alert("Ingestion failed");
        } finally {
            setUploading(false);
        }
    };

    const handleDelete = async (id: number) => {
        if (!confirm("Delete this document? This will remove data from Neo4j and ChromaDB.")) return;

        try {
            const res = await fetch(`http://localhost:8000/api/admin/documents/${id}`, {
                method: "DELETE",
                headers,
            });

            if (res.ok) {
                fetchData();
            }
        } catch (error) {
            alert("Delete failed");
        }
    };

    const getStatusBadge = (status: string) => {
        const styles: Record<string, string> = {
            pending: "bg-yellow-500/20 text-yellow-400",
            ingesting: "bg-blue-500/20 text-blue-400",
            ingested: "bg-green-500/20 text-green-400",
            failed: "bg-red-500/20 text-red-400",
        };
        return `px-2 py-1 rounded text-xs ${styles[status] || ""}`;
    };

    const getOrgName = (orgId: number) => {
        return organizations.find((o) => o.id === orgId)?.name || "-";
    };

    if (loading) return <div>Loading...</div>;

    return (
        <div>
            <h1 className="text-2xl font-bold mb-6">Documents Management</h1>

            {/* Config & Upload Section */}
            <div className="card mb-6">
                <div className="mb-6 pb-4 border-b border-[var(--border)]">
                    <h3 className="font-semibold text-lg">Configuration & Upload</h3>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <div className="space-y-6">
                        {/* Organization Selection moved here */}
                        <div>
                            <label className="block text-sm font-semibold mb-2">Organization</label>
                            <select
                                value={selectedOrgId}
                                onChange={(e) => setSelectedOrgId(e.target.value)}
                                className="w-full text-base py-2.5"
                            >
                                <option value="all">All Organizations (Filter Only)</option>
                                {organizations.map((org) => (
                                    <option key={org.id} value={org.id.toString()}>
                                        {org.name}
                                    </option>
                                ))}
                            </select>
                        </div>

                        <div>
                            <label className="block text-sm font-semibold mb-3">Source Type</label>
                            <div className="flex gap-4">
                                <label className={`flex flex-1 items-center justify-center gap-2 cursor-pointer px-4 py-3 rounded-xl border-2 transition-all ${uploadMode === "file" ? "border-[var(--hsbc-red)] bg-red-50" : "border-[var(--border)] hover:border-[var(--hsbc-gray-300)]"}`}>
                                    <input
                                        type="radio"
                                        checked={uploadMode === "file"}
                                        onChange={() => setUploadMode("file")}
                                        className="hidden"
                                    />
                                    <span className={`text-sm font-semibold ${uploadMode === "file" ? "text-[var(--hsbc-red)]" : "text-[var(--muted)]"}`}>📁 File Upload</span>
                                </label>
                                <label className={`flex flex-1 items-center justify-center gap-2 cursor-pointer px-4 py-3 rounded-xl border-2 transition-all ${uploadMode === "confluence" ? "border-[var(--hsbc-red)] bg-red-50" : "border-[var(--border)] hover:border-[var(--hsbc-gray-300)]"}`}>
                                    <input
                                        type="radio"
                                        checked={uploadMode === "confluence"}
                                        onChange={() => setUploadMode("confluence")}
                                        className="hidden"
                                    />
                                    <span className={`text-sm font-semibold ${uploadMode === "confluence" ? "text-[var(--hsbc-red)]" : "text-[var(--muted)]"}`}>🌐 Confluence</span>
                                </label>
                            </div>
                        </div>
                    </div>

                    <div className="flex flex-col justify-end">
                        {uploadMode === "file" ? (
                            <>
                                <input
                                    ref={fileInputRef}
                                    type="file"
                                    accept=".pdf,.txt,.html,.docx,.xlsx"
                                    multiple
                                    onChange={handleFileUpload}
                                    disabled={uploading || selectedOrgId === "all"}
                                    className="hidden"
                                    id="file-upload"
                                />
                                <label
                                    htmlFor="file-upload"
                                    className={`drop-zone block cursor-pointer text-center p-8 border-2 border-dashed rounded-xl transition-all h-[180px] flex flex-col items-center justify-center ${selectedOrgId === "all" ? "bg-gray-50 border-gray-200 cursor-not-allowed opacity-60" : "border-[var(--border)] hover:border-[var(--hsbc-red)] hover:bg-red-50"}`}
                                >
                                    <div className="text-3xl mb-2">📄</div>
                                    <div className="font-semibold mb-1">
                                        {selectedOrgId === "all"
                                            ? "Select Organization First"
                                            : uploading ? `Uploading... (${uploadProgress?.current}/${uploadProgress?.total})` : "Click or drop multiple files"}
                                    </div>
                                    <div className="text-xs text-[var(--muted)]">PDF, TXT, HTML, DOCX, XLSX supported</div>
                                </label>
                            </>
                        ) : (
                            <div className="space-y-4 bg-gray-50 p-6 rounded-xl border border-[var(--border)] h-[180px] flex flex-col justify-center">
                                <div className="grid grid-cols-1 gap-3">
                                    <input
                                        value={confluenceName}
                                        onChange={(e) => setConfluenceName(e.target.value)}
                                        placeholder="Document name"
                                        disabled={selectedOrgId === "all"}
                                        className="w-full"
                                    />
                                    <input
                                        value={confluenceUrl}
                                        onChange={(e) => setConfluenceUrl(e.target.value)}
                                        placeholder="Confluence page URL"
                                        disabled={selectedOrgId === "all"}
                                        className="w-full"
                                    />
                                </div>
                                <button
                                    onClick={handleConfluenceSubmit}
                                    disabled={uploading || !confluenceUrl || !confluenceName || selectedOrgId === "all"}
                                    className="btn-primary w-full"
                                >
                                    {selectedOrgId === "all" ? "Select Organization First" : uploading ? "Ingesting..." : "🔗 Ingest from Confluence"}
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Documents Table */}
            <div className="card">
                <div className="flex justify-between items-center mb-6">
                    <h3 className="font-semibold text-lg">Document List</h3>
                    <div className="text-sm text-[var(--muted)] bg-[var(--hsbc-gray-100)] px-3 py-1.5 rounded-full font-medium">
                        {selectedOrgId === "all" ? "🌎 Showing All Files" : `🏢 Filtered by: ${getOrgName(parseInt(selectedOrgId))}`}
                    </div>
                </div>

                <div className="overflow-x-auto">
                    <table>
                        <thead>
                            <tr>
                                <th>Document Name</th>
                                <th>Type</th>
                                <th>Organization</th>
                                <th>Status</th>
                                <th>Nodes</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {documents
                                .filter(doc => selectedOrgId === "all" || doc.org_id === parseInt(selectedOrgId))
                                .map((doc) => (
                                    <tr key={doc.id}>
                                        <td className="font-semibold text-[var(--hsbc-gray-700)]">
                                            <a
                                                href={`http://localhost:8000/api/admin/documents/${doc.id}/view?token=${token}`}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="text-[var(--hsbc-red)] hover:underline"
                                            >
                                                {doc.name}
                                            </a>
                                        </td>
                                        <td><span className="text-xs font-mono uppercase bg-gray-100 px-2 py-0.5 rounded text-gray-600">{doc.doc_type}</span></td>
                                        <td className="text-sm">{getOrgName(doc.org_id)}</td>
                                        <td>
                                            <span className={getStatusBadge(doc.status)}>{doc.status}</span>
                                            {doc.error_message && (
                                                <span className="text-xs text-[var(--hsbc-red)] ml-2 cursor-help" title={doc.error_message}>
                                                    ⚠️
                                                </span>
                                            )}
                                        </td>
                                        <td className="text-[var(--muted)] font-mono text-sm">{doc.chunk_count ?? "-"}</td>
                                        <td>
                                            <button
                                                onClick={() => handleDelete(doc.id)}
                                                className="text-[var(--hsbc-red)] hover:underline text-sm font-medium"
                                            >
                                                Delete
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            {documents.filter(doc => selectedOrgId === "all" || doc.org_id === parseInt(selectedOrgId)).length === 0 && (
                                <tr>
                                    <td colSpan={6} className="text-center py-12 text-[var(--muted)] bg-gray-50/50">
                                        No documents found for this selection
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
