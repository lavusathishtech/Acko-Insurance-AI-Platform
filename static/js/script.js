/* static/js/script.js */
document.addEventListener("DOMContentLoaded", () => {
    // Initial State Check
    const token = localStorage.getItem("acko_token");
    const userRole = localStorage.getItem("acko_role");

    // Form Handling
    setupForms();

    // Setup navigation highlighting
    setupNavigation();

    // Check specific pages & load metrics
    if (document.getElementById("policies-container")) {
        loadCustomerDashboard();
    }
    if (document.getElementById("admin-kpis")) {
        loadAdminDashboard();
    }
});

// Helper for API Headers
function getHeaders(isMultipart = false) {
    const token = localStorage.getItem("acko_token");
    const headers = {};
    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }
    if (!isMultipart) {
        // Content-Type for URL Encoded / JSON is handled per request
    }
    return headers;
}

// Navigation Helper
function setupNavigation() {
    const navLinks = document.querySelectorAll(".nav-link");
    const currentPath = window.location.pathname;
    navLinks.forEach(link => {
        if (link.getAttribute("href") === currentPath) {
            link.classList.add("active");
        }
    });
}

function logout() {
    localStorage.removeItem("acko_token");
    localStorage.removeItem("acko_role");
    localStorage.removeItem("acko_user");
    window.location.href = "/login";
}

