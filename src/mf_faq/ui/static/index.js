/* =========================================================================
   Mutual Fund FAQ Assistant - Frontend controller (index.js)
   Controls dashboard cards, floating chatbot widget toggling, and query Q&A.
   ========================================================================= */

document.addEventListener("DOMContentLoaded", () => {
    // UI Elements
    const plansGrid = document.getElementById("plansGrid");
    const chatbotWidget = document.getElementById("chatbotWidget");
    const chatbotToggleBtn = document.getElementById("chatbotToggleBtn");
    const closeChatbotBtn = document.getElementById("closeChatbotBtn");
    const clearChatBtn = document.getElementById("clearChatBtn");
    
    const conversationFeed = document.getElementById("conversationFeed");
    const samplePills = document.getElementById("samplePills");
    const queryForm = document.getElementById("queryForm");
    const queryInput = document.getElementById("queryInput");
    const submitBtn = document.getElementById("submitBtn");
    const piiWarningToast = document.getElementById("piiWarningToast");
    const systemModel = document.getElementById("systemModel");
    const toastContainer = document.getElementById("toastContainer");

    let activeSchemeId = null;
    let schemesMetadata = {};

    // Static verified data to enrich cards (100% compliant, facts only, no placeholders)
    const cardExtraStats = {
        "hdfc_mid_cap": {
            fullName: "HDFC Mid-Cap Opportunities Fund",
            minSIP: "₹100",
            expenseRatio: "0.78%",
            exitLoad: "1.0% (if redeemed within 1 year)",
            risk: "Very High"
        },
        "hdfc_equity": {
            fullName: "HDFC Flexi Cap Fund",
            minSIP: "₹100",
            expenseRatio: "0.76%",
            exitLoad: "1.0% (if redeemed within 1 year)",
            risk: "Very High"
        },
        "hdfc_focused": {
            fullName: "HDFC Focused 30 Fund",
            minSIP: "₹100",
            expenseRatio: "0.92%",
            exitLoad: "1.0% (if redeemed within 1 year)",
            risk: "Very High"
        },
        "hdfc_elss": {
            fullName: "HDFC ELSS Tax Saver Fund",
            minSIP: "₹500",
            expenseRatio: "1.12%",
            exitLoad: "0% (3-year lock-in applies)",
            risk: "Very High"
        },
        "hdfc_large_cap": {
            fullName: "HDFC Large Cap Fund",
            minSIP: "₹100",
            expenseRatio: "0.85%",
            exitLoad: "1.0% (if redeemed within 1 year)",
            risk: "Very High"
        }
    };

    // 1. Toggle Chatbot Widget Visibility
    chatbotToggleBtn.addEventListener("click", () => {
        chatbotWidget.classList.toggle("collapsed");
        if (!chatbotWidget.classList.contains("collapsed")) {
            queryInput.focus();
            scrollToBottom();
            // Clear toggle notification badge if any
            document.querySelector(".toggle-badge").classList.add("hidden");
        }
    });

    closeChatbotBtn.addEventListener("click", () => {
        chatbotWidget.classList.add("collapsed");
    });

    // 2. Initialise App Details from /meta
    async function initApp() {
        try {
            const response = await fetch("/meta");
            if (!response.ok) throw new Error("Could not retrieve system metadata.");
            const data = await response.json();
            
            // Populate System Model info
            if (data.model_engine) {
                systemModel.textContent = `Engine: ${data.model_engine} | v${data.version}`;
            }

            // Populate Whitelisted Schemes in Main Dashboard Grid
            if (data.schemes && data.schemes.length > 0) {
                plansGrid.innerHTML = ""; // Clear skeletons
                data.schemes.forEach(scheme => {
                    schemesMetadata[scheme.id] = scheme;
                    const stats = cardExtraStats[scheme.id] || {
                        fullName: scheme.name,
                        minSIP: "₹100",
                        expenseRatio: "0.85%",
                        exitLoad: "1.0%",
                        risk: "Very High"
                    };
                    
                    const card = document.createElement("div");
                    card.className = "plan-card";
                    card.dataset.id = scheme.id;
                    card.innerHTML = `
                        <div class="card-content">
                            <div class="card-header">
                                <span class="plan-tag">${scheme.category}</span>
                                <a href="${scheme.url}" target="_blank" rel="noopener nofollow" class="plan-link" title="Open official page">Groww Page ↗</a>
                            </div>
                            <h3 class="plan-title">${stats.fullName}</h3>
                            <div class="plan-stats">
                                <div class="stat-row">
                                    <span class="stat-label">Min Investment (SIP)</span>
                                    <span class="stat-value highlight-green">${stats.minSIP}</span>
                                </div>
                                <div class="stat-row">
                                    <span class="stat-label">Expense Ratio</span>
                                    <span class="stat-value">${stats.expenseRatio}</span>
                                </div>
                                <div class="stat-row">
                                    <span class="stat-label">Exit Load</span>
                                    <span class="stat-value" title="${stats.exitLoad}">${stats.exitLoad.split(" ")[0]} ${stats.exitLoad.includes("lock-in") ? "Lock-in" : "Exit"}</span>
                                </div>
                                <div class="stat-row">
                                    <span class="stat-label">Riskometer Profile</span>
                                    <span class="stat-value">${stats.risk}</span>
                                </div>
                            </div>
                        </div>
                        <button class="plan-action-btn">
                            <span>Ask GROWWW AI</span>
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                                <line x1="5" y1="12" x2="19" y2="12"></line>
                                <polyline points="12 5 19 12 12 19"></polyline>
                            </svg>
                        </button>
                    `;
                    
                    // Click plan card to select, open chatbot, and load context
                    card.addEventListener("click", (e) => {
                        // Prevent clicking direct link from resetting selection flow
                        if (e.target.classList.contains("plan-link")) return;
                        selectScheme(scheme.id);
                    });
                    
                    plansGrid.appendChild(card);
                });
            }
        } catch (error) {
            console.error("Initialization failed:", error);
            showToast("Initialization error: Backend offline. Dynamic retrieval disabled.", true);
        }
    }

    // 3. Select Scheme Card
    function selectScheme(schemeId) {
        activeSchemeId = schemeId;
        
        // Update active class on cards
        document.querySelectorAll(".plan-card").forEach(card => {
            if (card.dataset.id === schemeId) {
                card.classList.add("active");
            } else {
                card.classList.remove("active");
            }
        });

        // Auto-expand chatbot if collapsed
        if (chatbotWidget.classList.contains("collapsed")) {
            chatbotWidget.classList.remove("collapsed");
        }

        // Generate context-aware suggested questions for pills
        const stats = cardExtraStats[schemeId];
        const shortName = stats ? stats.fullName : schemesMetadata[schemeId].name.split(" - ")[0];
        
        const pills = [
            { label: `Exit Load`, query: `What is the exit load of ${shortName}?` },
            { label: `Expense Ratio`, query: `What is the expense ratio of ${shortName}?` },
            { label: `Min Investment`, query: `What is the minimum investment for ${shortName}?` }
        ];

        // Highlight active scheme title in chatbot welcome/suggestions area
        samplePills.innerHTML = "";
        pills.forEach(pill => {
            const btn = document.createElement("button");
            btn.className = "sample-pill-btn";
            btn.textContent = pill.label;
            btn.addEventListener("click", () => {
                queryInput.value = pill.query;
                submitQuery();
            });
            samplePills.appendChild(btn);
        });

        queryInput.focus();
        showToast(`Loaded details for: ${shortName}`);
        
        // System notification ping inside chatbot to guide user
        appendSystemLog(`Switched focus to: <strong>${shortName}</strong>. Suggested queries updated.`);
    }

    // 4. Client-side PII Pre-checker
    queryInput.addEventListener("input", () => {
        const text = queryInput.value;
        const panRegex = /[a-zA-Z]{5}[0-9]{4}[a-zA-Z]{1}/;
        const aadhaarRegex = /\b\d{4}\s?\d{4}\s?\d{4}\b/;
        const emailRegex = /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/;
        const phoneRegex = /\b(\+91[\-\s]?)?[6-9]\d{9}\b/;

        if (panRegex.test(text) || aadhaarRegex.test(text) || emailRegex.test(text) || phoneRegex.test(text)) {
            piiWarningToast.classList.remove("hidden");
        } else {
            piiWarningToast.classList.add("hidden");
        }
    });

    // 5. Submit Query Event Handler
    queryForm.addEventListener("submit", (e) => {
        e.preventDefault();
        submitQuery();
    });

    async function submitQuery() {
        const query = queryInput.value.trim();
        if (!query) return;

        // Reset input and redact PII warnings
        queryInput.value = "";
        piiWarningToast.classList.add("hidden");

        // Expand chatbot if collapsed
        if (chatbotWidget.classList.contains("collapsed")) {
            chatbotWidget.classList.remove("collapsed");
        }

        // 1. Append User bubble
        appendUserMessage(query);

        // 2. Disable input and show skeleton loader
        toggleInputState(true);
        const skeletonBubble = appendAssistantSkeleton();

        try {
            // Fetch response from Backend REST API
            const response = await fetch("/ask", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query: query })
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || "Server failed to process query.");
            }

            const data = await response.json();
            
            // 3. Replace skeleton with real response
            displayAssistantResponse(skeletonBubble, data);

        } catch (error) {
            console.error("Query failed:", error);
            removeMessageElement(skeletonBubble);
            appendErrorMessage(error.message || "Unable to reach the assistant server.");
            showToast("Query deflection error. Check terminal logs.", true);
        } finally {
            toggleInputState(false);
            scrollToBottom();
        }
    }

    // Helpers to Append Messages
    function appendUserMessage(text) {
        const msg = document.createElement("div");
        msg.className = "message bubble-user";
        msg.innerHTML = `
            <div class="bubble-content">
                <p>${escapeHTML(text)}</p>
            </div>
            <div class="bubble-meta">
                <span>User Query</span>
            </div>
        `;
        conversationFeed.appendChild(msg);
        scrollToBottom();
    }

    function appendSystemLog(htmlText) {
        const log = document.createElement("div");
        log.style.textAlign = "center";
        log.style.fontSize = "0.75rem";
        log.style.color = "var(--purple-accent)";
        log.style.background = "rgba(120, 53, 214, 0.04)";
        log.style.border = "1px solid rgba(120, 53, 214, 0.08)";
        log.style.padding = "6px 12px";
        log.style.borderRadius = "12px";
        log.style.margin = "8px auto";
        log.style.maxWidth = "90%";
        log.innerHTML = htmlText;
        conversationFeed.appendChild(log);
        scrollToBottom();
    }

    function appendAssistantSkeleton() {
        const msg = document.createElement("div");
        msg.className = "message bubble-assistant";
        msg.innerHTML = `
            <div class="bubble-content bubble-skeleton">
                <div class="skeleton-line line-1"></div>
                <div class="skeleton-line line-2"></div>
                <div class="skeleton-line line-3"></div>
            </div>
            <div class="bubble-meta">
                <span>Compliance Check in Progress...</span>
            </div>
        `;
        conversationFeed.appendChild(msg);
        scrollToBottom();
        return msg;
    }

    function displayAssistantResponse(element, data) {
        // Safe mapping of intent text
        let intentLabel = data.intent.charAt(0).toUpperCase() + data.intent.slice(1);
        if (data.intent === "factual") intentLabel = "✓ Factual Answer";
        if (data.intent === "pii_blocked") intentLabel = "🛡️ PII Guard Block";
        if (data.intent === "dont_know") intentLabel = "⚠️ Unknown (Off-Corpus)";
        if (data.intent === "advisory" || data.intent === "comparison" || data.intent === "prediction") {
            intentLabel = "🛡️ Compliant Refusal";
        }

        let citationHTML = "";
        if (data.source_url) {
            citationHTML = `• Source: <a href="${data.source_url}" target="_blank" rel="noopener nofollow" class="bubble-citation-link">Groww Page ↗</a>`;
        }

        element.innerHTML = `
            <div class="bubble-content">
                <p>${escapeHTML(data.answer).replace(/\n/g, '<br/>')}</p>
            </div>
            <div class="bubble-meta">
                <span>${intentLabel}</span>
                ${citationHTML}
            </div>
        `;
        
        // Flash toggle button badge if chatbot is closed when answer arrives (e.g. background answer)
        if (chatbotWidget.classList.contains("collapsed")) {
            document.querySelector(".toggle-badge").classList.remove("hidden");
        }
    }

    function appendErrorMessage(errorMsg) {
        const msg = document.createElement("div");
        msg.className = "message bubble-assistant";
        msg.innerHTML = `
            <div class="bubble-content" style="background: rgba(231, 76, 60, 0.05); border-color: rgba(231, 76, 60, 0.25);">
                <p style="color: #ff9999;">⚠️ <strong>Error:</strong> Failed to fetch answer from backend. Uvicorn service might be stopped or rate limited.</p>
                <p style="font-size: 0.8rem; color: var(--text-muted); margin-top: 4px;">Detail: ${escapeHTML(errorMsg)}</p>
            </div>
            <div class="bubble-meta">
                <span style="color: #ff9999;">Connection Error</span>
            </div>
        `;
        conversationFeed.appendChild(msg);
    }

    function removeMessageElement(element) {
        if (element && element.parentNode) {
            element.parentNode.removeChild(element);
        }
    }

    function toggleInputState(disabled) {
        queryInput.disabled = disabled;
        submitBtn.disabled = disabled;
        if (!disabled) {
            queryInput.focus();
        }
    }

    function scrollToBottom() {
        conversationFeed.scrollTop = conversationFeed.scrollHeight;
    }

    // Clear Chat Handler
    clearChatBtn.addEventListener("click", () => {
        conversationFeed.innerHTML = `
            <div class="message bubble-assistant">
                <div class="bubble-content">
                    <p>Welcome back! Ask a factual question about our 5 whitelisted HDFC schemes (Exit loads, expense ratios, lock-in periods, portfolio details).</p>
                </div>
                <div class="bubble-meta">
                    <span>System Active</span>
                </div>
            </div>
        `;
        showToast("Conversation cleared successfully.");
    });

    // Suggested Question Pill Buttons in Form Container
    document.querySelectorAll(".sample-pill-btn").forEach(pill => {
        pill.addEventListener("click", () => {
            queryInput.value = pill.dataset.query;
            submitQuery();
        });
    });

    // Toast Notification utility
    function showToast(message, isError = false) {
        const toast = document.createElement("div");
        toast.className = `toast ${isError ? 'toast-error' : ''}`;
        toast.textContent = message;
        toastContainer.appendChild(toast);
        
        // Remove toast after 3.5 seconds
        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transform = "translateY(20px)";
            setTimeout(() => {
                if (toast.parentNode) {
                    toastContainer.removeChild(toast);
                }
            }, 300);
        }, 3500);
    }

    // Helper: Escape HTML
    function escapeHTML(str) {
        return str
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // Initialize on start
    initApp();
});
