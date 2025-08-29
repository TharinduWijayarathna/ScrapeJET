// ScrapeJET Web Scraper UI - JavaScript
// Advanced web scraper interface with real-time progress tracking

class ScrapeJETUI {
  constructor() {
    this.apiBaseUrl = "http://localhost:8000";
    this.currentScrapeId = null;
    this.progressInterval = null;
    this.startTime = null;
    this.sites = [];

    this.init();
  }

  init() {
    this.setupEventListeners();
    this.checkApiStatus();
    this.loadSites();
    this.setupProgressTracking();
  }

  // Event Listeners
  setupEventListeners() {
    // Tab switching
    document.querySelectorAll(".tab-btn").forEach((btn) => {
      btn.addEventListener("click", (e) =>
        this.switchTab(e.target.dataset.tab),
      );
    });

    // Scraper form
    document
      .getElementById("scrapeForm")
      .addEventListener("submit", (e) => this.handleScrape(e));
    document
      .getElementById("stopScrapeBtn")
      .addEventListener("click", () => this.stopScrape());

    // Query form
    document
      .getElementById("queryForm")
      .addEventListener("submit", (e) => this.handleQuery(e));
    document
      .getElementById("clearQueryBtn")
      .addEventListener("click", () => this.clearQuery());

    // Quick questions
    document.querySelectorAll(".quick-btn").forEach((btn) => {
      btn.addEventListener("click", (e) =>
        this.handleQuickQuestion(e.target.dataset.question),
      );
    });

    // Sites refresh
    document
      .getElementById("refreshSitesBtn")
      .addEventListener("click", () => this.loadSites());

    // Window focus/blur for progress tracking
    window.addEventListener("focus", () => this.resumeProgressTracking());
    window.addEventListener("blur", () => this.pauseProgressTracking());
  }

  // Tab Management
  switchTab(tabName) {
    // Update tab buttons
    document
      .querySelectorAll(".tab-btn")
      .forEach((btn) => btn.classList.remove("active"));
    document.querySelector(`[data-tab="${tabName}"]`).classList.add("active");

    // Update tab content
    document
      .querySelectorAll(".tab-content")
      .forEach((content) => content.classList.remove("active"));
    document.getElementById(tabName).classList.add("active");

    // Load data if needed
    if (tabName === "sites") {
      this.loadSites();
    } else if (tabName === "analytics") {
      this.loadAnalytics();
    } else if (tabName === "query") {
      this.loadQuerySites();
    }
  }

  // API Status Check
  async checkApiStatus() {
    try {
      const response = await fetch(`${this.apiBaseUrl}/health`);
      const data = await response.json();

      if (response.ok) {
        this.updateStatus("online", "API Online");
        this.showToast(
          "success",
          "Connected",
          "Successfully connected to ScrapeJET API",
        );
      } else {
        throw new Error("API not healthy");
      }
    } catch (error) {
      console.error("API Status Check Failed:", error);
      this.updateStatus("offline", "API Offline");
      this.showToast(
        "error",
        "Connection Failed",
        "Could not connect to ScrapeJET API",
      );
    }
  }

  updateStatus(status, text) {
    const statusDot = document.getElementById("statusDot");
    const statusText = document.getElementById("statusText");

    statusDot.className = `status-dot ${status}`;
    statusText.textContent = text;
  }

  // Scraping Functions
  async handleScrape(e) {
    e.preventDefault();

    const url = document.getElementById("scrapeUrl").value;
    const expectedPages = parseInt(
      document.getElementById("expectedPages").value,
    );
    const outputFormat = document.getElementById("outputFormat").value;

    if (!url) {
      this.showToast("error", "Validation Error", "Please enter a valid URL");
      return;
    }

    this.startScraping(url, expectedPages, outputFormat);
  }