// Form Handlers
function setupForms() {
    // Customer Login/Register Toggle
    const toggleAuthBtn = document.getElementById("toggle-auth-mode");
    if (toggleAuthBtn) {
        toggleAuthBtn.addEventListener("click", (e) => {
            e.preventDefault();
            const regSection = document.getElementById("register-section");
            const loginSection = document.getElementById("login-section");
            const isLogin = regSection.style.display === "none";
            
            if (isLogin) {
                regSection.style.display = "block";
                loginSection.style.display = "none";
                toggleAuthBtn.textContent = "Already have an account? Login here";
            } else {
                regSection.style.display = "none";
                loginSection.style.display = "block";
                toggleAuthBtn.textContent = "Don't have an account? Register here";
            }
        });
    }

    // Customer Login Submission
    const loginForm = document.getElementById("customer-login-form");
    if (loginForm) {
        loginForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const formData = new FormData(loginForm);
            showSpinner(true);
            try {
                const response = await fetch("/api/auth/login", {
                    method: "POST",
                    body: formData
                });
                if (!response.ok) throw new Error(await response.text());
                const data = await response.json();
                localStorage.setItem("acko_token", data.access_token);
                localStorage.setItem("acko_role", "customer");
                localStorage.setItem("acko_user", JSON.stringify(data.user));
                window.location.href = "/dashboard";
            } catch (err) {
                alert("Login failed. Check your credentials.");
                console.error(err);
            } finally {
                showSpinner(false);
            }
        });
    }

    // Customer Register Submission
    const registerForm = document.getElementById("customer-register-form");
    if (registerForm) {
        registerForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const formData = new FormData(registerForm);
            showSpinner(true);
            try {
                const response = await fetch("/api/auth/register", {
                    method: "POST",
                    body: formData
                });
                if (!response.ok) throw new Error(await response.text());
                const data = await response.json();
                localStorage.setItem("acko_token", data.access_token);
                localStorage.setItem("acko_role", "customer");
                localStorage.setItem("acko_user", JSON.stringify(data.user));
                window.location.href = "/dashboard";
            } catch (err) {
                alert("Registration failed. Email might already exist.");
                console.error(err);
            } finally {
                showSpinner(false);
            }
        });
    }

    // Admin Login Submission
    const adminLoginForm = document.getElementById("admin-login-form");
    if (adminLoginForm) {
        adminLoginForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const formData = new FormData(adminLoginForm);
            showSpinner(true);
            try {
                const response = await fetch("/api/auth/admin/login", {
                    method: "POST",
                    body: formData
                });
                if (!response.ok) throw new Error(await response.text());
                const data = await response.json();
                localStorage.setItem("acko_token", data.access_token);
                localStorage.setItem("acko_role", data.user.role);
                localStorage.setItem("acko_user", JSON.stringify(data.user));
                window.location.href = "/admin-dashboard";
            } catch (err) {
                alert("Admin login failed. Try email 'admin@acko.demo' and password 'admin123'.");
                console.error(err);
            } finally {
                showSpinner(false);
            }
        });
    }

    // Premium Predictor Form
    const quoteForm = document.getElementById("premium-quote-form");
    if (quoteForm) {
        quoteForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const formData = new FormData(quoteForm);
            showSpinner(true);
            try {
                const response = await fetch("/api/premium/predict", {
                    method: "POST",
                    headers: getHeaders(),
                    body: formData
                });
                if (!response.ok) throw new Error(await response.text());
                const data = await response.json();
                
                // Render Result Card
                document.getElementById("quote-result-card").style.display = "block";
                document.getElementById("premium-value").innerHTML = `₹${data.final_premium.toLocaleString()}`;
                
                // Display breakdowns
                const details = `
                    <div class="d-flex justify-content-between mb-2"><span>Vehicle:</span><strong>${data.vehicle_model} (${data.registration_year})</strong></div>
                    <div class="d-flex justify-content-between mb-2"><span>Own Damage Base:</span><strong>₹${data.own_damage}</strong></div>
                    <div class="d-flex justify-content-between mb-2"><span>Third Party Cover:</span><strong>₹${data.third_party}</strong></div>
                    <div class="d-flex justify-content-between mb-2"><span>NCB Discount:</span><strong class="text-success">-₹${data.ncb_discount}</strong></div>
                    <div class="d-flex justify-content-between mb-2"><span>GST (18%):</span><strong>₹${data.gst}</strong></div>
                    <hr>
                    <div class="d-flex justify-content-between text-primary font-weight-bold"><span>Risk Score:</span><strong>${data.risk_score}/100</strong></div>
                `;
                document.getElementById("premium-breakdown").innerHTML = details;
            } catch (err) {
                alert("Quotation computation failed. Please authenticate.");
                window.location.href = "/login";
            } finally {
                showSpinner(false);
            }
        });
    }

    // AI Policy Chatbot
    const chatForm = document.getElementById("chatbot-input-form");
    if (chatForm) {
        chatForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const inputField = document.getElementById("chatbot-message-input");
            const message = inputField.value.trim();
            if (!message) return;

            appendChatMessage("user", message);
            inputField.value = "";

            try {
                const formData = new FormData();
                formData.append("message", message);
                const response = await fetch("/api/chatbot/message", {
                    method: "POST",
                    headers: getHeaders(),
                    body: formData
                });
                if (!response.ok) throw new Error();
                const data = await response.json();
                appendChatMessage("bot", data.reply);
            } catch (err) {
                appendChatMessage("bot", "I am currently unable to query the database. Please try again later.");
            }
        });
    }

    // Claims Submission Form
    const claimForm = document.getElementById("claim-submission-form");
    if (claimForm) {
        claimForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const formData = new FormData(claimForm);
            showSpinner(true);
            try {
                const response = await fetch("/api/claims/submit", {
                    method: "POST",
                    headers: getHeaders(true),
                    body: formData
                });
                if (!response.ok) throw new Error();
                const data = await response.json();
                
                // Update claim response UI
                document.getElementById("claim-result-box").style.display = "block";
                document.getElementById("claim-severity").innerText = data.damage_severity;
                document.getElementById("claim-parts").innerText = data.affected_parts;
                document.getElementById("claim-payout").innerText = `₹${data.estimated_payout.toLocaleString()}`;
                document.getElementById("claim-prob").innerText = `${Math.round(data.approval_probability * 100)}%`;
                
                // Color indicator based on severity
                const indicator = document.getElementById("claim-severity");
                indicator.className = "badge";
                if (data.damage_severity === "Severe") indicator.classList.add("bg-danger");
                else if (data.damage_severity === "Moderate") indicator.classList.add("bg-warning");
                else indicator.classList.add("bg-success");

            } catch (err) {
                alert("Claims analysis failed. Please authenticate.");
                window.location.href = "/login";
            } finally {
                showSpinner(false);
            }
        });
    }

    // Manager SQL AI Assistant Form
    const managerAssistForm = document.getElementById("manager-assistant-form");
    if (managerAssistForm) {
        managerAssistForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const inputVal = document.getElementById("manager-question-input").value;
            showSpinner(true);
            try {
                const formData = new FormData();
                formData.append("question", inputVal);
                const response = await fetch("/api/admin/assistant", {
                    method: "POST",
                    headers: getHeaders(),
                    body: formData
                });
                if (!response.ok) throw new Error();
                const data = await response.json();
                
                document.getElementById("assistant-response-card").style.display = "block";
                document.getElementById("assistant-sql").innerText = data.sql;
                document.getElementById("assistant-explanation").innerText = data.explanation;
                document.getElementById("assistant-result").innerText = JSON.stringify(data.result, null, 2);
            } catch (err) {
                alert("AI SQL generation failed.");
            } finally {
                showSpinner(false);
            }
        });
    }
}

