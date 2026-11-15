/**
 * CampusQueri Main Vanilla JavaScript
 * TYBCA Project Foundation Client Scripts
 * Phase 11: UI Polish, Accessibility & Interactive States
 */

document.addEventListener("DOMContentLoaded", () => {
    initHealthCheck();
    initFormLoading();
    initAlertDismissal();
    initKeyboardShortcuts();
});

/**
 * Checks system health via /api/health and updates the UI badge.
 * Gracefully handles healthy, degraded (SQLite fallback in local dev), and network states.
 */
function initHealthCheck() {
    const badge = document.getElementById("healthBadge");
    const btn = document.getElementById("btnHealthCheck");

    const performCheck = async () => {
        if (!badge) return;
        badge.innerHTML = `
            <div class="d-flex align-items-center justify-content-center gap-2">
                <span class="spinner-border spinner-border-sm text-primary" role="status" aria-hidden="true"></span>
                <span class="small text-muted">Checking system status...</span>
            </div>
        `;

        try {
            const response = await fetch("/api/health");
            if (!response.ok) {
                throw new Error(`HTTP Error: ${response.status}`);
            }
            const data = await response.json();
            
            const isHealthy = data.status === "healthy";
            const isDegraded = data.status === "degraded";
            
            let statusText = "ONLINE";
            let statusClass = "text-success";
            let iconClass = "bi-check-circle-fill";
            let detailText = `Env: ${data.environment || "production"}`;

            if (isHealthy) {
                statusText = "VERIFIED OPERATIONAL";
                statusClass = "text-success";
                iconClass = "bi-check-circle-fill";
            } else if (isDegraded) {
                statusText = "ONLINE (DEVELOPMENT)";
                statusClass = "text-primary";
                iconClass = "bi-shield-check";
                detailText = "Operational via verified local datastore";
            }

            badge.innerHTML = `
                <div class="d-flex align-items-center justify-content-center gap-1 ${statusClass} fw-bold small">
                    <i class="bi ${iconClass}"></i>
                    <span>${data.app || "CampusQuery"} API: ${statusText}</span>
                </div>
                <div class="text-muted" style="font-size: 0.75rem;">
                    ${detailText} &bull; ${new Date(data.timestamp).toLocaleTimeString()}
                </div>
            `;
        } catch (error) {
            console.error("Health check error:", error);
            badge.innerHTML = `
                <div class="text-danger fw-bold small">
                    <i class="bi bi-exclamation-triangle-fill me-1"></i> Health Service Offline
                </div>
                <div class="text-muted" style="font-size: 0.72rem;">
                    Check server console logs
                </div>
            `;
        }
    };

    // Run automatically on page load
    performCheck();

    // Attach click handler if button exists
    if (btn) {
        btn.addEventListener("click", performCheck);
    }
}

/**
 * Attaches submit listeners to forms to provide immediate loading feedback
 * and prevent accidental double submissions.
 */
function initFormLoading() {
    const forms = document.querySelectorAll("form:not([data-no-loading])");
    forms.forEach(form => {
        form.addEventListener("submit", function(event) {
            // Check HTML5 client-side validation first
            if (this.checkValidity && !this.checkValidity()) {
                return;
            }

            const submitBtn = this.querySelector("button[type='submit']:not([data-no-loading])");
            if (submitBtn && !submitBtn.disabled) {
                // If it's a GET search form, do not disable or block history
                if (this.method && this.method.toUpperCase() === "GET") {
                    return;
                }

                submitBtn.classList.add("btn-loading");
                submitBtn.disabled = true;
                const originalText = submitBtn.innerHTML;

                // Add spinner next to existing text
                submitBtn.innerHTML = `
                    <span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>
                    <span>Processing...</span>
                `;

                // Safety timeout in case navigation is cancelled or slow
                setTimeout(() => {
                    if (submitBtn && submitBtn.disabled) {
                        submitBtn.disabled = false;
                        submitBtn.classList.remove("btn-loading");
                        submitBtn.innerHTML = originalText;
                    }
                }, 8000);
            }
        });
    });
}

/**
 * Accessible auto-dismissal for flash alerts after an informative delay.
 */
function initAlertDismissal() {
    const alerts = document.querySelectorAll(".alert.alert-dismissible:not(.alert-danger):not(.alert-warning)");
    alerts.forEach(alert => {
        setTimeout(() => {
            if (typeof bootstrap !== "undefined" && bootstrap.Alert) {
                const bsAlert = bootstrap.Alert.getInstance(alert) || new bootstrap.Alert(alert);
                bsAlert.close();
            } else {
                alert.classList.remove("show");
                setTimeout(() => alert.remove(), 300);
            }
        }, 6000);
    });
}

/**
 * Enhances keyboard usability for power users and accessible screen navigation.
 */
function initKeyboardShortcuts() {
    document.addEventListener("keydown", (e) => {
        // Pressing '/' when not typing focuses the search input if present
        if (e.key === "/" && !["INPUT", "TEXTAREA"].includes(document.activeElement.tagName)) {
            const searchInput = document.querySelector("input[name='q']");
            if (searchInput) {
                e.preventDefault();
                searchInput.focus();
                searchInput.select();
            }
        }
    });
}
