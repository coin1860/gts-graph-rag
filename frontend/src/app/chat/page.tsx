"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import dynamic from "next/dynamic";
import { v4 as uuidv4 } from "uuid";

// Dynamic import for ForceGraph2D (client-side only)
const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
    ssr: false,
    loading: () => <div className="graph-loading">Loading graph...</div>,
});

interface Organization {
    id: number;
    name: string;
}

interface Document {
    id: number;
    name: string;
    org_id: number;
    doc_type: string;
}

interface User {
    id: number;
    username: string;
    role: string;
    organizations: Organization[];
}

interface SourceItem {
    content: string;
    source: string;
    score: number;
    metadata: Record<string, any>;
}

interface Message {
    id: string;
    role: "user" | "assistant";
    content: string;
    sources?: SourceItem[];
    reasoningSteps?: string[];
}

// Graph visualization types
interface GraphNode {
    id: string;
    label: string;
    color?: string;
    x?: number;
    y?: number;
}

interface GraphEdge {
    source: string;
    target: string;
}

interface GraphData {
    nodes: GraphNode[];
    links: GraphEdge[];
}

// Graph Visualization Component
const GraphVisualization = ({
    data,
    onFullscreen,
}: {
    data: GraphData;
    onFullscreen: () => void;
}) => {
    const graphRef = useRef<any>(null);

    const handleNodeClick = useCallback((node: any, event: MouseEvent) => {
        if (graphRef.current && node.x !== undefined && node.y !== undefined) {
            graphRef.current.centerAt(node.x, node.y, 500);
            graphRef.current.zoom(2, 500);
        }
    }, []);

    // Custom node rendering with label
    const nodeCanvasObject = useCallback((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
        const label = node.label || node.id;
        const fontSize = Math.max(10 / globalScale, 3);
        ctx.font = `${fontSize}px Sans-Serif`;

        // Draw node circle
        ctx.beginPath();
        ctx.arc(node.x, node.y, 5, 0, 2 * Math.PI);
        ctx.fillStyle = node.color || "#0066CC";
        ctx.fill();

        // Draw label
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillStyle = "#333";
        ctx.fillText(label, node.x, node.y + 10);
    }, []);

    if (!data.nodes || data.nodes.length === 0) {
        return (
            <div className="graph-empty">
                <p>No graph data available</p>
                <p className="text-sm text-[var(--muted)]">Ask a question to see knowledge graph results</p>
            </div>
        );
    }

    return (
        <div className="graph-container">
            <ForceGraph2D
                ref={graphRef}
                graphData={data}
                nodeCanvasObject={nodeCanvasObject}
                nodeLabel={(node: any) => `${node.label} (${node.type || 'Entity'})`}
                linkColor={() => "#999"}
                linkWidth={2}
                linkDirectionalArrowLength={4}
                linkDirectionalArrowRelPos={1}
                linkLabel={(link: any) => link.label || ""}
                linkDirectionalParticles={2}
                linkDirectionalParticleSpeed={0.005}
                onNodeClick={handleNodeClick}
                enableNodeDrag={true}
                enableZoomInteraction={true}
                enablePanInteraction={true}
                width={280}
                height={200}
            />
            <button className="fullscreen-btn" onClick={onFullscreen} title="Fullscreen">

                ⛶
            </button>
        </div>
    );
};