  async startScraping(url, expectedPages, outputFormat) {
    try {
      // Update UI
      this.showProgress("scrape");
      this.updateScrapeProgress(0, "Initializing scraper...", 0, "-", 0);

      // Start timing
      this.startTime = Date.now();
      this.startProgressTimer();

      // Make API call
      const response = await fetch(`${this.apiBaseUrl}/scrape`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          url: url,
          expected_pages: expectedPages,
          output_format: outputFormat,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      this.handleScrapeSuccess(data);
    } catch (error) {
      console.error("Scraping Error:", error);
      this.handleScrapeError(error);
    }
  }

  handleScrapeSuccess(data) {
    this.stopProgressTimer();

    // Hide progress, show results
    document.getElementById("scrapeProgress").style.display = "none";
    document.getElementById("scrapeResults").style.display = "block";

    // Update results
    document.getElementById("totalPages").textContent = data.total_pages || 0;
    document.getElementById("filesCreated").textContent = Object.keys(
      data.files || {},
    ).length;
    document.getElementById("totalDuration").textContent = this.formatDuration(
      Date.now() - this.startTime,
    );

    // Display files
    this.displayResultFiles(data.files || {});

    // Reset form
    this.resetScrapeForm();

    // Show success toast
    this.showToast(
      "success",
      "Scraping Complete",
      `Successfully scraped ${data.total_pages} pages from the website`,
    );

    // Refresh sites
    setTimeout(() => this.loadSites(), 1000);
  }

  handleScrapeError(error) {
    this.stopProgressTimer();
    this.hideProgress("scrape");
    this.resetScrapeForm();

    this.showToast("error", "Scraping Failed", error.message);
  }

  stopScrape() {
    // In a real implementation, you'd send a stop request to the API
    this.stopProgressTimer();
    this.hideProgress("scrape");
    this.resetScrapeForm();

    this.showToast(
      "info",
      "Scraping Stopped",
      "Scraping operation was stopped by user",
    );
  }

  resetScrapeForm() {
    document.getElementById("scrapeBtn").style.display = "flex";
    document.getElementById("stopScrapeBtn").style.display = "none";
    document
      .getElementById("scrapeForm")
      .querySelectorAll("input, select")
      .forEach((el) => {
        el.disabled = false;
      });
  }

  // Progress Tracking
  setupProgressTracking() {
    // Simulate progress for demonstration
    // In a real implementation, you'd get this from the API
  }

  startProgressTimer() {
    document.getElementById("scrapeBtn").style.display = "none";
    document.getElementById("stopScrapeBtn").style.display = "flex";
    document
      .getElementById("scrapeForm")
      .querySelectorAll("input, select")
      .forEach((el) => {
        el.disabled = true;
      });

    // Simulate progress updates
    let progress = 0;
    let pagesFound = 0;
    let currentPage = "homepage";

    this.progressInterval = setInterval(() => {
      progress += Math.random() * 5;
      pagesFound += Math.floor(Math.random() * 3);

      if (progress > 95) {
        progress = 95; // Don't complete until API responds
      }

      const elapsed = Date.now() - this.startTime;
      this.updateScrapeProgress(
        progress,
        `Processing ${currentPage}...`,
        pagesFound,
        currentPage,
        elapsed,
      );

      // Simulate different page types
      const pages = [
        "homepage",
        "products",
        "categories",
        "contact",
        "about",
        "blog",
      ];
      currentPage = pages[Math.floor(Math.random() * pages.length)];
    }, 500);
  }

  stopProgressTimer() {
    if (this.progressInterval) {
      clearInterval(this.progressInterval);
      this.progressInterval = null;
    }
  }

  updateScrapeProgress(percentage, text, pagesFound, currentPage, elapsed) {
    document.getElementById("scrapeProgressFill").style.width =
      `${percentage}%`;
    document.getElementById("scrapeProgressText").textContent = text;
    document.getElementById("pagesFound").textContent = pagesFound;
    document.getElementById("currentPage").textContent = currentPage;
    document.getElementById("timeElapsed").textContent =
      this.formatDuration(elapsed);
  }

  showProgress(type) {
    if (type === "scrape") {
      document.getElementById("scrapeProgress").style.display = "block";
      document.getElementById("scrapeResults").style.display = "none";
    } else if (type === "query") {
      document.getElementById("queryProgress").style.display = "block";
      document.getElementById("queryResults").style.display = "none";
    }
  }

  hideProgress(type) {
    if (type === "scrape") {
      document.getElementById("scrapeProgress").style.display = "none";
    } else if (type === "query") {
      document.getElementById("queryProgress").style.display = "none";
    }
  }

  resumeProgressTracking() {
    // Resume any paused operations
  }

  pauseProgressTracking() {
    // Pause operations when window loses focus
  }

  // Query Functions
  async handleQuery(e) {
    e.preventDefault();

    const question = document.getElementById("queryQuestion").value;
    const siteName = document.getElementById("querySite").value;
    const nResults = parseInt(document.getElementById("queryNumResults").value);

    if (!question.trim()) {
      this.showToast("error", "Validation Error", "Please enter a question");
      return;
    }

    this.executeQuery(question, siteName, nResults);
  }

  async executeQuery(question, siteName, nResults) {
    try {
      this.showProgress("query");

      const requestBody = {
        question: question,
        n_results: nResults,
      };

      if (siteName) {
        requestBody.site_name = siteName;
      }

      const response = await fetch(`${this.apiBaseUrl}/query`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(
          `HTTP ${response.status}: ${response.statusText} - ${errorText}`,
        );
      }

      const data = await response.json();
      this.displayQueryResults(data);
    } catch (error) {
      console.error("Query Error:", error);
      this.hideProgress("query");
      this.showToast("error", "Query Failed", error.message);
    }
  }

  displayQueryResults(data) {
    this.hideProgress("query");

    // Show results section
    const queryResultsElement = document.getElementById("queryResults");
    if (queryResultsElement) {
      queryResultsElement.style.display = "block";
    } else {
      this.showToast("error", "UI Error", "Query results element not found");
      return;
    }

    // Display answer
    const answerBox = document.getElementById("answerBox");
    if (answerBox && data.answer) {
      answerBox.innerHTML = this.formatAnswer(data.answer);
    } else if (answerBox) {
      answerBox.innerHTML = "No answer received from the API.";
    }

    // Display context
    const contextList = document.getElementById("contextList");
    if (contextList) {
      contextList.innerHTML = "";

      if (data.context && data.context.length > 0) {
        data.context.forEach((ctx, index) => {
          const contextItem = document.createElement("div");
          contextItem.className = "context-item";
          contextItem.innerHTML = `
                        <div class="context-header">
                            <a href="${ctx.url || "#"}" class="context-url" target="_blank">
                                ${ctx.url || "Unknown URL"}
                            </a>
                        </div>
                        <div class="context-content">${this.truncateText(ctx.content || "", 200)}</div>
                    `;
          contextList.appendChild(contextItem);
        });
      } else {
        contextList.innerHTML =
          '<div class="context-item">No relevant context found.</div>';
      }
    }

    this.showToast(
      "success",
      "Query Complete",
      "Your question has been answered",
    );
  }

  handleQuickQuestion(question) {
    document.getElementById("queryQuestion").value = question;
    document.getElementById("queryForm").dispatchEvent(new Event("submit"));
  }

  clearQuery() {
    document.getElementById("queryQuestion").value = "";
    document.getElementById("querySite").value = "";
    document.getElementById("queryNumResults").value = "5";
    document.getElementById("queryResults").style.display = "none";
    this.hideProgress("query");
  }

  // Sites Management
  async loadSites() {
    try {
      document.getElementById("sitesLoading").style.display = "block";

      const response = await fetch(`${this.apiBaseUrl}/sites`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      this.sites = data.sites || [];
      this.displaySites(data.sites || [], data.stats || {});
      this.updateQuerySiteOptions();
    } catch (error) {
      console.error("Error loading sites:", error);
      this.showToast("error", "Load Error", "Failed to load sites data");
    } finally {
      document.getElementById("sitesLoading").style.display = "none";
    }
  }

  displaySites(sites, stats) {
    const sitesGrid = document.getElementById("sitesGrid");
    sitesGrid.innerHTML = "";

    if (sites.length === 0) {
      sitesGrid.innerHTML = `
                <div class="loading-spinner">
                    <i class="fas fa-info-circle"></i>
                    <p>No sites scraped yet. Start by scraping a website!</p>
                </div>
            `;
      return;
    }

    sites.forEach((site) => {
      const siteStats = stats[site] || {};
      const siteCard = document.createElement("div");
      siteCard.className = "site-card";
      siteCard.innerHTML = `
                <div class="site-header">
                    <div class="site-name">${site}</div>
                    <div class="site-status active">Active</div>
                </div>
                <div class="site-stats">
                    <div class="site-stat">
                        <div class="site-stat-number">${siteStats.total_pages || 0}</div>
                        <div class="site-stat-label">Pages</div>
                    </div>
                    <div class="site-stat">
                        <div class="site-stat-number">${siteStats.total_chunks || 0}</div>
                        <div class="site-stat-label">Chunks</div>
                    </div>
                </div>
                <div class="site-actions">
                    <button class="btn-small btn-info" onclick="ui.viewSiteInfo('${site}')">
                        <i class="fas fa-info"></i> Info
                    </button>
                    <button class="btn-small btn-danger" onclick="ui.deleteSite('${site}')">
                        <i class="fas fa-trash"></i> Delete
                    </button>
                </div>
            `;
      sitesGrid.appendChild(siteCard);
    });
  }

  updateQuerySiteOptions() {
    const select = document.getElementById("querySite");
    select.innerHTML = '<option value="">All Sites</option>';

    this.sites.forEach((site) => {
      const option = document.createElement("option");
      option.value = site;
      option.textContent = site;
      select.appendChild(option);
    });
  }

  loadQuerySites() {
    this.updateQuerySiteOptions();
  }

  async viewSiteInfo(siteName) {
    try {
      const response = await fetch(`${this.apiBaseUrl}/sites/${siteName}/info`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      this.showSiteInfoModal(siteName, data.info);
    } catch (error) {
      console.error("Error loading site info:", error);
      this.showToast("error", "Load Error", "Failed to load site information");
    }
  }

  async deleteSite(siteName) {
    if (!confirm(`Are you sure you want to delete all data for ${siteName}?`)) {
      return;
    }

    try {
      const response = await fetch(`${this.apiBaseUrl}/sites/${siteName}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      this.showToast(
        "success",
        "Site Deleted",
        `Successfully deleted data for ${siteName}`,
      );
      this.loadSites();
    } catch (error) {
      console.error("Error deleting site:", error);
      this.showToast("error", "Delete Error", "Failed to delete site data");
    }
  }

  // Analytics
  async loadAnalytics() {
    try {
      // Load sites data for analytics
      const response = await fetch(`${this.apiBaseUrl}/sites`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      this.updateAnalytics(data.sites || [], data.stats || {});
    } catch (error) {
      console.error("Error loading analytics:", error);
      this.showToast("error", "Load Error", "Failed to load analytics data");
    }
  }

  updateAnalytics(sites, stats) {
    let totalPages = 0;
    let totalChunks = 0;
    let totalProducts = 0;

    Object.values(stats).forEach((siteStats) => {
      totalPages += siteStats.total_pages || 0;
      totalChunks += siteStats.total_chunks || 0;
      totalProducts += siteStats.total_products || 0;
    });

    document.getElementById("totalSites").textContent = sites.length;
    document.getElementById("totalPagesAnalytics").textContent = totalPages;
    document.getElementById("totalProducts").textContent = totalProducts;
    document.getElementById("totalChunks").textContent = totalChunks;

    this.updateActivityList();
  }

  updateActivityList() {
    const activityList = document.getElementById("activityList");
    const activities = [
      { icon: "fas fa-spider", text: "System initialized", time: "Just now" },
      {
        icon: "fas fa-database",
        text: `${this.sites.length} sites loaded`,
        time: "1 min ago",
      },
    ];

    activityList.innerHTML = activities
      .map(
        (activity) => `
            <div class="activity-item">
                <i class="${activity.icon}"></i>
                <span>${activity.text}</span>
            </div>
        `,
      )
      .join("");
  }

  // Utility Functions
  showSiteInfoModal(siteName, info) {
    // Create a simple modal or use the toast system
    const infoText = JSON.stringify(info, null, 2);
    this.showToast(
      "info",
      `Site Info: ${siteName}`,
      `Site information loaded. Check console for details.`,
    );
    console.log(`Site Info for ${siteName}:`, info);
  }

  displayResultFiles(files) {
    const resultFiles = document.getElementById("resultFiles");
    resultFiles.innerHTML = "<h4>Generated Files:</h4>";

    Object.entries(files).forEach(([key, filename]) => {
      const fileItem = document.createElement("div");
      fileItem.className = "file-item";
      fileItem.innerHTML = `
                <span class="file-name">${filename}</span>
                <span class="file-size">JSON</span>
            `;
      resultFiles.appendChild(fileItem);
    });
  }

  formatAnswer(answer) {
    // Simple formatting for the answer
    return answer
      .replace(/\n/g, "<br>")
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
  }

  truncateText(text, maxLength) {
    return text.length > maxLength
      ? text.substring(0, maxLength) + "..."
      : text;
  }

  formatDuration(ms) {
    const seconds = Math.floor(ms / 1000);
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  }

  // Toast Notifications
  showToast(type, title, message, duration = 5000) {
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.innerHTML = `
            <div class="toast-header">
                <span class="toast-title">${title}</span>
                <button class="toast-close">&times;</button>
            </div>
            <div class="toast-message">${message}</div>
        `;

    document.getElementById("toastContainer").appendChild(toast);

    // Close button
    toast.querySelector(".toast-close").addEventListener("click", () => {
      toast.remove();
    });

    // Auto remove
    setTimeout(() => {
      if (toast.parentNode) {
        toast.remove();
      }
    }, duration);

    return toast;
  }

  // Loading States
  showLoading(message = "Processing...") {
    const overlay = document.getElementById("loadingOverlay");
    overlay.querySelector("p").textContent = message;
    overlay.style.display = "flex";
  }

  hideLoading() {
    document.getElementById("loadingOverlay").style.display = "none";
  }
}

// Initialize the UI when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  window.ui = new ScrapeJETUI();
});

// Global functions for onclick handlers
function viewSiteInfo(siteName) {
  window.ui.viewSiteInfo(siteName);
}

function deleteSite(siteName) {
  window.ui.deleteSite(siteName);
}

// Error handling
window.addEventListener("error", (e) => {
  console.error("JavaScript Error:", e.error);
  if (window.ui) {
    window.ui.showToast(
      "error",
      "JavaScript Error",
      "An unexpected error occurred",
    );
  }
});