// Render Policy/Claims lists in dashboard
async function loadCustomerDashboard() {
    try {
        const res = await fetch("/api/customer/overview", {
            headers: getHeaders()
        });
        if (!res.ok) throw new Error();
        const data = await res.json();
        
        // Populate policies
        const policiesDiv = document.getElementById("policies-container");
        if (data.policies.length === 0) {
            policiesDiv.innerHTML = `<div class="alert alert-info">No active policies found. Generate a quote to get started!</div>`;
        } else {
            policiesDiv.innerHTML = data.policies.map(p => `
                <div class="card mb-3 shadow-sm border-0">
                    <div class="card-body d-flex justify-content-between align-items-center">
                        <div>
                            <h5 class="mb-1 text-primary">${p.vehicle_model} (${p.vehicle_type})</h5>
                            <small class="text-muted">City: ${p.city} | IDV: ₹${p.idv.toLocaleString()}</small>
                        </div>
                        <div class="text-right">
                            <span class="badge bg-success mb-2">Active</span>
                            <div class="font-weight-bold">Premium: ₹${p.final_premium.toLocaleString()}</div>
                        </div>
                    </div>
                </div>
            `).join("");
        }

        // Populate Claims
        const claimsDiv = document.getElementById("claims-container");
        if (data.claims.length === 0) {
            claimsDiv.innerHTML = `<div class="text-muted text-center py-3">No claims submitted.</div>`;
        } else {
            claimsDiv.innerHTML = data.claims.map(c => `
                <div class="card mb-3 shadow-sm border-0">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <h6 class="text-dark mb-0">${c.vehicle_model} - ${c.incident_date}</h6>
                            <span class="badge ${c.status === 'approved' ? 'bg-success' : 'bg-warning'}">${c.status}</span>
                        </div>
                        <p class="small text-muted mb-2">${c.description}</p>
                        <div class="d-flex justify-content-between">
                            <small>Severity: <strong>${c.damage_severity}</strong></small>
                            <small class="text-primary font-weight-bold">Est. Payout: ₹${c.estimated_payout.toLocaleString()}</small>
                        </div>
                    </div>
                </div>
            `).join("");
        }

    } catch (err) {
        logout();
    }
}

// Render Admin Dashboard and Charts
async function loadAdminDashboard() {
    try {
        const res = await fetch("/api/admin/dashboard", {
            headers: getHeaders()
        });
        if (!res.ok) throw new Error();
        const data = await res.json();

        // Load KPIs
        document.getElementById("kpi-claims").innerText = data.kpis.claims_today;
        document.getElementById("kpi-rate").innerText = data.kpis.approval_rate;
        document.getElementById("kpi-payout").innerText = data.kpis.avg_claim;
        document.getElementById("kpi-premium").innerText = data.kpis.avg_premium;

        // Render Claims table
        const tbl = document.getElementById("admin-claims-table");
        if (data.claims.length === 0) {
            tbl.innerHTML = `<tr><td colspan="6" class="text-center">No claim records.</td></tr>`;
        } else {
            tbl.innerHTML = data.claims.map(c => `
                <tr>
                    <td>#CLM-${c.id}</td>
                    <td>${c.vehicle_model}</td>
                    <td>${c.damage_severity}</td>
                    <td>₹${c.estimated_payout.toLocaleString()}</td>
                    <td><span class="badge ${c.fraud_risk === 'high' ? 'bg-danger' : 'bg-success'}">${c.fraud_risk}</span></td>
                    <td><span class="badge ${c.status === 'approved' ? 'bg-success' : 'bg-warning'}">${c.status}</span></td>
                </tr>
            `).join("");
        }

        // Initialize Chart.js
        renderCharts(data.claims, data.quotations);

    } catch (err) {
        localStorage.removeItem("acko_token");
        window.location.href = "/admin-login";
    }
}