// Fullscreen Graph Modal
const GraphFullscreenModal = ({
    data,
    onClose,
}: {
    data: GraphData;
    onClose: () => void;
}) => {
    const graphRef = useRef<any>(null);

    // Custom node rendering with label for fullscreen
    const nodeCanvasObject = useCallback((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
        const label = node.label || node.id;
        const fontSize = Math.max(14 / globalScale, 4);
        ctx.font = `${fontSize}px Sans-Serif`;

        // Draw node circle
        ctx.beginPath();
        ctx.arc(node.x, node.y, 8, 0, 2 * Math.PI);
        ctx.fillStyle = node.color || "#0066CC";
        ctx.fill();

        // Draw label
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillStyle = "#333";
        ctx.fillText(label, node.x, node.y + 15);
    }, []);

    return (
        <div className="graph-modal-overlay" onClick={onClose}>
            <div className="graph-modal" onClick={(e) => e.stopPropagation()}>
                <button className="modal-close-btn" onClick={onClose}>✕</button>
                <h3>📊 Knowledge Graph</h3>
                <div className="graph-modal-content">
                    <ForceGraph2D
                        ref={graphRef}
                        graphData={data}
                        nodeCanvasObject={nodeCanvasObject}
                        nodeLabel={(node: any) => `${node.label} (${node.type || 'Entity'})`}
                        linkColor={() => "#666"}
                        linkWidth={2}
                        linkDirectionalArrowLength={6}
                        linkDirectionalArrowRelPos={1}
                        linkLabel={(link: any) => link.label || ""}
                        linkDirectionalParticles={3}
                        linkDirectionalParticleSpeed={0.005}
                        enableNodeDrag={true}
                        enableZoomInteraction={true}
                        enablePanInteraction={true}
                    />
                </div>
            </div>
        </div>
    );
};




// Collapsible Section Component
const CollapsibleSection = ({
    title,
    icon,
    children,
    defaultOpen = false,
}: {
    title: string;
    icon: string;
    children: React.ReactNode;
    defaultOpen?: boolean;
}) => {
    const [isOpen, setIsOpen] = useState(defaultOpen);
    return (
        <div className="collapsible-section">
            <button className="collapsible-header" onClick={() => setIsOpen(!isOpen)}>
                <span>{icon} {title}</span>
                <span className="collapse-icon">{isOpen ? "▼" : "▶"}</span>
            </button>
            {isOpen && <div className="collapsible-content">{children}</div>}
        </div>
    );
};

// Collapsible Reasoning Step with Markdown support
const CollapsibleReasoningStep = ({
    step,
    index,
    isStreaming = false,
}: {
    step: string;
    index: number;
    isStreaming?: boolean;
}) => {
    const [isExpanded, setIsExpanded] = useState(false);
    const [wasStreaming, setWasStreaming] = useState(false);

    // Auto-expand when streaming starts, auto-collapse when streaming ends
    useEffect(() => {
        if (isStreaming && !wasStreaming) {
            // Streaming just started - expand
            setIsExpanded(true);
            setWasStreaming(true);
        } else if (!isStreaming && wasStreaming) {
            // Streaming just ended - collapse
            setIsExpanded(false);
            setWasStreaming(false);
        }
    }, [isStreaming, wasStreaming]);

    // Check if step contains node output (💬 pattern) - use [\s\S] for multiline
    const nodeOutputMatch = step.match(/^💬\s*\[([^\]]+)\]:\s*([\s\S]+)$/);

    if (nodeOutputMatch) {
        const nodeName = nodeOutputMatch[1];
        const content = nodeOutputMatch[2];

        return (
            <div className={`reasoning-step collapsible-step ${isStreaming ? 'streaming' : ''}`}>
                <button
                    className="step-header"
                    onClick={() => setIsExpanded(!isExpanded)}
                >
                    <span className="step-number">{index + 1}.</span>
                    <span className="step-icon">{isStreaming ? '⏳' : '💬'}</span>
                    <span className="step-title">[{nodeName}]</span>
                    <span className="step-arrow">{isExpanded ? "▼" : "▶"}</span>
                </button>
                {isExpanded && (
                    <div className="step-content">
                        <ReactMarkdown>{content}</ReactMarkdown>
                    </div>
                )}
            </div>
        );
    }

    // Regular step without collapsible content
    return (
        <div className="reasoning-step">{index + 1}. {step}</div>
    );
};

