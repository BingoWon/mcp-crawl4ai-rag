// 极简JavaScript - 数据获取和动态刷新

class DatabaseViewer {
  constructor() {
    this.apiBase = "http://localhost:8001/api";
    this.refreshInterval = 3000; // 3秒刷新
    this.lastData = {
      pages: null,
      chunks: null,
      stats: null,
    };
    this.init();
  }

  init() {
    this.loadData();
    this.startAutoRefresh();
  }

  async loadData() {
    await Promise.all([this.loadPages(), this.loadChunks(), this.loadStats()]);
    this.updateLastUpdateTime();
  }

  async loadPages() {
    try {
      const response = await fetch(`${this.apiBase}/pages`);
      const result = await response.json();

      if (result.success) {
        // 智能刷新：只有数据变化时才更新DOM
        if (!this.isDataEqual(this.lastData.pages, result.data)) {
          this.renderPages(result.data);
          this.lastData.pages = result.data;
        } else {
          // 数据没变化，但要确保显示正确的状态
          if (result.data.length === 0) {
            this.showEmpty("pages");
          } else {
            this.showTable("pages");
          }
        }
        this.updatePanelCount("pages", result.count);
      } else {
        this.showError("pages", result.error);
      }
    } catch (error) {
      this.showError("pages", error.message);
    }
  }

  async loadChunks() {
    try {
      const response = await fetch(`${this.apiBase}/chunks`);
      const result = await response.json();

      if (result.success) {
        // 智能刷新：只有数据变化时才更新DOM
        if (!this.isDataEqual(this.lastData.chunks, result.data)) {
          this.renderChunks(result.data);
          this.lastData.chunks = result.data;
        } else {
          // 数据没变化，但要确保显示正确的状态
          if (result.data.length === 0) {
            this.showEmpty("chunks");
          } else {
            this.showTable("chunks");
          }
        }
        this.updatePanelCount("chunks", result.count);
      } else {
        this.showError("chunks", result.error);
      }
    } catch (error) {
      this.showError("chunks", error.message);
    }
  }

  async loadStats() {
    try {
      const response = await fetch(`${this.apiBase}/stats`);
      const result = await response.json();

      if (result.success) {
        // 智能刷新：只有统计数据变化时才更新
        if (!this.isDataEqual(this.lastData.stats, result.data)) {
          document.getElementById(
            "pages-count"
          ).textContent = `Pages: ${result.data.pages_count}`;
          document.getElementById(
            "chunks-count"
          ).textContent = `Chunks: ${result.data.chunks_count}`;
          this.lastData.stats = result.data;
        }
      }
    } catch (error) {
      console.error("Failed to load stats:", error);
    }
  }

  renderPages(pages) {
    const tbody = document.getElementById("pages-tbody");

    if (pages.length === 0) {
      this.showEmpty("pages");
      return;
    }

    tbody.innerHTML = pages
      .map(
        (page) => `
            <tr>
                <td title="${page.url}">${page.url}</td>
                <td title="${page.content}">${page.content}</td>
                <td>${this.formatDate(page.created_at)}</td>
                <td>${this.formatDate(page.updated_at)}</td>
            </tr>
        `
      )
      .join("");

    this.showTable("pages");
  }

  renderChunks(chunks) {
    const tbody = document.getElementById("chunks-tbody");

    if (chunks.length === 0) {
      this.showEmpty("chunks");
      return;
    }

    tbody.innerHTML = chunks
      .map(
        (chunk) => `
            <tr>
                <td title="${chunk.url}">${chunk.url}</td>
                <td title="${chunk.content}">${chunk.content}</td>
                <td class="embedding-${chunk.has_embedding.toLowerCase()}">${
          chunk.has_embedding
        }</td>
                <td>${this.formatDate(chunk.created_at)}</td>
            </tr>
        `
      )
      .join("");

    this.showTable("chunks");
  }

  showError(type, message) {
    document.getElementById(`${type}-error`).style.display = "flex";
    document.getElementById(`${type}-error`).textContent = `Error: ${message}`;
    document.getElementById(`${type}-table`).style.display = "none";
    document.getElementById(`${type}-empty`).style.display = "none";
  }

  showTable(type) {
    document.getElementById(`${type}-error`).style.display = "none";
    document.getElementById(`${type}-table`).style.display = "block";
    document.getElementById(`${type}-empty`).style.display = "none";
  }

  showEmpty(type) {
    document.getElementById(`${type}-error`).style.display = "none";
    document.getElementById(`${type}-table`).style.display = "none";
    document.getElementById(`${type}-empty`).style.display = "flex";
  }

  updatePanelCount(type, count) {
    document.getElementById(`${type}-panel-count`).textContent = count;
  }

  updateLastUpdateTime() {
    const now = new Date();
    document.getElementById(
      "last-update"
    ).textContent = `Last Update: ${now.toLocaleTimeString()}`;
  }

  formatDate(dateString) {
    if (!dateString) return "--";
    const date = new Date(dateString);
    return date.toLocaleString("zh-CN", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  }

  startAutoRefresh() {
    setInterval(() => {
      this.loadData();
    }, this.refreshInterval);
  }

  // 智能刷新：数据比较函数
  isDataEqual(oldData, newData) {
    if (!oldData && !newData) return true;
    if (!oldData || !newData) return false;
    return JSON.stringify(oldData) === JSON.stringify(newData);
  }

  // 清除缓存，强制刷新
  clearCache() {
    this.lastData = {
      pages: null,
      chunks: null,
      stats: null,
    };
  }
}

// 全局变量
let dbViewer;

// 页面加载完成后启动
document.addEventListener("DOMContentLoaded", () => {
  dbViewer = new DatabaseViewer();

  // 添加快捷键：按F5清除缓存并刷新
  document.addEventListener("keydown", (e) => {
    if (e.key === "F5") {
      e.preventDefault();
      dbViewer.clearCache();
      dbViewer.loadData();
      console.log("缓存已清除，数据已刷新");
    }
  });
});