// Chart.js helper
function renderCharts(claims, quotations) {
    const claimsCtx = document.getElementById("admin-claims-chart");
    const revenueCtx = document.getElementById("admin-revenue-chart");
    if (!claimsCtx || !revenueCtx) return;

    // Count severities
    const severeCount = claims.filter(c => c.damage_severity === "Severe").length || 10;
    const modCount = claims.filter(c => c.damage_severity === "Moderate").length || 24;
    const lowCount = claims.filter(c => c.damage_severity === "Low").length || 38;

    new Chart(claimsCtx, {
        type: "doughnut",
        data: {
            labels: ["Severe", "Moderate", "Low"],
            datasets: [{
                data: [severeCount, modCount, lowCount],
                backgroundColor: ["#ef4444", "#f59e0b", "#10b981"]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: "#ffffff" } }
            }
        }
    });

    // Premium Trends (Quotations timeline)
    const quoteLabels = quotations.slice(0, 7).map(q => q.vehicle_model) || ["Amaze", "Classic", "Nexon", "i20"];
    const quoteVals = quotations.slice(0, 7).map(q => q.final_premium) || [12840, 2140, 18900, 9500];

    new Chart(revenueCtx, {
        type: "bar",
        data: {
            labels: quoteLabels,
            datasets: [{
                label: "Quoted Premium (INR)",
                data: quoteVals,
                backgroundColor: "#2684ff"
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: "#ffffff" } }
            },
            scales: {
                x: { ticks: { color: "#ffffff" } },
                y: { ticks: { color: "#ffffff" } }
            }
        }
    });

    // 4D Bubble Chart (Amount, Probability, Severity, Color)
    const fourCtx = document.getElementById("admin-4d-chart");
    if (fourCtx) {
        const bubblePoints = claims.map(c => {
            const amount = c.estimated_payout ?? c.amount ?? c.claim_amount ?? 0;
            let prob = c.probability ?? c.approval_probability ?? c.approval_prob ?? 0;
            // Normalize probability to 0..1 if it's given as percentage
            if (prob > 1) prob = prob / 100;

            const severityRaw = c.damage_severity ?? c.severity ?? c.severity_score ?? 0;
            let sevScore = 5;
            if (typeof severityRaw === 'number') sevScore = severityRaw;
            else if (typeof severityRaw === 'string') {
                if (severityRaw.toLowerCase().includes('severe') || severityRaw.toLowerCase().includes('high')) sevScore = 12;
                else if (severityRaw.toLowerCase().includes('moderate') || severityRaw.toLowerCase().includes('med')) sevScore = 8;
                else sevScore = 4;
            }
            const r = Math.min(24, Math.max(4, Math.round(sevScore)));

            let color = '#10b981';
            if ((c.fraud_risk && c.fraud_risk.toLowerCase() === 'high') || (c.fraud_score && c.fraud_score > 0.7)) color = '#ef4444';
            else if (c.status && (c.status === 'approved' || c.status === 'Approved')) color = '#2684ff';

            return { x: amount, y: prob, r: r, backgroundColor: color, id: c.id, vehicle: c.vehicle_model || c.vehicle };
        }).filter(p => Number.isFinite(p.x) && Number.isFinite(p.y));

        new Chart(fourCtx, {
            type: 'bubble',
            data: {
                datasets: [{
                    label: 'Claims 4D',
                    data: bubblePoints,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { labels: { color: '#ffffff' } },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const d = context.raw || {};
                                const probDisplay = d.y <= 1 ? Math.round(d.y * 100) + '%' : String(d.y);
                                return [`ID: ${d.id || 'N/A'}`, `Vehicle: ${d.vehicle || 'N/A'}`, `Payout: ₹${d.x}`, `Approval: ${probDisplay}`, `Size(severity): ${d.r}`];
                            }
                        }
                    }
                },
                scales: {
                    x: { title: { display: true, text: 'Estimated Payout (INR)', color: '#ffffff' }, ticks: { color: '#ffffff' } },
                    y: { title: { display: true, text: 'Approval Probability', color: '#ffffff' }, ticks: { color: '#ffffff', callback: function(val){ return val >= 1 ? val : (val*100).toFixed(0) + '%'; } } }
                }
            }
        });
    }
}

// Chat UI Bubbles helper
function appendChatMessage(sender, text) {
    const chatWrap = document.getElementById("chatbot-messages-wrap");
    if (!chatWrap) return;
    const bubble = document.createElement("div");
    bubble.className = `chat-message-bubble ${sender}`;
    bubble.innerHTML = `<p class="mb-0">${text.replace(/\n/g, "<br>")}</p>`;
    chatWrap.appendChild(bubble);
    chatWrap.scrollTop = chatWrap.scrollHeight;
}

// Spinner Helper
function showSpinner(show) {
    const sp = document.getElementById("loading-spinner-overlay");
    if (sp) {
        sp.style.display = show ? "flex" : "none";
    }
}

// Report Download Handler
function downloadReport() {
    const reportType = document.getElementById("report-type-select")?.value || "escalation";
    const reportFormat = document.getElementById("report-format-select")?.value || "csv";
    const dateRange = document.getElementById("report-date-select")?.value || "all";

    showSpinner(true);
    try {
        let url = "/api/admin/report?type=" + reportType + "&format=" + reportFormat + "&range=" + dateRange;
        const link = document.createElement("a");
        link.href = url;
        link.download = `admin_report_${new Date().toISOString().split('T')[0]}.${reportFormat}`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    } catch (err) {
        alert("Report download failed: " + err.message);
    } finally {
        showSpinner(false);
    }
}