// Message Content Component with Markdown and Source Links
const MessageContent = ({
    content,
    sources,
    onSourceClick,
}: {
    content: string;
    sources?: SourceItem[];
    onSourceClick: (source: SourceItem) => void;
}) => {
    // Parse content and replace [Source X] with clickable elements
    const parseContent = (text: string): React.ReactNode[] => {
        const parts = text.split(/(\[Source \d+\])/g);

        return parts.map((part, index) => {
            const match = part.match(/\[Source (\d+)\]/);
            if (match && sources) {
                const sourceIndex = parseInt(match[1]) - 1;
                const source = sources[sourceIndex];
                if (source) {
                    return (
                        <button
                            key={index}
                            className="inline-source-link"
                            onClick={(e) => {
                                e.preventDefault();
                                onSourceClick(source);
                            }}
                        >
                            {part}
                        </button>
                    );
                }
            }
            return part;
        });
    };

    // Custom renderer for text elements in ReactMarkdown
    return (
        <div className="message-markdown">
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                    // Parse source links in text content
                    p: ({ children }) => {
                        const processChildren = (child: React.ReactNode): React.ReactNode => {
                            if (typeof child === 'string') {
                                return parseContent(child);
                            }
                            return child;
                        };
                        return <p>{Array.isArray(children) ? children.map(c => processChildren(c)) : processChildren(children)}</p>;
                    },
                    li: ({ children }) => {
                        const processChildren = (child: React.ReactNode): React.ReactNode => {
                            if (typeof child === 'string') {
                                return parseContent(child);
                            }
                            return child;
                        };
                        return <li>{Array.isArray(children) ? children.map(c => processChildren(c)) : processChildren(children)}</li>;
                    },
                    td: ({ children }) => {
                        const processChildren = (child: React.ReactNode): React.ReactNode => {
                            if (typeof child === 'string') {
                                return parseContent(child);
                            }
                            return child;
                        };
                        return <td>{Array.isArray(children) ? children.map(c => processChildren(c)) : processChildren(children)}</td>;
                    },
                }}
            >
                {content}
            </ReactMarkdown>
        </div>
    );
};

