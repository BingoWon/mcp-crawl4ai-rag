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

    // 搜索状态
    this.searchState = {
      pages: "",
      chunks: ""
    };

    // 倒计时相关
    this.countdownTimer = null;
    this.refreshTimer = null;
    this.remainingTime = this.refreshInterval / 1000; // 剩余秒数

    this.init();
  }

  init() {
    // 初始化倒计时显示
    this.updateCountdownDisplay();

    // 设置搜索事件监听器
    this.setupSearchListeners();

    // 加载初始数据
    this.loadData();

    // 启动自动刷新和倒计时
    this.startAutoRefresh();
  }

  async loadData() {
    await Promise.all([this.loadPages(), this.loadChunks(), this.loadStats()]);
  }

  async loadPages() {
    try {
      const searchParam = this.searchState.pages ? `&search=${encodeURIComponent(this.searchState.pages)}` : '';
      const response = await fetch(
        `${this.apiBase}/pages?sort=created_at&order=desc${searchParam}`
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
      const searchParam = this.searchState.chunks ? `&search=${encodeURIComponent(this.searchState.chunks)}` : '';
      const response = await fetch(
        `${this.apiBase}/chunks?page=${currentPage}&size=${this.pagination.chunks.size}${searchParam}`
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
          this.lastData.stats = result.data;

          // 更新全局统计显示
          this.updateGlobalStats(result.data);
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

  updateGlobalStats(stats) {
    // 更新页面顶部的全局统计
    document.getElementById("total-pages").textContent = `总数: ${stats.pages_count}`;
    document.getElementById("content-pages").textContent = `有内容: ${stats.pages_with_content} (${stats.content_percentage}%)`;
    document.getElementById("processed-pages").textContent = `已处理: ${stats.pages_processed} (${stats.processing_percentage}%)`;
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
    const processedStatus = page.processed_at
      ? `<span style="color: #28a745;">✓ ${this.formatDate(page.processed_at)}</span>`
      : `<span style="color: #6c757d;">未处理</span>`;

    return `
      <tr class="clickable-row" onclick="showContentModal('${page.id}', '${this.escapeJsString(page.full_url || page.url)}', '${this.escapeJsString(page.full_content)}', 'page')">
        <td class="url-cell" title="${page.full_url || page.url}">${page.url}</td>
        <td class="content-cell" title="${page.content}">${page.content}</td>
        <td>${this.formatDate(page.created_at)}</td>
        <td>${processedStatus}</td>
      </tr>
    `;
  }

  createChunkRow(chunk) {
    // 解析 content 字段中的 JSON 数据用于表格显示
    let displayContent = chunk.content;

    try {
      const parsedContent = JSON.parse(chunk.content);
      // 显示 JSON 的简化版本，包含 context 和 content 信息
      const contextInfo = parsedContent.context ? `Context: ${parsedContent.context.substring(0, 50)}...` : 'No context';
      const contentInfo = parsedContent.content ? `Content: ${parsedContent.content.substring(0, 100)}...` : 'No content';
      displayContent = `${contextInfo} | ${contentInfo}`;
    } catch (e) {
      // 如果解析失败，显示原始内容的前150字符
      displayContent = chunk.content.length > 150 ? chunk.content.substring(0, 150) + '...' : chunk.content;
    }

    return `
      <tr class="clickable-row"
          data-chunk-id="${chunk.id}"
          data-chunk-url="${this.escapeHtml(chunk.full_url || chunk.url)}"
          onclick="window.dbViewer.handleChunkRowClick(this)">
        <td class="url-cell" title="${chunk.full_url || chunk.url}">${chunk.url}</td>
        <td class="content-cell" title="点击查看完整内容">${displayContent}</td>
      </tr>
    `;
  }

  startAutoRefresh() {
    // 启动倒计时显示
    this.startCountdown();

    // 启动自动刷新
    this.refreshTimer = setInterval(() => {
      this.loadData();
      this.resetCountdown();
    }, this.refreshInterval);
  }

  startCountdown() {
    this.remainingTime = this.refreshInterval / 1000;
    this.updateCountdownDisplay();

    this.countdownTimer = setInterval(() => {
      this.remainingTime--;
      this.updateCountdownDisplay();

      if (this.remainingTime <= 0) {
        this.remainingTime = this.refreshInterval / 1000;
      }
    }, 1000);
  }

  resetCountdown() {
    this.remainingTime = this.refreshInterval / 1000;
    this.updateCountdownDisplay();
  }

  updateCountdownDisplay() {
    const timerElement = document.getElementById('countdown-timer');
    if (timerElement) {
      timerElement.textContent = `${this.remainingTime}s`;

      // 添加视觉效果：最后1秒时变红
      if (this.remainingTime <= 1) {
        timerElement.style.background = '#dc3545';
        timerElement.style.color = 'white';
      } else {
        timerElement.style.background = '#e9ecef';
        timerElement.style.color = '#495057';
      }
    }
  }

  // 立即刷新功能
  refreshNow() {
    // 清除现有定时器
    if (this.refreshTimer) {
      clearInterval(this.refreshTimer);
    }
    if (this.countdownTimer) {
      clearInterval(this.countdownTimer);
    }

    // 立即加载数据
    this.loadData();

    // 重新启动自动刷新
    this.startAutoRefresh();
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

  // 设置搜索事件监听器
  setupSearchListeners() {
    // Pages 搜索
    const pagesSearchInput = document.getElementById('pages-search');
    const pagesSearchBtn = document.getElementById('pages-search-btn');
    const pagesSearchClear = document.getElementById('pages-search-clear');

    if (pagesSearchInput) {
      // 输入事件 - 实时搜索
      pagesSearchInput.addEventListener('input', (e) => {
        this.searchState.pages = e.target.value.trim();
        this.debounceSearch('pages');
      });

      // 回车键搜索
      pagesSearchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
          this.performSearch('pages');
        }
      });
    }

    if (pagesSearchBtn) {
      pagesSearchBtn.addEventListener('click', () => {
        this.searchState.pages = pagesSearchInput.value.trim();
        this.performSearch('pages');
      });
    }

    if (pagesSearchClear) {
      pagesSearchClear.addEventListener('click', () => {
        this.clearSearch('pages');
      });
    }

    // Chunks 搜索
    const chunksSearchInput = document.getElementById('chunks-search');
    const chunksSearchBtn = document.getElementById('chunks-search-btn');
    const chunksSearchClear = document.getElementById('chunks-search-clear');

    if (chunksSearchInput) {
      // 输入事件 - 实时搜索
      chunksSearchInput.addEventListener('input', (e) => {
        this.searchState.chunks = e.target.value.trim();
        this.debounceSearch('chunks');
      });

      // 回车键搜索
      chunksSearchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
          this.performSearch('chunks');
        }
      });
    }

    if (chunksSearchBtn) {
      chunksSearchBtn.addEventListener('click', () => {
        this.searchState.chunks = chunksSearchInput.value.trim();
        this.performSearch('chunks');
      });
    }

    if (chunksSearchClear) {
      chunksSearchClear.addEventListener('click', () => {
        this.clearSearch('chunks');
      });
    }
  }

  // 防抖搜索
  debounceSearch(type) {
    if (this.searchTimers && this.searchTimers[type]) {
      clearTimeout(this.searchTimers[type]);
    }

    if (!this.searchTimers) {
      this.searchTimers = {};
    }

    this.searchTimers[type] = setTimeout(() => {
      this.performSearch(type);
    }, 500); // 500ms 防抖
  }

  // 执行搜索
  async performSearch(type) {
    if (type === 'pages') {
      await this.loadPages();
    } else if (type === 'chunks') {
      // 重置到第一页
      this.pagination.chunks.page = 1;
      await this.loadChunks(1);
    }
  }

  // 清除搜索
  clearSearch(type) {
    const input = document.getElementById(`${type}-search`);
    if (input) {
      input.value = '';
      this.searchState[type] = '';
      this.performSearch(type);
    }
  }

  // 处理 chunk 行点击事件
  handleChunkRowClick(row) {
    const id = row.getAttribute('data-chunk-id');
    const url = row.getAttribute('data-chunk-url');

    console.log('=== Chunk 点击调试信息 ===');
    console.log('点击的 chunk ID:', id);
    console.log('点击的 chunk URL:', url);
    console.log('lastData.chunks 存在:', !!this.lastData.chunks);

    if (this.lastData.chunks) {
      console.log('chunks 是数组:', Array.isArray(this.lastData.chunks));

      if (Array.isArray(this.lastData.chunks)) {
        console.log('chunks 数组长度:', this.lastData.chunks.length);
        console.log('前3个 chunk ID:', this.lastData.chunks.slice(0, 3).map(c => c.id));
      } else {
        console.log('chunks 数据结构:', Object.keys(this.lastData.chunks));
        console.log('chunks.data 存在:', !!this.lastData.chunks.data);

        if (this.lastData.chunks.data) {
          console.log('chunks.data 长度:', this.lastData.chunks.data.length);
          console.log('前3个 chunk ID:', this.lastData.chunks.data.slice(0, 3).map(c => c.id));
        }
      }
    }

    // 从内存中的数据获取完整内容
    const chunk = this.findChunkById(id);
    console.log('找到的 chunk:', !!chunk);

    if (chunk) {
      console.log('chunk.full_content 长度:', chunk.full_content ? chunk.full_content.length : 0);
      showContentModal(id, url, chunk.full_content, 'chunk');
    } else {
      console.log('未找到 chunk，显示错误信息');
      showContentModal(id, url, '调试信息：无法获取完整内容。请查看控制台调试输出。', 'chunk');
    }
  }

  // 根据 ID 查找 chunk 数据
  findChunkById(id) {
    console.log('查找 chunk ID:', id);

    // 检查数据结构
    if (this.lastData.chunks) {
      console.log('lastData.chunks 类型:', Array.isArray(this.lastData.chunks) ? 'Array' : 'Object');

      // 如果是数组，直接查找
      if (Array.isArray(this.lastData.chunks)) {
        console.log('从数组中查找，数组长度:', this.lastData.chunks.length);
        const found = this.lastData.chunks.find(chunk => {
          console.log('比较:', chunk.id, '===', id, '结果:', chunk.id === id);
          return chunk.id === id;
        });
        console.log('查找结果:', !!found);
        return found;
      }

      // 如果是对象且有 data 属性
      if (this.lastData.chunks.data && Array.isArray(this.lastData.chunks.data)) {
        console.log('从 data 属性中查找，数组长度:', this.lastData.chunks.data.length);
        const found = this.lastData.chunks.data.find(chunk => {
          console.log('比较:', chunk.id, '===', id, '结果:', chunk.id === id);
          return chunk.id === id;
        });
        console.log('查找结果:', !!found);
        return found;
      }
    }

    console.log('lastData.chunks 不存在或格式不正确');
    return null;
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
function showContentModal(_id, url, content, type) {
  console.log('=== showContentModal 调试信息 ===');
  console.log('ID:', _id);
  console.log('URL:', url);
  console.log('Content 类型:', typeof content);
  console.log('Content 长度:', content ? content.length : 0);
  console.log('Type:', type);

  const modal = document.getElementById("content-modal");
  const modalTitle = document.getElementById("modal-title");
  const modalUrl = document.getElementById("modal-url");
  const modalContent = document.getElementById("modal-content");

  // 设置标题
  modalTitle.textContent = type === "page" ? "页面详情" : "Chunk详情";

  // 设置URL
  modalUrl.textContent = url;

  // 解析并设置内容
  let displayContent = content || "无内容";

  // 如果是 chunk 类型，尝试格式化 JSON 显示
  if (type === "chunk" && content) {
    console.log('处理 chunk 内容...');
    console.log('原始内容长度:', content.length);

    try {
      // 尝试解析 JSON 并格式化显示
      const parsedContent = JSON.parse(content);
      console.log('JSON 解析成功');
      console.log('JSON 结构:', Object.keys(parsedContent));

      // 格式化 JSON 为易读格式
      displayContent = JSON.stringify(parsedContent, null, 2);
      console.log('格式化后内容长度:', displayContent.length);
    } catch (e) {
      console.log('JSON 解析失败，显示原始内容:', e.message);
      // 如果解析失败，显示原始内容
      displayContent = content;
    }
  }

  console.log('最终显示内容长度:', displayContent.length);

  // 使用 pre 标签保持格式
  modalContent.innerHTML = `<pre style="white-space: pre-wrap; word-wrap: break-word;">${displayContent}</pre>`;

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
  window.dbViewer = dbViewer; // 暴露到全局

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
