// Scraper Web Scraper UI - JavaScript
// Advanced web scraper interface with real-time progress tracking

class ScraperUI {
  constructor() {
    this.apiBaseUrl = "http://localhost:8000";
    this.currentScrapeId = null;
    this.progressInterval = null;
    this.sites = [];

    this.init();
  }

  init() {
    this.setupEventListeners();
    this.checkApiStatus();
    // Delay loading sites to ensure DOM is ready
    setTimeout(() => {
      this.loadSites();
    }, 100);
    this.setupProgressTracking();
  }

  // Event Listeners
  setupEventListeners() {
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => {
        this.setupEventListenersInternal();
      });
    } else {
      this.setupEventListenersInternal();
    }
  }

  setupEventListenersInternal() {
    // Sidebar functionality
    const openSidebarBtn = document.getElementById("openSidebar");
    const closeSidebarBtn = document.getElementById("closeSidebar");
    const sidebar = document.getElementById("sidebar");

    if (openSidebarBtn) {
      openSidebarBtn.addEventListener("click", () => {
        sidebar.classList.remove("-translate-x-full");
      });
    }

    if (closeSidebarBtn) {
      closeSidebarBtn.addEventListener("click", () => {
        sidebar.classList.add("-translate-x-full");
      });
    }

    // Navigation
    document.querySelectorAll(".nav-item").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        this.switchTab(e.currentTarget.dataset.tab);
        // Close sidebar on mobile after navigation
        if (window.innerWidth < 1024) {
          sidebar.classList.add("-translate-x-full");
        }
      });
    });

    // Scraper form
    const scrapeForm = document.getElementById("scrapeForm");
    if (scrapeForm) {
      scrapeForm.addEventListener("submit", (e) => this.handleScrape(e));
    }
    
    const stopScrapeBtn = document.getElementById("stopScrapeBtn");
    if (stopScrapeBtn) {
      stopScrapeBtn.addEventListener("click", () => this.stopScrape());
    }

    // Query form
    const queryForm = document.getElementById("queryForm");
    if (queryForm) {
      queryForm.addEventListener("submit", (e) => this.handleQuery(e));
    }
    
    const clearQueryBtn = document.getElementById("clearQueryBtn");
    if (clearQueryBtn) {
      clearQueryBtn.addEventListener("click", () => this.clearQuery());
    }

    // Quick questions
    document.querySelectorAll(".quick-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const question = e.currentTarget.dataset.question;
        this.handleQuickQuestion(question);
      });
    });

    // Sites refresh
    const refreshSitesBtn = document.getElementById("refreshSitesBtn");
    if (refreshSitesBtn) {
      refreshSitesBtn.addEventListener("click", () => this.loadSites());
    }

    // Window focus/blur for progress tracking
    window.addEventListener("focus", () => this.resumeProgressTracking());
    window.addEventListener("blur", () => this.pauseProgressTracking());
  }

  // Progress Tracking Setup
  setupProgressTracking() {
    // Initialize progress tracking variables
    this.progressInterval = null;
    this.currentScrapeId = null;
    
    // Set up any additional progress tracking initialization
    console.log("Progress tracking initialized");
  }

  // Tab Management
  switchTab(tabName) {
    // Update navigation items
    document.querySelectorAll(".nav-item").forEach((btn) => {
      btn.classList.remove("bg-blue-50", "text-blue-700", "border-blue-200");
      btn.classList.add("text-gray-700", "hover:bg-gray-100");
      btn.querySelector("i").classList.remove("text-blue-600");
      btn.querySelector("i").classList.add("text-gray-500");
    });

    const activeBtn = document.querySelector(`[data-tab="${tabName}"]`);
    if (activeBtn) {
      activeBtn.classList.remove("text-gray-700", "hover:bg-gray-100");
      activeBtn.classList.add("bg-blue-50", "text-blue-700", "border", "border-blue-200");
      activeBtn.querySelector("i").classList.remove("text-gray-500");
      activeBtn.querySelector("i").classList.add("text-blue-600");
    }

    // Update tab content
    document.querySelectorAll(".tab-content").forEach((content) => {
      content.style.display = "none";
    });
    document.getElementById(tabName).style.display = "block";

    // Update page title
    const pageTitle = document.getElementById("pageTitle");
    if (pageTitle) {
      const titles = {
        scraper: "Web Scraper",
        query: "AI Query",
        sites: "Scraped Sites",
        analytics: "Analytics"
      };
      pageTitle.textContent = titles[tabName] || "Dashboard";
    }

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
        this.showToast("success", "Connected", "Successfully connected to Scraper API");
      } else {
        throw new Error("API not healthy");
      }
    } catch (error) {
      console.error("API Status Check Failed:", error);
      this.updateStatus("offline", "API Offline");
      this.showToast("error", "Connection Failed", "Cannot connect to Scraper API");
    }
  }

  updateStatus(status, text) {
    const statusEl = document.getElementById("apiStatus");
    if (!statusEl) return;

    if (status === "online") {
      statusEl.className = "inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800";
      statusEl.innerHTML = '<span class="w-2 h-2 bg-green-400 rounded-full mr-1"></span>Online';
    } else {
      statusEl.className = "inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800";
      statusEl.innerHTML = '<span class="w-2 h-2 bg-red-400 rounded-full mr-1"></span>Offline';
    }
  }

  // Scraping
  async handleScrape(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const url = formData.get("url");
    const maxPages = parseInt(formData.get("maxPages")) || 10;

    if (!url) {
      this.showToast("error", "Validation Error", "Please enter a valid URL");
      return;
    }

    try {
      this.showLoadingOverlay();
      
      const response = await fetch(`${this.apiBaseUrl}/scrape`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          url: url,
          expected_pages: maxPages,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const data = await response.json();
      this.currentScrapeId = data.job_id;
      
      this.showScrapeProgress();
      this.startRealProgressTracking();
      
      this.showToast("success", "Scraping Started", "Web scraping job initiated successfully");
      
    } catch (error) {
      console.error("Scraping error:", error);
      this.showToast("error", "Scraping Failed", error.message);
    } finally {
      this.hideLoadingOverlay();
    }
  }

  showScrapeProgress() {
    const progressSection = document.getElementById("progressSection");
    const scrapeBtn = document.getElementById("scrapeBtn");
    const stopScrapeBtn = document.getElementById("stopScrapeBtn");
    
    if (progressSection) progressSection.style.display = "block";
    if (scrapeBtn) scrapeBtn.style.display = "none";
    if (stopScrapeBtn) stopScrapeBtn.style.display = "flex";
  }

  hideScrapeProgress() {
    const progressSection = document.getElementById("progressSection");
    const scrapeBtn = document.getElementById("scrapeBtn");
    const stopScrapeBtn = document.getElementById("stopScrapeBtn");
    
    if (progressSection) progressSection.style.display = "none";
    if (scrapeBtn) scrapeBtn.style.display = "flex";
    if (stopScrapeBtn) stopScrapeBtn.style.display = "none";
  }

  startRealProgressTracking() {
    if (this.progressInterval) {
      clearInterval(this.progressInterval);
    }

    this.progressInterval = setInterval(async () => {
      if (!this.currentScrapeId) return;

      try {
        const response = await fetch(`${this.apiBaseUrl}/scrape/${this.currentScrapeId}/progress`);
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        this.updateScrapeProgress(data);
        
        if (data.status === "completed" || data.status === "failed" || data.status === "cancelled") {
          this.handleScrapeComplete(data);
        }
        
      } catch (error) {
        console.error("Progress tracking error:", error);
        this.stopProgressTracking();
      }
    }, 1500);
  }

  updateScrapeProgress(data) {
    console.log("Progress data received:", data); // Debug log
    
    const progressFill = document.getElementById("progressFill");
    const currentPage = document.getElementById("currentPage");
    const pagesFound = document.getElementById("pagesFound");
    const targetPages = document.getElementById("targetPages");
    const scrapeProgressText = document.getElementById("scrapeProgressText");

    if (progressFill) {
      const percentage = data.progress || 0;
      progressFill.style.width = `${percentage}%`;
      
      // Update progress bar classes based on status
      progressFill.className = "progress-bar h-full rounded-full transition-all duration-300";
      if (data.status === "running") {
        progressFill.classList.add("loading");
      } else if (data.status === "completed") {
        progressFill.classList.add("completed");
      }
    }

    if (currentPage) {
      currentPage.textContent = data.current_page || "Starting...";
    }

    if (pagesFound) {
      pagesFound.textContent = data.pages_scraped || 0;
    }

    if (targetPages) {
      targetPages.textContent = data.total_pages || 0;
    }

    if (scrapeProgressText) {
      let statusText = "Initializing scraper...";
      
      if (data.status === "running") {
        statusText = data.message || "Scraping in progress...";
      } else if (data.status === "completed") {
        statusText = data.message || "Scraping completed successfully!";
      } else if (data.status === "failed") {
        statusText = "Scraping failed: " + (data.message || "Unknown error");
      } else if (data.status === "cancelled") {
        statusText = "Scraping was cancelled";
      }
      
      scrapeProgressText.textContent = statusText;
    }
  }

  async handleScrapeComplete(data) {
    this.stopProgressTracking();
    
    if (data.status === "completed") {
      try {
        const response = await fetch(`${this.apiBaseUrl}/scrape/${this.currentScrapeId}/result`);
        if (response.ok) {
          const resultData = await response.json();
          this.displayScrapeResults(resultData);
        }
      } catch (error) {
        console.error("Error fetching results:", error);
      }
      
      this.showToast("success", "Scraping Complete", "Website scraping completed successfully!");
    } else if (data.status === "failed") {
      this.showToast("error", "Scraping Failed", data.error || "Unknown error occurred");
    } else if (data.status === "cancelled") {
      this.showToast("info", "Scraping Cancelled", "Scraping job was cancelled");
    }
    
    this.currentScrapeId = null;
    this.hideScrapeProgress();
  }

  displayScrapeResults(data) {
    const resultsSection = document.getElementById("resultsSection");
    const resultsContent = document.getElementById("resultsContent");
    
    if (!resultsSection || !resultsContent) return;
    
    // Safely handle files data
    let filesHtml = '';
    if (data.files && Array.isArray(data.files) && data.files.length > 0) {
      filesHtml = `
        <div class="mt-6">
          <h4 class="text-lg font-semibold text-gray-900 mb-4">Generated Files</h4>
          <div class="space-y-2">
            ${data.files.map(file => `
              <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span class="text-sm text-gray-700">${file}</span>
                <button class="text-blue-600 hover:text-blue-800 text-sm font-medium">
                  <i class="fas fa-download mr-1"></i>Download
                </button>
              </div>
            `).join('')}
          </div>
        </div>
      `;
    } else if (data.files && typeof data.files === 'object') {
      // Handle case where files is an object with file paths as keys
      const fileList = Object.keys(data.files);
      if (fileList.length > 0) {
        filesHtml = `
          <div class="mt-6">
            <h4 class="text-lg font-semibold text-gray-900 mb-4">Generated Files</h4>
            <div class="space-y-2">
              ${fileList.map(filePath => `
                <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <span class="text-sm text-gray-700">${filePath}</span>
                  <button class="text-blue-600 hover:text-blue-800 text-sm font-medium">
                    <i class="fas fa-download mr-1"></i>Download
                  </button>
                </div>
              `).join('')}
            </div>
          </div>
        `;
      }
    }
    
    resultsContent.innerHTML = `
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div class="bg-blue-50 rounded-lg p-6 border border-blue-200">
          <div class="flex items-center mb-2">
            <i class="fas fa-file-alt text-blue-600 text-xl mr-3"></i>
            <h4 class="text-lg font-semibold text-blue-900">Total Pages</h4>
          </div>
          <p class="text-3xl font-bold text-blue-900">${data.total_pages || data.stats?.total_pages || 0}</p>
        </div>
        
        <div class="bg-green-50 rounded-lg p-6 border border-green-200">
          <div class="flex items-center mb-2">
            <i class="fas fa-download text-green-600 text-xl mr-3"></i>
            <h4 class="text-lg font-semibold text-green-900">Files Created</h4>
          </div>
          <p class="text-3xl font-bold text-green-900">${data.files_created || (data.files ? Object.keys(data.files).length : 0)}</p>
        </div>
        
        <div class="bg-purple-50 rounded-lg p-6 border border-purple-200">
          <div class="flex items-center mb-2">
            <i class="fas fa-clock text-purple-600 text-xl mr-3"></i>
            <h4 class="text-lg font-semibold text-purple-900">Duration</h4>
          </div>
          <p class="text-3xl font-bold text-purple-900">${this.formatDuration(data.stats?.start_time, data.stats?.end_time) || "0s"}</p>
        </div>
      </div>
      
      ${filesHtml}
      
      ${data.stats ? `
        <div class="mt-6">
          <h4 class="text-lg font-semibold text-gray-900 mb-4">Scraping Statistics</h4>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div class="bg-gray-50 rounded-lg p-4 text-center">
              <div class="text-2xl font-bold text-blue-600">${data.stats.successful_pages || 0}</div>
              <div class="text-sm text-gray-600">Successful</div>
            </div>
            <div class="bg-gray-50 rounded-lg p-4 text-center">
              <div class="text-2xl font-bold text-red-600">${data.stats.failed_pages || 0}</div>
              <div class="text-sm text-gray-600">Failed</div>
            </div>
            <div class="bg-gray-50 rounded-lg p-4 text-center">
              <div class="text-2xl font-bold text-yellow-600">${data.stats.duplicate_pages || 0}</div>
              <div class="text-sm text-gray-600">Duplicates</div>
            </div>
            <div class="bg-gray-50 rounded-lg p-4 text-center">
              <div class="text-2xl font-bold text-green-600">${data.stats.requests_pages || 0}</div>
              <div class="text-sm text-gray-600">Requests</div>
            </div>
          </div>
        </div>
      ` : ''}
    `;
    
    resultsSection.style.display = "block";
  }

  async stopScrape() {
    if (!this.currentScrapeId) return;

    try {
      const response = await fetch(`${this.apiBaseUrl}/scrape/${this.currentScrapeId}`, {
        method: "DELETE",
      });

      if (response.ok) {
        this.showToast("info", "Scraping Stopped", "Scraping job cancelled successfully");
        this.handleScrapeCancelled();
      } else {
        throw new Error(`HTTP ${response.status}`);
      }
    } catch (error) {
      console.error("Error stopping scrape:", error);
      this.showToast("error", "Stop Failed", "Failed to stop scraping job");
    }
  }

  handleScrapeCancelled() {
    this.stopProgressTracking();
    this.currentScrapeId = null;
    this.hideScrapeProgress();
  }

  stopProgressTracking() {
    if (this.progressInterval) {
      clearInterval(this.progressInterval);
      this.progressInterval = null;
    }
  }

  pauseProgressTracking() {
    if (this.progressInterval) {
      clearInterval(this.progressInterval);
    }
  }

  resumeProgressTracking() {
    if (this.currentScrapeId && !this.progressInterval) {
      this.startRealProgressTracking();
    }
  }

  // Query System
  async handleQuery(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const query = formData.get("query");
    const site = formData.get("site");

    if (!query.trim()) {
      this.showToast("error", "Validation Error", "Please enter a question");
      return;
    }

    try {
      this.showLoadingOverlay();
      
      const response = await fetch(`${this.apiBaseUrl}/query`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: query,
          site_name: site || null,
          n_results: 5,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const data = await response.json();
      this.displayQueryResults(data);
      
      this.showToast("success", "Query Complete", "AI response generated successfully");
      
    } catch (error) {
      console.error("Query error:", error);
      this.showToast("error", "Query Failed", error.message);
    } finally {
      this.hideLoadingOverlay();
    }
  }

  displayQueryResults(data) {
    const queryResults = document.getElementById("queryResults");
    const queryContent = document.getElementById("queryContent");
    
    if (!queryResults || !queryContent) return;
    
    // Format the answer with better structure
    const formattedAnswer = this.formatAIAnswer(data.answer || "No answer available");
    
    // Show site filter info if a specific site was selected
    const siteFilterInfo = data.site_name ? `
      <div class="mb-4 p-3 bg-blue-100 rounded-lg border border-blue-200">
        <div class="flex items-center">
          <i class="fas fa-filter text-blue-600 mr-2"></i>
          <span class="text-sm font-medium text-blue-800">
            Filtered by site: <strong>${data.site_name}</strong>
          </span>
        </div>
      </div>
    ` : '';
    
    queryContent.innerHTML = `
      <div class="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl p-6 border border-blue-200 mb-6">
        <div class="flex items-center mb-4">
          <div class="w-10 h-10 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center mr-3">
            <i class="fas fa-robot text-white"></i>
          </div>
          <div>
            <h4 class="text-lg font-semibold text-blue-900">AI Answer</h4>
            <p class="text-sm text-blue-600">Powered by OpenAI</p>
          </div>
        </div>
        ${siteFilterInfo}
        <div class="prose prose-blue max-w-none">
          ${formattedAnswer}
        </div>
      </div>
      
      ${data.context && data.context.length > 0 ? `
        <div class="bg-white rounded-xl border border-gray-200 p-6">
          <div class="flex items-center mb-4">
            <div class="w-8 h-8 bg-gray-100 rounded-lg flex items-center justify-center mr-3">
              <i class="fas fa-file-alt text-gray-600"></i>
            </div>
            <h4 class="text-lg font-semibold text-gray-900">Relevant Sources</h4>
          </div>
          <div class="space-y-4">
            ${data.context.map((item, index) => {
              const sourceSite = item.metadata?.source || 'Unknown source';
              const isFromSelectedSite = data.site_name && sourceSite.includes(data.site_name);
              
              return `
                <div class="bg-gray-50 rounded-lg p-4 border border-gray-200 hover:bg-gray-100 transition-colors">
                  <div class="flex items-start justify-between mb-3">
                    <div class="flex items-center">
                      <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${isFromSelectedSite ? 'bg-green-100 text-green-800' : 'bg-blue-100 text-blue-800'} mr-2">
                        Source ${index + 1}
                      </span>
                      <span class="text-xs text-gray-500">${sourceSite}</span>
                      ${isFromSelectedSite ? '<span class="ml-2 text-xs text-green-600 font-medium">✓ Selected Site</span>' : ''}
                    </div>
                    <div class="text-xs text-gray-400">
                      ${item.metadata?.page || ''}
                    </div>
                  </div>
                  <div class="text-sm text-gray-700 leading-relaxed">
                    ${this.formatContextContent(item.page_content || item.content || 'No content available')}
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        </div>
      ` : ''}
    `;
    
    queryResults.style.display = "block";
  }

  formatAIAnswer(answer) {
    // Convert plain text to structured HTML
    let formatted = answer
      // Convert line breaks to paragraphs
      .split('\n\n').map(paragraph => {
        if (paragraph.trim()) {
          return `<p class="mb-4 text-gray-700 leading-relaxed">${paragraph.trim()}</p>`;
        }
        return '';
      }).join('')
      
      // Convert single line breaks to <br>
      .replace(/\n/g, '<br>')
      
      // Highlight important terms
      .replace(/\*\*(.*?)\*\*/g, '<strong class="text-blue-900">$1</strong>')
      .replace(/\*(.*?)\*/g, '<em class="text-gray-600">$1</em>')
      
      // Format lists
      .replace(/^[-•*]\s+(.+)$/gm, '<li class="ml-4 mb-1">$1</li>')
      .replace(/(<li.*<\/li>)/s, '<ul class="list-disc list-inside mb-4 space-y-1">$1</ul>')
      
      // Format numbered lists
      .replace(/^\d+\.\s+(.+)$/gm, '<li class="ml-4 mb-1">$1</li>')
      .replace(/(<li.*<\/li>)/s, '<ol class="list-decimal list-inside mb-4 space-y-1">$1</ol>')
      
      // Format headings
      .replace(/^###\s+(.+)$/gm, '<h3 class="text-lg font-semibold text-gray-900 mb-3 mt-6">$1</h3>')
      .replace(/^##\s+(.+)$/gm, '<h2 class="text-xl font-bold text-gray-900 mb-4 mt-8">$1</h2>')
      .replace(/^#\s+(.+)$/gm, '<h1 class="text-2xl font-bold text-gray-900 mb-6 mt-10">$1</h1>')
      
      // Format code blocks
      .replace(/```(.*?)```/gs, '<pre class="bg-gray-100 p-3 rounded-lg text-sm font-mono overflow-x-auto mb-4">$1</pre>')
      .replace(/`(.*?)`/g, '<code class="bg-gray-100 px-1 py-0.5 rounded text-sm font-mono">$1</code>')
      
      // Format links
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-blue-600 hover:text-blue-800 underline" target="_blank">$1</a>');

    return formatted;
  }

  formatContextContent(content) {
    // Truncate long content and format it nicely
    const maxLength = 300;
    let formatted = content;
    
    if (content.length > maxLength) {
      formatted = content.substring(0, maxLength) + '...';
    }
    
    return formatted
      .replace(/\n/g, '<br>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>');
  }

  async handleQuickQuestion(question) {
    const queryText = document.getElementById("queryText");
    if (queryText) {
      queryText.value = question;
    }
    
    // Automatically submit the form
    const queryForm = document.getElementById("queryForm");
    if (queryForm) {
      queryForm.dispatchEvent(new Event("submit"));
    }
  }

  clearQuery() {
    const queryForm = document.getElementById("queryForm");
    const queryResults = document.getElementById("queryResults");
    
    if (queryForm) queryForm.reset();
    if (queryResults) queryResults.style.display = "none";
  }

  loadQuerySites() {
    this.updateQuerySiteOptions();
  }

  // Sites Management
  async loadSites() {
    try {
      const sitesLoadingEl = document.getElementById("sitesLoading");
      if (sitesLoadingEl) {
        sitesLoadingEl.style.display = "block";
      }

      console.log("Loading sites from:", `${this.apiBaseUrl}/sites`);
      
      const response = await fetch(`${this.apiBaseUrl}/sites`);
      console.log("Sites response status:", response.status);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error("Sites API error response:", errorText);
        throw new Error(`HTTP ${response.status}: ${response.statusText} - ${errorText}`);
      }

      const data = await response.json();
      console.log("Sites data received:", data);
      
      this.sites = data.sites || [];
      this.displaySites(data.sites || [], data.stats || {});
      this.updateQuerySiteOptions();
      
      console.log("Sites loaded successfully:", this.sites.length, "sites");
    } catch (error) {
      console.error("Error loading sites:", error);
      console.error("Error details:", error.stack);
      
      // Show more detailed error message
      let errorMessage = "Failed to load sites data";
      if (error.message.includes("Failed to fetch")) {
        errorMessage = "Cannot connect to API server. Please check if the server is running on localhost:8000";
      } else if (error.message.includes("CORS")) {
        errorMessage = "CORS error. Please open the UI from a web server instead of file://";
      } else {
        errorMessage = `Error: ${error.message}`;
      }
      
      this.showToast("error", "Load Error", errorMessage);
    } finally {
      const sitesLoadingEl = document.getElementById("sitesLoading");
      if (sitesLoadingEl) {
        sitesLoadingEl.style.display = "none";
      }
    }
  }

  displaySites(sites, stats) {
    const sitesGrid = document.getElementById("sitesGrid");
    if (!sitesGrid) {
      console.error("sitesGrid element not found");
      return;
    }
    
    sitesGrid.innerHTML = "";

    if (sites.length === 0) {
      sitesGrid.innerHTML = `
        <div class="col-span-full text-center py-12">
          <div class="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <i class="fas fa-info-circle text-gray-400 text-2xl"></i>
          </div>
          <h3 class="text-lg font-medium text-gray-900 mb-2">No sites scraped yet</h3>
          <p class="text-gray-600">Start by scraping a website to see it here!</p>
        </div>
      `;
      return;
    }

    sites.forEach((site) => {
      const siteStats = stats[site] || {};
      const siteCard = document.createElement("div");
      siteCard.className = "bg-white rounded-xl shadow-sm border border-gray-200 p-6 card-hover";
      siteCard.innerHTML = `
        <div class="flex items-center justify-between mb-4">
          <div class="flex items-center space-x-3">
            <div class="w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
              <i class="fas fa-globe text-white"></i>
            </div>
            <div>
              <h3 class="text-lg font-semibold text-gray-900">${site}</h3>
              <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                <span class="w-2 h-2 bg-green-400 rounded-full mr-1"></span>
                Active
              </span>
            </div>
          </div>
        </div>
        
        <div class="grid grid-cols-2 gap-4 mb-4">
          <div class="text-center">
            <div class="text-2xl font-bold text-blue-600">${siteStats.total_pages || 0}</div>
            <div class="text-sm text-gray-600">Pages</div>
          </div>
          <div class="text-center">
            <div class="text-2xl font-bold text-purple-600">${siteStats.total_chunks || 0}</div>
            <div class="text-sm text-gray-600">Chunks</div>
          </div>
        </div>
        
        <div class="flex space-x-2">
          <button class="flex-1 bg-blue-50 text-blue-700 px-3 py-2 rounded-lg text-sm font-medium hover:bg-blue-100 transition-colors" onclick="ui.viewSiteInfo('${site}')">
            <i class="fas fa-info mr-1"></i> Info
          </button>
          <button class="flex-1 bg-red-50 text-red-700 px-3 py-2 rounded-lg text-sm font-medium hover:bg-red-100 transition-colors" onclick="ui.deleteSite('${site}')">
            <i class="fas fa-trash mr-1"></i> Delete
          </button>
        </div>
      `;
      sitesGrid.appendChild(siteCard);
    });
  }

  updateQuerySiteOptions() {
    const select = document.getElementById("querySite");
    if (!select) {
      console.error("querySite select element not found");
      return;
    }
    
    select.innerHTML = '<option value="">All Sites</option>';

    this.sites.forEach((site) => {
      const option = document.createElement("option");
      option.value = site;
      option.textContent = site;
      select.appendChild(option);
    });
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

      if (response.ok) {
        this.showToast("success", "Site Deleted", `${siteName} has been deleted successfully`);
        this.loadSites(); // Refresh the sites list
      } else {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
    } catch (error) {
      console.error("Error deleting site:", error);
      this.showToast("error", "Delete Failed", "Failed to delete site");
    }
  }

  showSiteInfoModal(siteName, info) {
    // Create a modern modal for site info
    const modal = document.createElement("div");
    modal.className = "fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4";
    modal.innerHTML = `
      <div class="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div class="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 rounded-t-xl">
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-3">
              <div class="w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                <i class="fas fa-globe text-white"></i>
              </div>
              <div>
                <h3 class="text-xl font-semibold text-gray-900">Site Information</h3>
                <p class="text-sm text-gray-600">${siteName}</p>
              </div>
            </div>
            <button class="text-gray-400 hover:text-gray-600 p-2 hover:bg-gray-100 rounded-lg transition-colors" onclick="this.closest('.fixed').remove()">
              <i class="fas fa-times text-lg"></i>
            </button>
          </div>
        </div>
        
        <div class="p-6 space-y-6">
          <!-- Site Overview -->
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div class="bg-blue-50 rounded-lg p-4 border border-blue-200">
              <div class="flex items-center">
                <div class="p-2 bg-blue-100 rounded-lg mr-3">
                  <i class="fas fa-file-alt text-blue-600"></i>
                </div>
                <div>
                  <p class="text-sm font-medium text-blue-700">Total Pages</p>
                  <p class="text-2xl font-bold text-blue-900">${info.total_pages || 0}</p>
                </div>
              </div>
            </div>
            
            <div class="bg-green-50 rounded-lg p-4 border border-green-200">
              <div class="flex items-center">
                <div class="p-2 bg-green-100 rounded-lg mr-3">
                  <i class="fas fa-cube text-green-600"></i>
                </div>
                <div>
                  <p class="text-sm font-medium text-green-700">Vector Chunks</p>
                  <p class="text-2xl font-bold text-green-900">${info.total_chunks || 0}</p>
                </div>
              </div>
            </div>
            
            <div class="bg-purple-50 rounded-lg p-4 border border-purple-200">
              <div class="flex items-center">
                <div class="p-2 bg-purple-100 rounded-lg mr-3">
                  <i class="fas fa-clock text-purple-600"></i>
                </div>
                <div>
                  <p class="text-sm font-medium text-purple-700">Status</p>
                  <p class="text-lg font-semibold text-purple-900">${info.status || 'Active'}</p>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Site Details -->
          <div class="bg-gray-50 rounded-lg p-4">
            <h4 class="text-lg font-semibold text-gray-900 mb-3">Site Details</h4>
            <div class="space-y-3">
              <div class="flex justify-between items-center py-2 border-b border-gray-200">
                <span class="text-sm font-medium text-gray-600">Site Name:</span>
                <span class="text-sm text-gray-900">${info.name || siteName}</span>
              </div>
              <div class="flex justify-between items-center py-2 border-b border-gray-200">
                <span class="text-sm font-medium text-gray-600">URL:</span>
                <a href="${info.url || `https://${siteName}`}" target="_blank" class="text-sm text-blue-600 hover:text-blue-800 underline">
                  ${info.url || `https://${siteName}`}
                </a>
              </div>
              <div class="flex justify-between items-center py-2 border-b border-gray-200">
                <span class="text-sm font-medium text-gray-600">Last Updated:</span>
                <span class="text-sm text-gray-900">${new Date(info.last_updated * 1000).toLocaleString()}</span>
              </div>
              <div class="flex justify-between items-center py-2">
                <span class="text-sm font-medium text-gray-600">Data Size:</span>
                <span class="text-sm text-gray-900">${Math.round((info.total_chunks || 0) * 0.5)} KB</span>
              </div>
            </div>
          </div>
          
          <!-- Actions -->
          <div class="flex space-x-3">
            <button class="flex-1 bg-blue-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-blue-700 transition-colors">
              <i class="fas fa-eye mr-2"></i>View Pages
            </button>
            <button class="flex-1 bg-red-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-red-700 transition-colors" onclick="ui.deleteSite('${siteName}'); this.closest('.fixed').remove();">
              <i class="fas fa-trash mr-2"></i>Delete Site
            </button>
          </div>
        </div>
      </div>
    `;
    
    document.body.appendChild(modal);
    
    // Close modal when clicking outside
    modal.addEventListener("click", (e) => {
      if (e.target === modal) {
        modal.remove();
      }
    });
    
    // Close modal with Escape key
    document.addEventListener("keydown", function closeModal(e) {
      if (e.key === "Escape") {
        modal.remove();
        document.removeEventListener("keydown", closeModal);
      }
    });
  }

  // Analytics
  async loadAnalytics() {
    try {
      const response = await fetch(`${this.apiBaseUrl}/analytics`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      this.updateAnalytics(data);
    } catch (error) {
      console.error("Error loading analytics:", error);
      this.showToast("error", "Load Error", "Failed to load analytics data");
    }
  }

  updateAnalytics(data) {
    const totalSites = document.getElementById("totalSites");
    const totalPagesAnalytics = document.getElementById("totalPagesAnalytics");
    const totalProducts = document.getElementById("totalProducts");
    const totalChunks = document.getElementById("totalChunks");

    if (totalSites) totalSites.textContent = data.total_sites || 0;
    if (totalPagesAnalytics) totalPagesAnalytics.textContent = data.total_pages || 0;
    if (totalProducts) totalProducts.textContent = data.total_products || 0;
    if (totalChunks) totalChunks.textContent = data.total_chunks || 0;
  }

  // Utility Functions
  showLoadingOverlay() {
    const overlay = document.getElementById("loadingOverlay");
    if (overlay) overlay.style.display = "flex";
  }

  hideLoadingOverlay() {
    const overlay = document.getElementById("loadingOverlay");
    if (overlay) overlay.style.display = "none";
  }

  formatDuration(startTime, endTime) {
    if (!startTime || !endTime) return "0s";
    const duration = endTime - startTime;
    if (duration < 60) {
      return `${Math.round(duration)}s`;
    } else {
      const minutes = Math.floor(duration / 60);
      const seconds = Math.round(duration % 60);
      return `${minutes}m ${seconds}s`;
    }
  }

  showToast(type, title, message) {
    const container = document.getElementById("toastContainer");
    if (!container) return;

    const toast = document.createElement("div");
    const bgColor = type === "success" ? "bg-green-500" : type === "error" ? "bg-red-500" : type === "info" ? "bg-blue-500" : "bg-yellow-500";
    const icon = type === "success" ? "check-circle" : type === "error" ? "exclamation-circle" : type === "info" ? "info-circle" : "exclamation-triangle";
    
    toast.className = `${bgColor} text-white px-6 py-4 rounded-lg shadow-lg max-w-sm transform transition-all duration-300 translate-x-full`;
    toast.innerHTML = `
      <div class="flex items-center">
        <i class="fas fa-${icon} mr-3"></i>
        <div>
          <div class="font-medium">${title}</div>
          <div class="text-sm opacity-90">${message}</div>
        </div>
        <button class="ml-4 text-white hover:text-gray-200" onclick="this.parentElement.parentElement.remove()">
          <i class="fas fa-times"></i>
        </button>
      </div>
    `;
    
    container.appendChild(toast);
    
    // Animate in
    setTimeout(() => {
      toast.classList.remove("translate-x-full");
    }, 100);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
      toast.classList.add("translate-x-full");
      setTimeout(() => {
        if (toast.parentElement) {
          toast.remove();
        }
      }, 300);
    }, 5000);
  }

  // Get API base URL based on environment
  getApiBaseUrl() {
    // Check if we're running in Docker or have a specific API URL
    const urlParams = new URLSearchParams(window.location.search);
    const apiUrl = urlParams.get('api_url');
    
    if (apiUrl) {
      return apiUrl;
    }
    
    // Check if we're running on a different port (Docker scenario)
    const currentHost = window.location.hostname;
    const currentPort = window.location.port;
    
    // If UI is running on port 8080, API is likely on port 8000
    if (currentPort === '8080') {
      return `http://${currentHost}:8000`;
    }
    
    // For demo UI, default to localhost:8000
    // This works for both local development and Docker
    return 'http://localhost:8000';
  }
}

// Initialize the UI when the page loads
const ui = new ScraperUI();