export default function ChatPage() {
    const router = useRouter();
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Auth state
    const [user, setUser] = useState<User | null>(null);
    const [token, setToken] = useState<string | null>(null);
    const [allOrgs, setAllOrgs] = useState<Organization[]>([]);

    // Chat state
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [currentReasoningSteps, setCurrentReasoningSteps] = useState<string[]>([]);
    const [currentAnswer, setCurrentAnswer] = useState("");
    const [currentSources, setCurrentSources] = useState<SourceItem[]>([]);

    // Sidebar state
    const [customPrompt, setCustomPrompt] = useState("");

    // Load customPrompt from localStorage on mount
    useEffect(() => {
        const savedPrompt = localStorage.getItem("customPrompt");
        if (savedPrompt) {
            setCustomPrompt(savedPrompt);
        }
    }, []);

    // Save customPrompt to localStorage on blur
    const handleCustomPromptBlur = () => {
        localStorage.setItem("customPrompt", customPrompt);
    };
    const [selectedOrgId, setSelectedOrgId] = useState<string>("all");
    const [documents, setDocuments] = useState<Document[]>([]);
    const [selectedFileIds, setSelectedFileIds] = useState<number[]>([]);

    // Right panel state - selected source
    const [selectedSource, setSelectedSource] = useState<SourceItem | null>(null);
    const [expandedReasoning, setExpandedReasoning] = useState<string | null>(null);

    // Graph visualization state
    const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
    const [showGraphFullscreen, setShowGraphFullscreen] = useState(false);

    // Temp knowledge state - use uuid package for cross-environment compatibility
    const [sessionId] = useState(() => uuidv4());
    const [tempFiles, setTempFiles] = useState<{ id: string; name: string; status: 'uploading' | 'ready' | 'error' }[]>([]);
    const [isDragging, setIsDragging] = useState(false);
    const tempFileInputRef = useRef<HTMLInputElement>(null);

    // Fetch user info on mount
    useEffect(() => {
        const storedToken = localStorage.getItem("token");
        if (!storedToken) {
            router.push("/");
            return;
        }
        setToken(storedToken);

        fetch("http://localhost:8000/api/auth/me", {
            headers: { Authorization: `Bearer ${storedToken}` },
        })
            .then((res) => {
                if (!res.ok) throw new Error("Unauthorized");
                return res.json();
            })
            .then((data) => {
                setUser(data);
                // For admin, fetch all orgs; for user, use their orgs
                if (data.role === "admin") {
                    fetch("http://localhost:8000/api/admin/organizations", {
                        headers: { Authorization: `Bearer ${storedToken}` },
                    })
                        .then((res) => res.json())
                        .then((orgs) => setAllOrgs(Array.isArray(orgs) ? orgs : []))
                        .catch(() => setAllOrgs(Array.isArray(data.organizations) ? data.organizations : []));
                } else {
                    setAllOrgs(Array.isArray(data.organizations) ? data.organizations : []);
                }
            })
            .catch(() => {
                localStorage.removeItem("token");
                router.push("/");
            });
    }, [router]);

    // Fetch documents when org changes
    useEffect(() => {
        if (!token) return;

        const orgIds = selectedOrgId === "all"
            ? allOrgs.map(o => o.id).join(",")
            : selectedOrgId;

        if (!orgIds) return;

        fetch(`http://localhost:8000/api/documents/search?org_ids=${orgIds}`, {
            headers: { Authorization: `Bearer ${token}` },
        })
            .then((res) => res.json())
            .then((data) => setDocuments(Array.isArray(data) ? data : []))
            .catch(console.error);
    }, [token, selectedOrgId, allOrgs]);

    // Scroll to bottom on new messages
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, currentAnswer]);

    const handleSend = async () => {
        if (!input.trim() || isLoading || !token) return;

        const userMessage: Message = {
            id: Date.now().toString(),
            role: "user",
            content: input,
        };

        setMessages((prev) => [...prev, userMessage]);
        setInput("");
        setIsLoading(true);
        setCurrentReasoningSteps([]);
        setCurrentAnswer("");
        setCurrentSources([]);
        setSelectedSource(null);

        try {
            // Determine org_ids to send
            const orgIds = selectedOrgId === "all"
                ? allOrgs.map(o => o.id)
                : [parseInt(selectedOrgId)];

            const response = await fetch("http://localhost:8000/api/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({
                    message: input,
                    org_ids: orgIds.length > 0 ? orgIds : null,
                    file_ids: selectedFileIds.length > 0 ? selectedFileIds : null,
                    custom_prompt: customPrompt || null,
                    session_id: sessionId,
                    temp_file_ids: tempFiles.filter(f => f.status === 'ready').map(f => f.id),
                }),
            });

            if (!response.ok) throw new Error("Chat failed");

            const reader = response.body?.getReader();
            if (!reader) return;

            const decoder = new TextDecoder();
            let assistantContent = "";
            let messageId = "";
            let reasoningSteps: string[] = [];
            let sources: SourceItem[] = [];

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const text = decoder.decode(value);
                const lines = text.split("\n");

                for (const line of lines) {
                    if (!line.startsWith("data: ")) continue;

                    try {
                        const data = JSON.parse(line.slice(6));

                        switch (data.type) {
                            case "start":
                                messageId = data.messageId;
                                break;
                            case "node-start":
                                // Show node starting
                                const startNode = data.data.display || data.data.node;
                                reasoningSteps = [...reasoningSteps, `⏳ ${startNode}...`];
                                setCurrentReasoningSteps(reasoningSteps);
                                break;
                            case "node-end":
                                // Mark node as complete
                                const endNode = data.data.display || data.data.node;
                                reasoningSteps = reasoningSteps.map(step =>
                                    step.includes(endNode) && step.startsWith("⏳")
                                        ? step.replace("⏳", "")
                                        : step
                                );
                                setCurrentReasoningSteps(reasoningSteps);
                                break;
                            case "llm-token":
                                // Real-time LLM token streaming - show in reasoning
                                const token = data.data.token;
                                const tokenNode = data.data.node;
                                // Append token to last step or create new step for this node
                                const lastStep = reasoningSteps[reasoningSteps.length - 1] || "";
                                const llmPrefix = `💬 [${tokenNode}]: `;
                                if (lastStep.startsWith(llmPrefix)) {
                                    // Append to existing LLM stream
                                    reasoningSteps[reasoningSteps.length - 1] = lastStep + token;
                                } else {
                                    // Start new LLM stream step
                                    reasoningSteps = [...reasoningSteps, llmPrefix + token];
                                }
                                setCurrentReasoningSteps([...reasoningSteps]);
                                break;
                            case "node-steps":
                                // Static steps from node (not LLM streaming)
                                const nodeSteps = data.data.steps || [];
                                reasoningSteps = [...reasoningSteps, ...nodeSteps];
                                setCurrentReasoningSteps(reasoningSteps);
                                break;
                            case "data-step":
                                reasoningSteps = [...reasoningSteps, data.data.step];
                                setCurrentReasoningSteps(reasoningSteps);
                                break;
                            case "data-sources":
                                sources = data.data.sources || [];
                                setCurrentSources(sources);
                                break;
                            case "text-delta":
                                assistantContent += data.delta;
                                setCurrentAnswer(assistantContent);
                                break;
                            case "text-content":
                                // Full content (not streaming)
                                assistantContent = data.content;
                                setCurrentAnswer(assistantContent);
                                break;
                            case "error":
                                reasoningSteps = [...reasoningSteps, `❌ ${data.message}`];
                                setCurrentReasoningSteps(reasoningSteps);
                                break;
                            case "graph-data":
                                // Graph visualization data from graph_retriever
                                const graphNodes = data.data.nodes || [];
                                const graphLinks = data.data.links || [];
                                setGraphData({
                                    nodes: graphNodes,
                                    links: graphLinks,
                                });
                                break;

                            case "finish":
                                break;
                        }
                    } catch (e) {
                        // Ignore parse errors
                    }
                }
            }

            // Add assistant message with sources and reasoning
            setMessages((prev) => [
                ...prev,
                {
                    id: messageId || Date.now().toString(),
                    role: "assistant",
                    content: assistantContent,
                    sources: sources,
                    reasoningSteps: reasoningSteps,
                },
            ]);
            setCurrentAnswer("");
            setCurrentReasoningSteps([]);
        } catch (error) {
            console.error("Chat error:", error);
            setMessages((prev) => [
                ...prev,
                {
                    id: Date.now().toString(),
                    role: "assistant",
                    content: "Sorry, I encountered an error. Please try again.",
                },
            ]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const handleLogout = () => {
        localStorage.removeItem("token");
        document.cookie = "token=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT";
        router.push("/");
    };

    const toggleFile = (fileId: number) => {
        setSelectedFileIds((prev) =>
            prev.includes(fileId) ? prev.filter((id) => id !== fileId) : [...prev, fileId]
        );
    };

    // Handle Quick Upload - immediately embed file to temp collection
    const handleQuickUpload = async (file: File) => {
        if (!token) return;

        const tempId = `temp_${Date.now()}`;
        setTempFiles(prev => [...prev, { id: tempId, name: file.name, status: 'uploading' }]);

        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('session_id', sessionId);

            const res = await fetch('http://localhost:8000/api/chat/temp-upload', {
                method: 'POST',
                headers: { Authorization: `Bearer ${token}` },
                body: formData,
            });

            if (res.ok) {
                const data = await res.json();
                setTempFiles(prev => prev.map(f =>
                    f.id === tempId ? { ...f, id: data.file_id, status: 'ready' } : f
                ));
            } else {
                setTempFiles(prev => prev.map(f =>
                    f.id === tempId ? { ...f, status: 'error' } : f
                ));
            }
        } catch {
            setTempFiles(prev => prev.map(f =>
                f.id === tempId ? { ...f, status: 'error' } : f
            ));
        }
    };

    // Drag and drop handlers
    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(true);
    };

    const handleDragLeave = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);
    };

    const handleDrop = async (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            // Upload first file (or loop for multiple)
            for (let i = 0; i < files.length; i++) {
                await handleQuickUpload(files[i]);
            }
        }
    };

    if (!user)
        return (
            <div className="flex items-center justify-center h-screen bg-[var(--hsbc-gray-100)]">
                <div className="text-center">
                    <img src="/hsbc_logo.png" alt="HSBC Logo" style={{ height: 40, width: "auto", margin: "0 auto" }} />
                    <p className="mt-4 text-[var(--muted)]">Loading...</p>
                </div>
            </div>
        );

    return (
        <div className="min-h-screen flex flex-col bg-[var(--background)]">
            {/* Header */}
            {/* Header */}
            <header className="hsbc-header">
                <div className="hsbc-logo">
                    <img src="/hsbc_logo.png" alt="HSBC Logo" style={{ height: 60, width: "auto" }} />
                </div>
                <div className="hsbc-header-red-bar">
                    <div className="hsbc-header-title">
                        BOI Knowledge Assistant
                    </div>
                    <div className="flex items-center gap-4 text-white">
                        {user.role === "admin" && (
                            <Link href="/admin" className="text-sm font-medium text-white/90 hover:text-white">
                                Admin
                            </Link>
                        )}
                        <div className="flex items-center gap-2 text-sm text-white/90">
                            <span className="w-2 h-2 rounded-full bg-green-400"></span>
                            {user.username}
                        </div>
                        <button onClick={handleLogout} className="text-sm font-medium text-white/90 hover:text-white">
                            Logout
                        </button>
                    </div>
                </div>
            </header>

            {/* Main 3-column layout */}
            <div className="app-layout">
                {/* Left Sidebar - Collapsible Menu */}
                <aside className="menu-sidebar">
                    <CollapsibleSection title="Custom Prompt" icon="✏️" defaultOpen>
                        <textarea
                            value={customPrompt}
                            onChange={(e) => setCustomPrompt(e.target.value)}
                            onBlur={handleCustomPromptBlur}
                            placeholder="Enter custom prompt for RAG system..."
                            className="prompt-textarea"
                            rows={4}
                        />
                        {customPrompt && (
                            <button className="clear-btn" onClick={() => { setCustomPrompt(""); localStorage.removeItem("customPrompt"); }}>
                                Clear
                            </button>
                        )}
                    </CollapsibleSection>

                    <CollapsibleSection title="Organizations" icon="🏢" defaultOpen>
                        <select
                            value={selectedOrgId}
                            onChange={(e) => {
                                setSelectedOrgId(e.target.value);
                                setSelectedFileIds([]);
                            }}
                            className="org-select"
                        >
                            <option value="all">All Organizations</option>
                            {allOrgs.map((org) => (
                                <option key={org.id} value={org.id.toString()}>
                                    {org.name}
                                </option>
                            ))}
                        </select>
                    </CollapsibleSection>

                    <CollapsibleSection title="File List" icon="📁" defaultOpen>
                        <div className="file-list-container">
                            {(!documents || documents.length === 0) ? (
                                <p className="text-sm text-[var(--muted)]">No files available</p>
                            ) : (
                                documents.map((doc) => (
                                    <label key={doc.id} className="file-checkbox">
                                        <input
                                            type="checkbox"
                                            checked={selectedFileIds.includes(doc.id)}
                                            onChange={() => toggleFile(doc.id)}
                                        />
                                        <span className="file-name" title={doc.name}>{doc.name}</span>
                                    </label>
                                ))
                            )}
                        </div>
                        {selectedFileIds.length > 0 && (
                            <div className="selected-count">
                                {selectedFileIds.length} file(s) selected
                            </div>
                        )}
                    </CollapsibleSection>

                    {/* Quick Upload Section */}
                    <CollapsibleSection title="Quick Upload" icon="📤" defaultOpen>
                        <div
                            className={`quick-upload-zone ${isDragging ? 'dragging' : ''}`}
                            onDragOver={handleDragOver}
                            onDragLeave={handleDragLeave}
                            onDrop={handleDrop}
                            onClick={() => tempFileInputRef.current?.click()}
                        >
                            <input
                                ref={tempFileInputRef}
                                type="file"
                                accept=".pdf,.md,.txt,.docx,.xlsx"
                                style={{ display: 'none' }}
                                onChange={(e) => {
                                    const file = e.target.files?.[0];
                                    if (file) handleQuickUpload(file);
                                    e.target.value = '';
                                }}
                            />
                            <div className="upload-icon">↑</div>
                            <p className="upload-text">Drop File Here</p>
                            <p className="upload-hint">- or -</p>
                            <p className="upload-link">Click to Upload</p>
                        </div>

                        {/* Uploaded temp files list */}
                        {tempFiles.length > 0 && (
                            <div className="quick-upload-files">
                                {tempFiles.map((file) => (
                                    <div key={file.id} className={`temp-file-chip ${file.status}`}>
                                        <span className="temp-file-icon">
                                            {file.status === 'uploading' ? '⏳' : file.status === 'ready' ? '✓' : '✗'}
                                        </span>
                                        <span className="temp-file-name">
                                            {file.name}
                                            {file.status === 'ready' && ' - uploaded successfully'}
                                            {file.status === 'error' && ' - upload failed'}
                                        </span>
                                        <button
                                            className="temp-file-remove"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                setTempFiles(prev => prev.filter(f => f.id !== file.id));
                                            }}
                                            title="Remove"
                                        >
                                            ×
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}
                    </CollapsibleSection>
                </aside>

                {/* Center - Chat Area */}
                <main className="chat-center">
                    <div className="chat-messages">
                        {messages.length === 0 && !currentAnswer && (
                            <div className="text-center mt-20 flex flex-col items-center">
                                <img src="/hsbc_logo.png" alt="HSBC Logo" style={{ height: 60, width: "auto", marginBottom: "1rem" }} />
                                <h2 className="text-2xl font-semibold mb-2 text-[var(--hsbc-red)]">BOI Knowledge Assistant</h2>
                                <p className="text-[var(--muted)] text-lg">Ask questions about your BOI design documents</p>
                            </div>
                        )}

                        {messages.map((msg) => (
                            <div key={msg.id} className={`message ${msg.role}`}>
                                <div className="message-header">
                                    <div className="message-avatar">{msg.role === "user" ? "U" : "AI"}</div>
                                    <span className="message-name">{msg.role === "user" ? user.username : "Assistant"}</span>
                                </div>
                                <div className="message-content">
                                    {msg.role === "assistant" ? (
                                        <MessageContent
                                            content={msg.content}
                                            sources={msg.sources}
                                            onSourceClick={setSelectedSource}
                                        />
                                    ) : (
                                        <div className="whitespace-pre-wrap">{msg.content}</div>
                                    )}

                                    {/* Reasoning Steps Toggle - Above sources */}
                                    {msg.reasoningSteps && msg.reasoningSteps.length > 0 && (
                                        <div className="reasoning-toggle">
                                            <button
                                                className="reasoning-link"
                                                onClick={() => setExpandedReasoning(expandedReasoning === msg.id ? null : msg.id)}
                                            >
                                                🧠 Reasoning Steps ({msg.reasoningSteps.length})
                                            </button>
                                            {expandedReasoning === msg.id && (
                                                <div className="reasoning-content">
                                                    {msg.reasoningSteps.map((step, i) => (
                                                        <CollapsibleReasoningStep key={i} step={step} index={i} />
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    {/* Source Citations with relevance score */}
                                    {msg.sources && msg.sources.length > 0 && (
                                        <div className="source-citations">
                                            {msg.sources.map((source, i) => (
                                                <button
                                                    key={i}
                                                    className={`source-link ${selectedSource === source ? "active" : ""}`}
                                                    onClick={() => setSelectedSource(source)}
                                                    title={`Relevance: ${((source as any).score * 100).toFixed(1)}%`}
                                                >
                                                    [Source {i + 1}] <span className="score">{((source as any).score * 100).toFixed(0)}%</span>
                                                </button>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}

                        {/* Streaming answer */}
                        {currentAnswer && (
                            <div className="message assistant">
                                <div className="message-header">
                                    <div className="message-avatar">AI</div>
                                    <span className="message-name">Assistant</span>
                                </div>
                                <div className="message-content">
                                    <MessageContent
                                        content={currentAnswer}
                                        sources={currentSources}
                                        onSourceClick={setSelectedSource}
                                    />
                                </div>
                            </div>
                        )}

                        {/* Current Reasoning Steps while loading */}
                        {isLoading && currentReasoningSteps.length > 0 && (
                            <div className="current-reasoning">
                                {currentReasoningSteps.map((step, i) => {
                                    // Detect if this step is currently streaming (last 💬 step during loading)
                                    const isLastLlmStep = step.startsWith("💬") &&
                                        i === currentReasoningSteps.findLastIndex(s => s.startsWith("💬"));
                                    return (
                                        <CollapsibleReasoningStep
                                            key={i}
                                            step={step}
                                            index={i}
                                            isStreaming={isLoading && isLastLlmStep}
                                        />
                                    );
                                })}
                            </div>
                        )}

                        {isLoading && currentReasoningSteps.length === 0 && !currentAnswer && (
                            <div className="message assistant">
                                <div className="message-header">
                                    <div className="message-avatar">AI</div>
                                    <span className="message-name">Assistant</span>
                                </div>
                                <div className="message-content animate-pulse">Thinking...</div>
                            </div>
                        )}

                        <div ref={messagesEndRef} />
                    </div>

                    {/* Input Area */}
                    <div className="chat-input-area">
                        <div className="chat-input-wrapper">
                            <textarea
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyDown={handleKeyDown}
                                placeholder="Ask about BOI documents... (paste URLs for instant context)"
                                disabled={isLoading}
                                className="chat-input"
                                rows={2}
                            />
                            <button onClick={handleSend} disabled={isLoading || !input.trim()} className="send-btn">
                                {isLoading ? "..." : "Send"}
                            </button>
                        </div>
                    </div>
                </main>

                {/* Right Panel - Graph + Source Details */}
                <aside className="source-panel">
                    {/* Knowledge Graph Section */}
                    <CollapsibleSection title="Knowledge Graph" icon="📊" defaultOpen>
                        <GraphVisualization
                            data={graphData}
                            onFullscreen={() => setShowGraphFullscreen(true)}
                        />
                    </CollapsibleSection>

                    {/* Source Details Section */}
                    <div className="panel-section">
                        <div className="panel-header">
                            <h3>📄 Source Details</h3>
                        </div>
                        <div className="panel-content">
                            {selectedSource ? (
                                <div className="source-detail">
                                    <div className="source-meta">
                                        <strong>Source:</strong> {selectedSource.metadata?.source || "Unknown"}
                                    </div>
                                    <div className="source-text">
                                        <div className="source-markdown">
                                            <ReactMarkdown>{selectedSource.content}</ReactMarkdown>
                                        </div>
                                    </div>
                                </div>
                            ) : (
                                <div className="empty-panel">
                                    <p>Click a [Source] link to view content</p>
                                </div>
                            )}
                        </div>
                    </div>
                </aside>

                {/* Fullscreen Graph Modal */}
                {showGraphFullscreen && (
                    <GraphFullscreenModal
                        data={graphData}
                        onClose={() => setShowGraphFullscreen(false)}
                    />
                )}
            </div>
        </div>
    );
}
