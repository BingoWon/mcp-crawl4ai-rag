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

    // 分页配置
    this.pagination = {
      pages: { page: 1, size: 100, total: 0, pages: 0 },
      chunks: { page: 1, size: 50, total: 0, pages: 0 },
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
      const response = await fetch(
        `${this.apiBase}/pages?sort=created_at&order=desc`
      );
      const result = await response.json();

      if (result.success) {
        // 简化后的数据结构 - 固定100条数据，无分页
        this.pagination.pages.total = result.count || 0;

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

        // 更新页面级统计信息
        if (result.stats) {
          this.updatePageStats(result.stats);
        }

        // 无需分页UI - 固定显示100条数据
      } else {
        this.showError("pages", result.error || "未知错误");
      }
    } catch (error) {
      this.showError("pages", error.message || "网络错误");
    }
  }

  async loadChunks(page = null) {
    try {
      const currentPage = page || this.pagination.chunks.page;
      const response = await fetch(
        `${this.apiBase}/chunks?page=${currentPage}&size=${this.pagination.chunks.size}`
      );
      const result = await response.json();

      if (result.success) {
        // 更新分页信息，确保类型正确
        this.pagination.chunks.page = parseInt(result.pagination.page) || 1;
        this.pagination.chunks.size = parseInt(result.pagination.size) || 50;
        this.pagination.chunks.total = parseInt(result.pagination.total) || 0;
        this.pagination.chunks.pages = parseInt(result.pagination.pages) || 0;

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

        // 更新分页UI
        this.updatePagination("chunks");
      } else {
        this.showError("chunks", result.error || "未知错误");
      }
    } catch (error) {
      this.showError("chunks", error.message || "网络错误");
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

          // 更新panel count显示
          this.updatePanelCount("pages", result.data.pages_count);
          this.updatePanelCount("chunks", result.data.chunks_count);
        }
      }
    } catch (error) {
      console.error("Failed to load stats:", error);
    }
  }

  renderPages(pages) {
    if (pages.length === 0) {
      this.showEmpty("pages");
      return;
    }

    // 直接渲染所有行
    const tbody = document.getElementById("pages-tbody");
    tbody.innerHTML = pages.map((page) => this.createPageRow(page)).join("");

    this.showTable("pages");
  }

  renderChunks(chunks) {
    if (chunks.length === 0) {
      this.showEmpty("chunks");
      return;
    }

    // 直接渲染所有行
    const tbody = document.getElementById("chunks-tbody");
    tbody.innerHTML = chunks
      .map((chunk) => this.createChunkRow(chunk))
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

  updatePanelCount(type, count, data = null) {
    if (type === "pages" && this.lastData.stats) {
      // 分别更新三个独立的统计区域
      const stats = this.lastData.stats;
      document.getElementById(
        "pages-total-count"
      ).textContent = `总数: ${count}`;
      document.getElementById(
        "pages-content-count"
      ).textContent = `有内容: ${stats.pages_with_content} (${stats.content_percentage}%)`;
      document.getElementById(
        "pages-avg-crawl"
      ).textContent = `平均爬取次数: ${stats.avg_crawl_count}`;
      document.getElementById(
        "pages-avg-process"
      ).textContent = `平均处理次数: ${stats.avg_process_count}`;
      document.getElementById(
        "pages-anomalous"
      ).textContent = `内容长度异常: ${stats.anomalous_pages}`;
    } else if (type === "chunks") {
      // chunks保持原有显示方式
      const panelCountElement = document.getElementById(`${type}-panel-count`);
      if (panelCountElement) {
        panelCountElement.textContent = count;
      }
    }
  }

  updatePageStats(stats) {
    // 更新页面级统计信息
    if (stats.avg_crawl_interval !== null) {
      document.getElementById(
        "pages-avg-interval"
      ).textContent = `近${stats.data_count}次爬取平均耗时: ${stats.avg_crawl_interval}秒`;
    } else {
      document.getElementById(
        "pages-avg-interval"
      ).textContent = `近${stats.data_count}次爬取平均耗时: --`;
    }
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

  escapeHtml(text) {
    if (!text) return "";
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  escapeJsString(text) {
    if (!text) return "";
    return text
      .replace(/\\/g, "\\\\") // 转义反斜杠
      .replace(/'/g, "\\'") // 转义单引号
      .replace(/"/g, '\\"') // 转义双引号
      .replace(/\n/g, "\\n") // 转义换行符
      .replace(/\r/g, "\\r") // 转义回车符
      .replace(/\t/g, "\\t"); // 转义制表符
  }

  createPageRow(page) {
    return `
      <tr>
        <td class="url-cell" title="${page.full_url || page.url}"
            onclick="showContentModal('${page.id}', '${this.escapeJsString(
      page.full_url || page.url
    )}', '${this.escapeJsString(page.full_content)}', 'page')">${page.url}</td>
        <td class="content-cell" title="${page.content}">${page.content}</td>
        <td><span class="crawl-count">${page.crawl_count}</span></td>
        <td><span class="process-count">${page.process_count}</span></td>
        <td>${this.formatDate(page.created_at)}</td>
        <td>${this.formatDate(page.last_crawled_at)}</td>
      </tr>
    `;
  }

  createChunkRow(chunk) {
    return `
      <tr>
        <td class="url-cell" title="${chunk.full_url || chunk.url}"
            onclick="showContentModal('${chunk.id}', '${this.escapeJsString(
      chunk.full_url || chunk.url
    )}', '${this.escapeJsString(
      chunk.full_content
    )}', 'chunk', '${this.escapeJsString(
      chunk.embedding_info
    )}', '${this.escapeJsString(chunk.raw_embedding)}')">${chunk.url}</td>
        <td class="content-cell" title="${chunk.content}">${chunk.content}</td>
        <td class="embedding-info">${chunk.embedding_info}</td>
        <td>${this.formatDate(chunk.created_at)}</td>
      </tr>
    `;
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

  // 更新分页UI
  updatePagination(type) {
    const container = document.getElementById(`${type}-pagination`);

    // Pages表无分页功能，直接隐藏
    if (type === "pages") {
      if (container) container.style.display = "none";
      return;
    }

    // 其他表保持原有分页逻辑
    const pagination = this.pagination[type];
    if (!container || pagination.pages <= 1) {
      if (container) container.style.display = "none";
      return;
    }

    container.style.display = "flex";
    container.innerHTML = this.generatePaginationHTML(type, pagination);
  }

  // 生成分页HTML
  generatePaginationHTML(type, pagination) {
    const { page, pages } = pagination;
    let html = "";

    // 上一页
    html += `<button onclick="viewer.changePage('${type}', ${page - 1})"
             ${page <= 1 ? "disabled" : ""}>上一页</button>`;

    // 页码
    const startPage = Math.max(1, page - 2);
    const endPage = Math.min(pages, page + 2);

    if (startPage > 1) {
      html += `<button onclick="viewer.changePage('${type}', 1)">1</button>`;
      if (startPage > 2) html += `<span>...</span>`;
    }

    for (let i = startPage; i <= endPage; i++) {
      html += `<button onclick="viewer.changePage('${type}', ${i})"
               ${i === page ? 'class="active"' : ""}>${i}</button>`;
    }

    if (endPage < pages) {
      if (endPage < pages - 1) html += `<span>...</span>`;
      html += `<button onclick="viewer.changePage('${type}', ${pages})">${pages}</button>`;
    }

    // 下一页
    html += `<button onclick="viewer.changePage('${type}', ${page + 1})"
             ${page >= pages ? "disabled" : ""}>下一页</button>`;

    return html;
  }

  // 切换页面
  async changePage(type, newPage) {
    if (newPage < 1 || newPage > this.pagination[type].pages) return;

    this.pagination[type].page = newPage;

    if (type === "chunks") {
      await this.loadChunks(newPage);
    }
    // Pages表无分页功能，固定显示100条数据
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

// 模态框相关函数
function showContentModal(
  id,
  url,
  content,
  type,
  embeddingInfo = "",
  rawEmbedding = ""
) {
  const modal = document.getElementById("content-modal");
  const modalTitle = document.getElementById("modal-title");
  const modalUrl = document.getElementById("modal-url");
  const modalContent = document.getElementById("modal-content");
  const modalEmbeddingSection = document.getElementById(
    "modal-embedding-section"
  );
  const modalEmbeddingInfo = document.getElementById("modal-embedding-info");
  const modalEmbeddingRaw = document.getElementById("modal-embedding-raw");

  // 设置标题
  modalTitle.textContent = type === "page" ? "页面详情" : "Chunk详情";

  // 设置URL
  modalUrl.textContent = url;

  // 设置内容
  modalContent.textContent = content || "无内容";

  // 设置embedding信息（仅对chunks显示）
  if (type === "chunk" && embeddingInfo) {
    modalEmbeddingSection.style.display = "block";
    modalEmbeddingInfo.textContent = embeddingInfo;
    modalEmbeddingRaw.textContent = rawEmbedding || "无原始数据";
  } else {
    modalEmbeddingSection.style.display = "none";
  }

  // 显示模态框
  modal.style.display = "flex";
}

function closeModal() {
  document.getElementById("content-modal").style.display = "none";
}

// 点击模态框外部关闭
document.addEventListener("click", (e) => {
  const modal = document.getElementById("content-modal");
  if (e.target === modal) {
    closeModal();
  }
});

// ESC键关闭模态框
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    closeModal();
  }
});

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
