//config
const supabaseUrl = "https://jqzlmzbvaesczarqptye.supabase.co";
const supabaseKey = "sb_publishable_wXUovp36dvd_VwdX-U8ecg_P-OrGwEb";
const supabaseClient = window.supabase.createClient(supabaseUrl, supabaseKey);
const backend_url = "https://vonika-git-110018515227.us-central1.run.app/api";
function clearName(name) {
  return name
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D")
    .replace(/[^a-zA-Z0-9.\-_]/g, "_")
    .toLowerCase();
}

// Toast Notifications System
function showToast(message, type = 'success') {
    const toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        console.warn("Toast container not found. Message:", message);
        return;
    }

    const toast = document.createElement('div');
    toast.className = `custom-toast ${type}`;
    
    let iconClass = 'fa-solid fa-circle-check';
    if (type === 'error') iconClass = 'fa-solid fa-circle-exclamation';
    else if (type === 'warning') iconClass = 'fa-solid fa-triangle-exclamation';
    else if (type === 'info') iconClass = 'fa-solid fa-circle-info';

    toast.innerHTML = `
        <div style="display: flex; align-items: center; flex: 1;">
            <i class="${iconClass}"></i>
            <span>${message}</span>
        </div>
        <div class="close-toast" onclick="this.parentElement.remove()">
            <i class="fa-solid fa-xmark" style="margin:0; font-size: 1rem;"></i>
        </div>
    `;

    toastContainer.appendChild(toast);

    // Auto close after 5 seconds
    setTimeout(() => {
        if (toast.parentElement) {
            toast.style.animation = 'fadeOutRight 0.35s forwards';
            setTimeout(() => {
                if (toast.parentElement) toast.remove();
            }, 350);
        }
    }, 2303);
}

// Global Error Handlers
window.addEventListener('error', function(event) {
    showToast(`Lỗi hệ thống: ${event.message}`, 'error');
});

window.addEventListener('unhandledrejection', function(event) {
    let msg = event.reason;
    if (event.reason && event.reason.message) {
        msg = event.reason.message;
    }
    showToast(`Lỗi: ${msg}`, 'error');
});

// Intercept console.error
const originalConsoleError = console.error;
console.error = function(...args) {
    originalConsoleError.apply(console, args);
    
    let msg = args.map(a => {
        if (a instanceof Error) return a.message;
        if (typeof a === 'object') {
            try { return JSON.stringify(a); } catch(e) { return 'Object error'; }
        }
        return a;
    }).join(' ');

    if (msg.includes("Failed to fetch") || msg.toLowerCase().includes("lỗi")) {
        showToast(msg, 'error');
    } else {
        showToast(`Lỗi: ${msg}`, 'error');
    }
};

// Layout
const themeToggleBtn = document.getElementById("theme-toggle-btn");
const themeIcon = themeToggleBtn ? themeToggleBtn.querySelector("i") : null;

const savedTheme = localStorage.getItem("theme");
if (savedTheme === "dark") {
  document.body.classList.add("dark-theme");
  if (themeIcon) {
    themeIcon.classList.replace("fa-moon", "fa-sun");
  }
}

if (themeToggleBtn && themeIcon) {
  themeToggleBtn.addEventListener("click", () => {
    document.body.classList.toggle("dark-theme");

    if (document.body.classList.contains("dark-theme")) {
      localStorage.setItem("theme", "dark");
      themeIcon.classList.replace("fa-moon", "fa-sun");
    } else {
      localStorage.setItem("theme", "light");
      themeIcon.classList.replace("fa-sun", "fa-moon");
    }
  });
}

const settingBtn = document.querySelector("#settings-btn");
function openSettingModal() {
  const settingModal = document.getElementById("settings-modal");
  if (settingModal) settingModal.classList.add("active");
}

function closeSettingModal() {
  const settingModal = document.getElementById("settings-modal");
  if (settingModal) settingModal.classList.remove("active");
}

settingBtn.addEventListener("click", () => {
  openSettingModal();
});

const closeSettingModalBtn = document.getElementById(
  "close-settings-modal-btn",
);
if (closeSettingModalBtn) {
  closeSettingModalBtn.addEventListener("click", closeSettingModal);
}

const settingModalOverlay = document.getElementById(
  "settings-modal",
);
if (settingModalOverlay) {
  settingModalOverlay.addEventListener("click", (e) => {
    if (e.target === settingModalOverlay) {
      closeSettingModal();
    }
  });
}




// Resizer

const resizerLeft = document.querySelector("#resizer-left");
const sidebarLeft = document.querySelector("#sidebar-left");
const resizerRight = document.querySelector("#resizer-right");
const sidebarRight = document.querySelector("#sidebar-right");
const toggleLeftBtn = document.querySelector("#toggle-left-btn");
const toggleRightBtn = document.querySelector("#toggle-right-btn");

let isResizeLeft = false;
resizerLeft.addEventListener("mousedown", () => {
  isResizeLeft = true;
  document.body.classList.add("is-resizing");
  resizerLeft.classList.add("active");
});

let isResizeRight = false;
resizerRight.addEventListener("mousedown", () => {
  isResizeRight = true;
  document.body.classList.add("is-resizing");
  resizerRight.classList.add("active");
});

document.addEventListener("mousemove", (e) => {
  if (isResizeLeft) {
    let newWidth = e.clientX;
    if (newWidth < 150) newWidth = 150;
    if (newWidth > 600) newWidth = 600;
    sidebarLeft.style.width = `${newWidth}px`;
  }

  if (isResizeRight) {
    let newWidth = window.innerWidth - e.clientX;
    if (newWidth < 150) newWidth = 150;
    if (newWidth > 600) newWidth = 600;
    sidebarRight.style.width = `${newWidth}px`;
  }
});

document.addEventListener("mouseup", () => {
  if (isResizeLeft || isResizeRight) {
    isResizeLeft = isResizeRight = false;
    document.body.classList.remove("is-resizing");
    resizerLeft.classList.remove("active");
    resizerRight.classList.remove("active");
  }
});

if (toggleLeftBtn) {
  toggleLeftBtn.addEventListener("click", () => {
    sidebarLeft.classList.toggle("is-collapsed");
    if (resizerLeft) resizerLeft.classList.toggle("hidden");
  });
}

if (toggleRightBtn) {
  toggleRightBtn.addEventListener("click", () => {
    sidebarRight.classList.toggle("is-collapsed");
    if (resizerRight) resizerRight.classList.toggle("hidden");
  });
}

// Chat Interface
const chatInput = document.querySelector("#chat-input");
const chatArea = document.querySelector(".chat-area");
const chatBox = document.querySelector("#chat-box");
const chatTitle = document.querySelector("#chat-title");
const sendBtn = document.querySelector("#send-btn");
const newChatBtn = document.getElementById("new-chat-btn");

function scrollToBottom(smooth = false, delay = 0) {
  if (chatBox) {
    if (delay > 0) {
      setTimeout(() => {
        if (smooth) chatBox.scrollTo({ top: chatBox.scrollHeight, behavior: 'smooth' });
        else chatBox.scrollTop = chatBox.scrollHeight;
      }, delay);
    } else {
        if (smooth) chatBox.scrollTo({ top: chatBox.scrollHeight, behavior: 'smooth' });
        else chatBox.scrollTop = chatBox.scrollHeight;
    }
  }
}

function parseAndRenderAIMessage(messageEl, rawContent, shouldStream = false) {
    let answer = rawContent;
    let suggestions = [];
    let sources = [];

    // Parse Sources
    const sourceIndex = answer.indexOf("---SOURCES---");
    if (sourceIndex !== -1) {
        const sourceText = answer.substring(sourceIndex + "---SOURCES---".length).trim();
        answer = answer.substring(0, sourceIndex).trim();
        try {
            sources = JSON.parse(sourceText);
        } catch (e) {}
    }

    // Parse Suggestions
    const sugIndex = answer.indexOf("---SUGGESTIONS---");
    if (sugIndex !== -1) {
        const sugText = answer.substring(sugIndex + "---SUGGESTIONS---".length).trim();
        answer = answer.substring(0, sugIndex).trim();
        suggestions = sugText.split('\n').map(l => l.replace(/^\d+\.\s*/, '').trim()).filter(l => l);
    }

    const contentContainer = messageEl.querySelector(".content");

    const footerDiv = document.createElement("div");
    footerDiv.className = "message-footer";
    footerDiv.style.cssText = "display: flex; justify-content: space-between; align-items: flex-end; margin-top: 15px; padding-top: 12px; border-top: 1px dashed var(--border-color, #e2e8f0); gap: 16px;";

    // Left: Sources
    const sourcesDiv = document.createElement("div");
    sourcesDiv.className = "sources";
    sourcesDiv.style.flex = "1";

    const showSources = document.getElementById("show-sources-toggle")?.checked ?? true;
    if (showSources && sources?.length) {
      let sourcesHtml = '<div style="font-size: 0.85rem; color: #64748b; margin-bottom: 8px; font-weight: 500;"> Nguồn tham khảo:</div>';
      sourcesHtml += '<div style="display: flex; flex-wrap: wrap; gap: 8px;">';
      sources.forEach(sourceName => {
        const fileObj = Array.from(corpusFiles.values()).find(f => f.file_name === sourceName);
        const href = fileObj ? fileObj.file_url : '#';
        const target = fileObj ? 'target="_blank"' : '';
        const cursor = fileObj ? 'cursor: pointer;' : 'cursor: default;';
        
        sourcesHtml += `
          <a href="${href}" ${target} class="source-chip" title="${sourceName}" style="display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; background-color: rgba(59, 130, 246, 0.1); color: #3b82f6; border: 1px solid rgba(59, 130, 246, 0.2); border-radius: 20px; font-size: 0.8rem; text-decoration: none; transition: all 0.2s ease; font-weight: 500; max-width: 100%; box-sizing: border-box; ${cursor}" onmouseover="this.style.backgroundColor='rgba(59, 130, 246, 0.2)'" onmouseout="this.style.backgroundColor='rgba(59, 130, 246, 0.1)'">
            <i class="fa-regular fa-file-lines" style="flex-shrink: 0;"></i> 
            <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 250px;">${sourceName}</span>
          </a>
        `;
      });
      sourcesHtml += '</div>';
      sourcesDiv.innerHTML = sourcesHtml;
    }

    // Right: Action Buttons (Copy, Download)
    const actionsDiv = document.createElement("div");
    actionsDiv.className = "action-buttons";
    actionsDiv.style.cssText = "display: flex; gap: 6px; align-items: center; flex-shrink: 0;";

    // Copy Button
    const copyBtn = document.createElement("button");
    copyBtn.title = "Copy nội dung";
    copyBtn.innerHTML = '<i class="fa-regular fa-copy"></i>';
    copyBtn.style.cssText = "background: none; border: 1px solid transparent; color: #94a3b8; cursor: pointer; font-size: 1rem; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; border-radius: 6px; transition: all 0.2s; opacity: 0.7;";
    copyBtn.onmouseover = () => { copyBtn.style.opacity = "1"; copyBtn.style.background = "var(--color-bg-hover)"; copyBtn.style.borderColor = "var(--color-border)"; };
    copyBtn.onmouseout = () => { copyBtn.style.opacity = "0.7"; copyBtn.style.background = "none"; copyBtn.style.borderColor = "transparent"; };
    copyBtn.onclick = () => {
        navigator.clipboard.writeText(answer).then(() => {
            copyBtn.innerHTML = '<i class="fa-solid fa-check" style="color: #10b981;"></i>';
            setTimeout(() => { copyBtn.innerHTML = '<i class="fa-regular fa-copy"></i>'; }, 2000);
        });
        showToast("Đã sao chép nội dung", "success");
    };

    // Download Button
    const exportBtn = document.createElement("button");
    exportBtn.title = "Tải Markdown";
    exportBtn.innerHTML = '<i class="fa-solid fa-download"></i>';
    exportBtn.style.cssText = "background: none; border: 1px solid transparent; color: #94a3b8; cursor: pointer; font-size: 1rem; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; border-radius: 6px; transition: all 0.2s; opacity: 0.7;";
    exportBtn.onmouseover = () => { exportBtn.style.opacity = "1"; exportBtn.style.background = "var(--color-bg-hover)"; exportBtn.style.borderColor = "var(--color-border)"; };
    exportBtn.onmouseout = () => { exportBtn.style.opacity = "0.7"; exportBtn.style.background = "none"; exportBtn.style.borderColor = "transparent"; };
    exportBtn.onclick = () => {
        const prevEl = messageEl.previousElementSibling;
        let userQuestion = "Không xác định";
        if (prevEl && prevEl.classList.contains("message-users")) {
            userQuestion = prevEl.innerText.trim();
        }
        
        let mdContent = `# User\n${userQuestion}\n\n# AI\n${answer}\n`;
        if (sources && sources.length > 0) {
            mdContent += `\n## Nguồn tham khảo\n`;
            sources.forEach(src => mdContent += `- ${src}\n`);
        }
        
        const blob = new Blob([mdContent], { type: "text/markdown;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        const safeName = userQuestion
            .replace(/[\\/:*?"<>|]/g, '')
            .trim()
            .split(/\s+/)
            .slice(0, 7)
            .join(" ");
        a.download = `${safeName}.md`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    actionsDiv.appendChild(copyBtn);
    actionsDiv.appendChild(exportBtn);

    footerDiv.appendChild(sourcesDiv);
    footerDiv.appendChild(actionsDiv);
    
    let suggestionsDiv = null;
    if (suggestions.length > 0) {
      suggestionsDiv = document.createElement("div");
      suggestionsDiv.className = "suggestions-container";
      suggestions.forEach(s => {
        const btn = document.createElement("button");
        btn.className = "suggestion-btn";
        btn.innerText = s;
        btn.onclick = () => {
          document.getElementById("chat-input").value = s;
          document.getElementById("send-btn").click();
        };
        suggestionsDiv.appendChild(btn);
      });
    }

    if (shouldStream) {
        contentContainer.innerHTML = `<div class="markdown-body"></div>`;
        const mdBody = contentContainer.querySelector('.markdown-body');
        let currentIndex = 0;
        const totalDuration = 800;
        const intervalMs = 35;
        const totalSteps = totalDuration / intervalMs;
        const charsPerStep = Math.max(5, Math.ceil(answer.length / totalSteps));

        const interval = setInterval(() => {
            currentIndex += charsPerStep;
            if (currentIndex >= answer.length) {
                currentIndex = answer.length;
                clearInterval(interval);
                mdBody.innerHTML = window.marked ? marked.parse(answer) : answer;
                contentContainer.appendChild(footerDiv);
                if (suggestionsDiv) messageEl.appendChild(suggestionsDiv);
                scrollToBottom(true, 50);
            } else {
                const currentText = answer.substring(0, currentIndex);
                mdBody.innerHTML = (window.marked ? marked.parse(currentText) : currentText) + '<span class="rag-typing-cursor"></span>';
                scrollToBottom(false, 0);
            }
        }, intervalMs);
    } else {
        const parsedAnswer = window.marked ? marked.parse(answer) : answer;
        contentContainer.innerHTML = `<div class="markdown-body">${parsedAnswer}</div>`;
        contentContainer.appendChild(footerDiv);
        if (suggestionsDiv) messageEl.appendChild(suggestionsDiv);
    }
}

async function loadMessages() {
  const { data, error } = await supabaseClient
    .from("chat_messages")
    .select("*")
    .order("id", { ascending: true });

  if (error) console.error("Error loading messages:", error);
  if (data) {
    data.forEach((message) => {
      if (message.role === "user") {
        const userEl = document.createElement("div");
        userEl.className = "message-users";
        userEl.innerHTML = `<div class="content">${message.content}</div>`;
        chatArea.appendChild(userEl);
        chatTitle.value = message.chat_title || "Chưa có tên";
        currentChatId = message.id;
      } else {
        const aiEl = document.createElement("div");
        aiEl.className = "message-ai";
        aiEl.innerHTML = `<div class="content"></div>`;
        chatArea.appendChild(aiEl);
        parseAndRenderAIMessage(aiEl, message.content);
        currentChatId = message.id;
      }
    });
    scrollToBottom(false, 100);
  }
}

chatInput.addEventListener("input", function () {
  this.style.height = "auto";
  this.style.height = this.scrollHeight + "px";
});

let currentChatId = "";

async function sendMessages(text) {
  if (text === "") return;

  const currentTitle = chatTitle.value;
  const titleToSave =
    currentTitle === "Chưa có tên" || currentTitle === ""
      ? text.trim().split(/\s+/).slice(0, 10).join(" ")
      : currentTitle;

  chatInput.value = "";
  chatInput.style.height = "auto";
  const userEl = document.createElement("div");
  userEl.className = "message-users";
  userEl.innerHTML = `<div class="content">${text}</div>`;
  chatArea.appendChild(userEl);
  scrollToBottom(true, 50);

  sendBtn.disabled = true;
  chatInput.disabled = true;

  try {
    const { data: insertedData, error: dbError } = await supabaseClient
      .from("chat_messages")
      .insert([{ role: "user", content: text, chat_title: titleToSave }])
      .select();

    if (dbError) throw dbError;
    if (insertedData?.length > 0) currentChatId = insertedData[0].id;
    chatTitle.value = titleToSave;

    const loadingEl = document.createElement("div");
    loadingEl.className = "message-ai";
    loadingEl.innerHTML = `<div class="content">
      <div class="typing-indicator">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>
    </div>`;
    chatArea.appendChild(loadingEl);
    scrollToBottom(true, 50);

    const fileIds = Array.from(selectedAttachFiles);
    let { answer, sources, tokens } = await fetchAIResponse(text, fileIds, currentChatId);

    if (tokens) {
      showToast(`Đã sử dụng ${tokens.toLocaleString()} tokens`, 'success');
    }

    let contentToSave = answer;
    if (sources && sources.length > 0) {
        contentToSave += "\n\n---SOURCES---\n" + JSON.stringify(sources);
    }

    parseAndRenderAIMessage(loadingEl, contentToSave, true);

    await supabaseClient
      .from("chat_messages")
      .insert([{ role: "assistant", content: contentToSave, chat_title: titleToSave }]);
  } catch (error) {
    console.error("Error:", error);
  } finally {
    sendBtn.disabled = false;
    chatInput.disabled = false;
  }
}

chatInput.addEventListener("keydown", async function (e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    const text = this.value.trim();
    sendMessages(text);
  }
});

sendBtn.addEventListener("click", async () => {
  const text = chatInput.value.trim();
  sendMessages(text);
});

async function newChatFunction() {
  chatTitle.value = "Chưa có tên";
  chatArea.innerHTML = `
        <div class="message-ai">
            <div class="content">Xin chào! Tôi là Vonika, hãy đặt câu hỏi bên dưới, tôi sẽ trả lời bạn trong giây lát.</div>
        </div>
    `;
  const text = chatInput.value.trim();
  if (text !== "") {
    chatInput.value = "";
    chatInput.style.height = "auto";
  }
  try {
    const { error: dbError } = await supabaseClient
      .from("chat_messages")
      .delete()
      .not("id", "is", null);
    if (dbError) throw dbError;
  } catch (error) {
    console.error("Error:", error);
  }
}

newChatBtn.addEventListener("click", () => {
  newChatFunction();
});

chatTitle.addEventListener("keydown", async (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    chatTitle.blur();

    if (!currentChatId) return;

    try {
      const { error: dbError } = await supabaseClient
        .from("chat_messages")
        .update({ chat_title: chatTitle.value })
        .eq("id", currentChatId);
      if (dbError) throw dbError;
    } catch (error) {
      console.error("Error:", error);
    }
  }
});

// File Management
const uploadBtn = document.querySelector("#upload-btn");
const uploadFolderBtn = document.querySelector("#upload-folder-btn");
const fileList = document.querySelector("#file-list");

const openModalBtn = document.querySelector("#open-modal-btn");
const closeModalBtn = document.querySelector("#close-modal-btn");
const uploadModal = document.querySelector("#upload-modal");
const modalUploadBox = document.querySelector(".modal-upload-box");

const pasteTextBtn = document.querySelector("#paste-text");
const pasteTextModal = document.querySelector("#paste-text-modal");
const closePasteTextModalBtn = document.querySelector("#close-paste-modal-btn");
const saveTextBtn = document.querySelector("#save-text-btn");
const pasteInput = document.querySelector("#paste-input");
const pasteCharCount = document.querySelector("#paste-char-count");

// Modal Upload
if (openModalBtn) {
  openModalBtn.addEventListener("click", () => {
    uploadModal.classList.add("active");
  });
}

if (closeModalBtn) {
  closeModalBtn.addEventListener("click", () => {
    uploadModal.classList.remove("active");
  });
}

if (uploadModal) {
  uploadModal.addEventListener("click", (e) => {
    if (e.target === uploadModal) {
      uploadModal.classList.remove("active");
    }
  });
}

if (modalUploadBox) {
  modalUploadBox.addEventListener("dragover", (e) => {
    e.preventDefault();
    modalUploadBox.classList.add("drag-over");
  });

  modalUploadBox.addEventListener("dragleave", (e) => {
    e.preventDefault();
    modalUploadBox.classList.remove("drag-over");
  });

  modalUploadBox.addEventListener("drop", (e) => {
    e.preventDefault();
    modalUploadBox.classList.remove("drag-over");

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const files = Array.from(e.dataTransfer.files);
      processFilesUpload(files);
    }
  });
}

// Modal Paste Text
if (saveTextBtn) {
  saveTextBtn.addEventListener("click", () => {
    const textInput = document.querySelector("#paste-input");
    const text = textInput.textContent.trim();
    if (text !== "") {
      uploadPasteFile(text);
      textInput.textContent = "";
      pasteCharCount.textContent = "0 ký tự";
      pasteTextModal.classList.remove("active");
    }
  });
}

if (closePasteTextModalBtn) {
  closePasteTextModalBtn.addEventListener("click", () => {
    pasteTextModal.classList.remove("active");
  });
}

if (pasteTextModal) {
  pasteTextModal.addEventListener("click", (e) => {
    if (e.target === pasteTextModal) {
      pasteTextModal.classList.remove("active");
    }
  });
}

if (pasteTextBtn) {
  pasteTextBtn.addEventListener("click", () => {
    if (uploadModal) uploadModal.classList.remove("active");
    if (pasteTextModal) pasteTextModal.classList.add("active");
  });
}

if (pasteInput) {
  pasteInput.addEventListener("input", () => {
    const textLength = pasteInput.textContent.length;
    pasteCharCount.textContent = `${textLength} ký tự`;
  });
}

// Market Report Modal
const marketReportModal = document.getElementById('market-report-modal');
const openMarketReportBtn = document.getElementById('ext-market-report-btn');
const closeMarketReportModalBtn = document.getElementById('close-market-report-modal-btn');

if (openMarketReportBtn && marketReportModal) {
    openMarketReportBtn.addEventListener('click', () => {
        marketReportModal.classList.add('active');
    });
}
if (closeMarketReportModalBtn && marketReportModal) {
    closeMarketReportModalBtn.addEventListener('click', () => {
        marketReportModal.classList.remove('active');
    });
}
if (marketReportModal) {
    marketReportModal.addEventListener('click', (e) => {
        if (e.target === marketReportModal) {
            marketReportModal.classList.remove('active');
        }
    });
}
const triggerReportBtn = document.getElementById('trigger-report-btn');
if (triggerReportBtn) {
    triggerReportBtn.addEventListener('click', async () => {
        const btnOriginalText = triggerReportBtn.innerHTML;
        triggerReportBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang gửi lệnh...';
        triggerReportBtn.disabled = true;

        try {
            const response = await fetch(`${backend_url}/trigger-github-action`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (response.ok) {
                showToast("Báo cáo đang được tạo trên GitHub.", "success");
            } else {
                const errorData = await response.json().catch(() => ({}));
                const errorMsg = errorData.detail || response.statusText;
                showToast(`Lỗi: ${errorMsg}`, "error");
            }
        } catch (error) {
            console.error("Trigger Action Error:", error);
            showToast("Không thể kết nối đến Backend Server", "error");
        } finally {
            triggerReportBtn.innerHTML = btnOriginalText;
            triggerReportBtn.disabled = false;
        }
    });
}

// File Action Toolbar
const actionToolbar = document.createElement("div");
actionToolbar.className = "action-toolbar";

const selectAllBtn = document.createElement("button");
selectAllBtn.className = "upload-btn";
selectAllBtn.id = "select-all-btn";
selectAllBtn.innerHTML = '<i class="fa-solid fa-check-double"></i> Chọn hết';

const batchDeleteBtn = document.createElement("button");
batchDeleteBtn.className = "upload-btn";
batchDeleteBtn.id = "batch-delete-btn";
batchDeleteBtn.innerHTML = '<i class="fa-solid fa-trash"></i> Xóa (0)';

actionToolbar.appendChild(selectAllBtn);
actionToolbar.appendChild(batchDeleteBtn);
fileList.parentNode.insertBefore(actionToolbar, fileList);

const selectedFiles = new Map();
const corpusFiles = new Map();
const selectedAttachFiles = new Set();
let isAllSelected = false;

function updateBatchDeleteBtn() {
  const readyChips = document.querySelectorAll(".file-chip.is-ready");
  const totalReady = readyChips.length;
  if (totalReady > 0) {
    actionToolbar.style.display = "flex";
  } else {
    actionToolbar.style.display = "none";
  }

  if (selectedFiles.size > 0) {
    batchDeleteBtn.style.display = "block";
    batchDeleteBtn.innerHTML = `<i class="fa-solid fa-trash"></i> Xóa (${selectedFiles.size})`;
  } else {
    batchDeleteBtn.style.display = "none";
  }

  if (totalReady > 0 && selectedFiles.size === totalReady) {
    isAllSelected = true;
    selectAllBtn.innerHTML = '<i class="fa-solid fa-xmark"></i> Bỏ chọn';
  } else {
    isAllSelected = false;
    selectAllBtn.innerHTML =
      '<i class="fa-solid fa-check-double"></i> Chọn hết';
  }
}

selectAllBtn.addEventListener("click", () => {
  const readyChips = document.querySelectorAll(".file-chip.is-ready");
  if (readyChips.length === 0) return;

  const targetSelectState = selectedFiles.size < readyChips.length;

  readyChips.forEach((chip) => {
    const isCurrentlySelected = chip.classList.contains("is-selected");

    if (targetSelectState && !isCurrentlySelected) {
      chip.click();
    } else if (!targetSelectState && isCurrentlySelected) {
      chip.click();
    }
  });
});

batchDeleteBtn.addEventListener("click", async () => {
  batchDeleteBtn.innerHTML = "<i class=\"fa-solid fa-spinner fa-spin\"></i> Đang xóa...";
  batchDeleteBtn.style.cursor = "wait";
  batchDeleteBtn.disabled = true;
  selectAllBtn.disabled = true;
  selectAllBtn.style.cursor = "wait";

  for (const [id, fileInfo] of selectedFiles.entries()) {
    try {
      await supabaseClient.from("uploaded_files").delete().eq("id", id);
      await supabaseClient.storage
        .from("chat-files")
        .remove([fileInfo.storageName]);
      fileInfo.domElement.remove();
      selectedFiles.delete(id);
      
      corpusFiles.delete(String(id));
      selectedAttachFiles.delete(String(id));
    } catch (error) {
      console.error("Lỗi khi xóa file ID:", id, error);
    }
  }
  
  updateSelectedFilesCount();
  checkStorageLimit();

  batchDeleteBtn.disabled = false;
  selectAllBtn.disabled = false;
  batchDeleteBtn.style.cursor = "pointer";
  selectAllBtn.style.cursor = "pointer";
  updateBatchDeleteBtn();
});

function setupFileInteraction(fileItem, fileData, storageName) {
  fileItem.classList.add("is-ready");

  const statusEl = fileItem.querySelector(".file-chip-status");
  if (statusEl) {
    statusEl.className = "file-chip-status status-success";
    statusEl.innerHTML =
      '<span style="color: #10B981;" title="Tải lên thành công">✔</span>';
  }

  fileItem.addEventListener("click", () => {
    const isSelected = fileItem.classList.toggle("is-selected");

    if (isSelected) {
      selectedFiles.set(fileData.id, {
        storageName: storageName,
        domElement: fileItem,
        url: fileData.file_url,
      });
    } else {
      selectedFiles.delete(fileData.id);
    }
    updateBatchDeleteBtn();
  });

  updateBatchDeleteBtn();
}

async function checkStorageLimit(newFileSize = 0) {
  try {
    const { data: usersData, error: usersError } = await supabaseClient.storage.from("chat-files").list("users_files", { limit: 10000 });
    const { data: marketData, error: marketError } = await supabaseClient.storage.from("chat-files").list("market_reports", { limit: 10000 });
    
    if (usersError) throw usersError;
    if (marketError) throw marketError;
    
    let currentTotalSize = 0;
    if (usersData) currentTotalSize += usersData.reduce((sum, f) => sum + (f.metadata?.size || 0), 0);
    if (marketData) currentTotalSize += marketData.reduce((sum, f) => sum + (f.metadata?.size || 0), 0);
    
    const ONE_GB = 1024 * 1024 * 1024;
    
    // Luôn luôn cập nhật UI với tổng dung lượng mới nhất
    const sizeCountEl = document.getElementById("file-size-count");
    if (sizeCountEl) {
        let sizeInMB = (currentTotalSize / (1024 * 1024)).toFixed(2);
        sizeCountEl.innerText = `${sizeInMB}/1024MB`;
    }

    if (currentTotalSize + newFileSize > ONE_GB) {
      return false;
    }
    return true;
  } catch (e) {
    console.error("Lỗi kiểm tra dung lượng storage:", e);
    return true; 
  }
}

async function processFilesUpload(files) {
  const allowMimeTypes = [
    ".pdf",
    ".txt",
    ".docx",
    ".json",
    ".xlsx",
    ".csv",
    ".tsv",
    ".md",
  ];

  const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB

  const validFiles = files.filter((file) => {
    const fileName = file.name.toLowerCase();
    const isValidType = allowMimeTypes.some((type) => fileName.endsWith(type));
    if (!isValidType) return false;
    
    if (file.size > MAX_FILE_SIZE) {
      showToast(`File "${file.name}" vượt quá giới hạn 50MB`, 'error');
      return false;
    }
    return true;
  });

  if (validFiles.length === 0) {
    if (!files.some(f => f.size > MAX_FILE_SIZE)) {
        showToast("Vui lòng chọn file có định dạng hợp lệ: .pdf, .txt, .docx, .json, .xlsx, .csv, .tsv, .md", 'error');
    }
    return;
  }

  const totalNewSize = validFiles.reduce((sum, f) => sum + f.size, 0);
  const isWithinLimit = await checkStorageLimit(totalNewSize);
    
  if (!isWithinLimit) {
      showToast("Kho lưu trữ đã đầy (Giới hạn 1GB). Vui lòng xóa bớt file cũ!", 'error');
      return;
  }

  
  
  for (const file of validFiles) {
    const fileItem = document.createElement("div");
    fileItem.className = "file-chip";
    const fileName = file.name;
    const uniqueFileName = `${Date.now()}_${clearName(file.name)}`;

    fileItem.innerHTML = `
            <div class="file-chip-icon">
                <svg viewBox="0 0 24 24"><path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/></svg>
            </div>
            <div class="file-chip-name" title="${fileName}">${fileName}</div>
            <div class="file-chip-status status-loading"><i class="fa-solid fa-spinner fa-spin"></i></div>
        `;
    const usersContainer = document.getElementById('users-files-container');
    const usersSection = document.getElementById('users-files-section');
    if (usersContainer) usersContainer.appendChild(fileItem);
    if (usersSection) usersSection.style.display = 'block';
    
    const emptyMsg = document.getElementById('empty-message');
    if (emptyMsg) emptyMsg.style.display = 'none';

    try {
      const { error: storageError } = await supabaseClient.storage
        .from("chat-files")
        .upload(`users_files/${uniqueFileName}`, file);
      if (storageError) throw storageError;

      const { data: publicUrlData } = supabaseClient.storage
        .from("chat-files")
        .getPublicUrl(`users_files/${uniqueFileName}`);
      const fileUrl = publicUrlData.publicUrl;

      const { data: dbData, error: dbError } = await supabaseClient
        .from("uploaded_files")
        .insert([{ file_name: fileName, file_url: fileUrl }])
        .select();
      if (dbError) throw dbError;

      try {
        const processRes = await fetch(`${backend_url}/process-file`,{
          method: "POST",
          headers: {'content-type': 'application/json'},
          body: JSON.stringify({file_id: dbData[0].id})
        });
        if (!processRes.ok) {
          throw new Error("Lỗi trích xuất văn bản (Có thể do file PDF là file scan/ảnh)");
        }
      }catch(error){
        console.error("Lỗi xử lý file:", error);
        throw error;
      }

      corpusFiles.set(String(dbData[0].id), dbData[0]);
      selectedAttachFiles.add(String(dbData[0].id));
      updateSelectedFilesCount();
      setupFileInteraction(fileItem, dbData[0], uniqueFileName);
    } catch (error) {
      console.error("Lỗi upload:", fileName, error);
      const statusEl = fileItem.querySelector(".file-chip-status");
      if (statusEl) {
        statusEl.className = "file-chip-status status-error";
        statusEl.innerHTML = '<span style="color: #EF4444;">✖</span>';
        fileItem.style.borderColor = "#EF4444";
      }
    }
  }
  checkStorageLimit();
}

async function uploadPasteFile(text) {
  try {
    const textBlob = new Blob([text]);
    const MAX_FILE_SIZE = 50 * 1024 * 1024;
    
    if (textBlob.size > MAX_FILE_SIZE) {
      showToast("Văn bản dán vào quá lớn (vượt 50MB)", 'error');
      return;
    }

    const isWithinLimit = await checkStorageLimit(textBlob.size);
    if (!isWithinLimit) {
      showToast("Storage đã đầy, vui lòng xóa file cũ", 'error');
      return;
    }

    let snippet = text.substring(0, 20).trim();
    if (!snippet) snippet = "Pasted_Text";

    const safeSnippet = clearName(snippet);
    const fileName = `${safeSnippet}.txt`;
    const uniqueFileName = `${Date.now()}_${safeSnippet}.txt`;

    const file = new File([text], fileName, { type: "text/plain" });

    const fileItem = document.createElement("div");
    fileItem.className = "file-chip";
    fileItem.innerHTML = `
            <div class="file-chip-icon">
                <svg viewBox="0 0 24 24"><path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/></svg>
            </div>
            <div class="file-chip-name" title="${fileName}">${fileName}</div>
            <div class="file-chip-status status-loading"><i class="fa-solid fa-spinner fa-spin"></i></div>
        `;
    const usersContainer = document.getElementById('users-files-container');
    const usersSection = document.getElementById('users-files-section');
    if (usersContainer) usersContainer.appendChild(fileItem);
    if (usersSection) usersSection.style.display = 'block';
    
    const emptyMsg = document.getElementById('empty-message');
    if (emptyMsg) emptyMsg.style.display = 'none';

    const { error: storageError } = await supabaseClient.storage
      .from("chat-files")
      .upload(`users_files/${uniqueFileName}`, file);

    if (storageError) throw storageError;

    const { data: publicUrlData } = supabaseClient.storage
      .from("chat-files")
      .getPublicUrl(`users_files/${uniqueFileName}`);
    const fileUrl = publicUrlData.publicUrl;

    const { data: dbData, error: dbError } = await supabaseClient
      .from("uploaded_files")
      .insert([{ file_name: fileName, file_url: fileUrl }])
      .select();

    if (dbError) throw dbError;
    
    try {
      await fetch(`${backend_url}/process-file`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file_id: dbData[0].id })
      });
    } catch (processError) {
      console.error("Lỗi khi xử lý file text trên RAG server:", processError);
    }

    corpusFiles.set(String(dbData[0].id), dbData[0]);
    selectedAttachFiles.add(String(dbData[0].id));
    updateSelectedFilesCount();
    setupFileInteraction(fileItem, dbData[0], uniqueFileName);
  } catch (error) {
    console.error("Lỗi khi upload văn bản pasted:", error);
    const statusEl = fileItem.querySelector(".file-chip-status");
    if (statusEl) {
      statusEl.className = "file-chip-status status-error";
      statusEl.innerHTML = '<span style="color: #EF4444;">✖</span>';
      fileItem.style.borderColor = "#EF4444";
    }
  }
  checkStorageLimit();
}

uploadBtn.addEventListener("click", () => {
  const fileInput = document.createElement("input");
  fileInput.type = "file";
  fileInput.multiple = true;
  fileInput.accept = ".pdf,.txt,.docx,.json,.xlsx,.csv,.tsv,.md";

  fileInput.addEventListener("change", (e) => {
    const files = Array.from(e.target.files);
    if (files.length > 0) {
      processFilesUpload(files);
      document.getElementById("close-modal-btn").click();
    }
  });
  fileInput.click();
});

uploadFolderBtn.addEventListener("click", () => {
  const folderInput = document.createElement("input");
  folderInput.type = "file";
  folderInput.webkitdirectory = true;
  folderInput.directory = true;
  folderInput.multiple = true;

  folderInput.addEventListener("change", (e) => {
    const files = Array.from(e.target.files);
    if (files.length > 0) {
      processFilesUpload(files);
      document.getElementById("close-modal-btn").click();
    }
  });
  folderInput.click();
});

async function loadFiles() {
  try {
    const { data: files, error } = await supabaseClient
      .from("uploaded_files")
      .select("*")
      .order("created_at", { ascending: false });

    if (error) throw error;

    if (files && files.length > 0) {
      files.forEach((fileData) => {
        renderFiles(fileData);
        corpusFiles.set(String(fileData.id), fileData);
        selectedAttachFiles.add(String(fileData.id));
      });
      updateSelectedFilesCount();
    }
  } catch (error) {
    console.error("Lỗi tải DB:", error);
  } finally {
    checkStorageLimit();
  }
}

function renderFiles(fileData) {
  const fileItem = document.createElement("div");
  fileItem.className = "file-chip";

  fileItem.innerHTML = `
        <div class="file-chip-icon">
            <svg viewBox="0 0 24 24"><path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/></svg>
        </div>
        <div class="file-chip-name" title="${fileData.file_name}">${fileData.file_name}</div>
        <div class="file-chip-status">
        </div>
    `;
  const emptyMsg = document.getElementById('empty-message');
  if (emptyMsg) emptyMsg.style.display = 'none';

  if (fileData.category === 'market_reports') {
      const mrContainer = document.getElementById('market-reports-container');
      const mrSection = document.getElementById('market-reports-section');
      if (mrContainer) mrContainer.appendChild(fileItem);
      if (mrSection) mrSection.style.display = 'block';
  } else {
      const usersContainer = document.getElementById('users-files-container');
      const usersSection = document.getElementById('users-files-section');
      if (usersContainer) usersContainer.appendChild(fileItem);
      if (usersSection) usersSection.style.display = 'block';
  }

  const fileUrl = fileData.file_url;
  const chatFilesIndex = fileUrl.indexOf("chat-files/");
  let fileNameInStorage = "";
  if (chatFilesIndex !== -1) {
      fileNameInStorage = fileUrl.substring(chatFilesIndex + "chat-files/".length);
  } else {
      fileNameInStorage = fileUrl.substring(fileUrl.lastIndexOf("/") + 1);
  }

  setupFileInteraction(fileItem, fileData, fileNameInStorage);
}

// Selected Files

const attachFileBtn = document.getElementById("attach-file-btn");
const filesCount = document.getElementById("files-count");

function updateSelectedFilesCount() {
  if (filesCount) {
    if (corpusFiles.size === 0) {
      filesCount.innerHTML = "0";
    } else {
      filesCount.innerHTML = `${selectedAttachFiles.size}/${corpusFiles.size}`;
    }
  }
}

function showSelectedFiles() {
  if (corpusFiles.size > 0) {
    let usersHTML = "";
    let marketHTML = "";

    corpusFiles.forEach((fileData) => {
      const fileIdStr = String(fileData.id);
      const isChecked = selectedAttachFiles.has(fileIdStr) ? "checked" : "";
      const liHTML = `
            <li style="padding: 0;">
                <label style="display: flex; align-items: center; gap: 10px; width: 100%; cursor: pointer; padding: 8px 12px; margin: 0;">
                    <input type="checkbox" class="select-checkbox" value="${fileIdStr}" ${isChecked}>
                    <span>${fileData.file_name}</span>
                </label>
            </li>
        `;
      if (fileData.category === 'market_reports') {
          marketHTML += liHTML;
      } else {
          usersHTML += liHTML;
      }
    });

    const fileListContainer = document.getElementById("selected-files-list");
    const allSelected = selectedAttachFiles.size === corpusFiles.size;
    const selectAllChecked = allSelected && corpusFiles.size > 0 ? "checked" : "";

    let finalHTML = `
        <div class="selected-files-header" style="padding-left: 12px; margin-bottom: 15px;">
            <label style="display: flex; align-items: center; gap: 10px; cursor: pointer; width: 100%;">
                <input type="checkbox" id="select-all-checkbox" ${selectAllChecked}>
                <span style="font-weight: 500;">Chọn tất cả</span>
            </label>
        </div>
    `;

    if (usersHTML) {
        finalHTML += `
            <div style="margin-bottom: 20px;">
                <h4 class="category-header">TÀI LIỆU CỦA BẠN</h4>
                <ul class="selected-files" style="margin-bottom: 0;">
                    ${usersHTML}
                </ul>
            </div>
        `;
    }

    if (marketHTML) {
        finalHTML += `
            <div>
                <h4 class="category-header">BÁO CÁO THỊ TRƯỜNG</h4>
                <ul class="selected-files" style="margin-bottom: 0;">
                    ${marketHTML}
                </ul>
            </div>
        `;
    }

    fileListContainer.innerHTML = finalHTML;
    updateSelectedFilesCount();
  } else {
    updateSelectedFilesCount();
    showToast("Chưa có file nào được tải lên. Vui lòng tải file lên trước.", "warning");
  }
}

// sự kiện click checkbox modal chọn file đính kèm
const fileListContainer = document.getElementById("selected-files-list");
if (fileListContainer) {
  fileListContainer.addEventListener("change", (e) => {
    if (e.target.classList.contains("select-checkbox")) {
      const fileId = e.target.value;
      if (e.target.checked) {
        selectedAttachFiles.add(fileId);
      } else {
        selectedAttachFiles.delete(fileId);
      }
      updateSelectedFilesCount();

      const selectAllCb = document.getElementById("select-all-checkbox");
      if (selectAllCb) {
        selectAllCb.checked = selectedAttachFiles.size === corpusFiles.size;
      }
    } else if (e.target.id === "select-all-checkbox") {
      const isChecked = e.target.checked;
      const checkboxes = document.querySelectorAll(".select-checkbox");
      checkboxes.forEach((cb) => {
        cb.checked = isChecked;
        if (isChecked) selectedAttachFiles.add(cb.value);
        else selectedAttachFiles.delete(cb.value);
      });
      updateSelectedFilesCount();
    }
  });
}

function openSelectedFilesModal() {
  const selectedFilesModal = document.getElementById("selected-files-modal");
  if (selectedFilesModal) selectedFilesModal.classList.add("active");
}

function closeSelectedFilesModal() {
  const selectedFilesModal = document.getElementById("selected-files-modal");
  if (selectedFilesModal) selectedFilesModal.classList.remove("active");
}

attachFileBtn.addEventListener("click", () => {
  if (corpusFiles.size > 0) {
    openSelectedFilesModal();
    showSelectedFiles();
  } else {
    showToast("Chưa có file nào được tải lên. Vui lòng tải file lên trước.");
  }
});

const closeSelectedFilesModalBtn = document.getElementById(
  "close-selected-files-modal-btn",
);
if (closeSelectedFilesModalBtn) {
  closeSelectedFilesModalBtn.addEventListener("click", closeSelectedFilesModal);
}

const selectedFilesModalOverlay = document.getElementById(
  "selected-files-modal",
);
if (selectedFilesModalOverlay) {
  selectedFilesModalOverlay.addEventListener("click", (e) => {
    if (e.target === selectedFilesModalOverlay) {
      closeSelectedFilesModal();
    }
  });
}

// Search web
const searchBtn = document.getElementById("search-btn");
const searchInput = document.getElementById("search-input");
const searchResult = document.getElementById("search-results-container");

async function fetchJinaSearch(url) {
  const response = await fetch(`${backend_url}/jina?q=${encodeURIComponent(url)}`);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return await response.text();
}

async function addWebSrcAsFile(item) {
  const res = await fetchJinaSearch(item.link);
  const title = item.title;
  const url = item.link;

  const fileName = `${clearName(title)}.md`;
  const uniqueFileName = `${Date.now()}_${fileName}`;
  const blob = new Blob([res], { type: "text/markdown" });

  const fileItem = document.createElement("div");
  fileItem.className = "file-chip";
  fileItem.innerHTML = `
            <div class="file-chip-icon">
                <svg viewBox="0 0 24 24"><path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/></svg>
            </div>
            <div class="file-chip-name" title="${fileName}">${fileName}</div>
            <div class="file-chip-status status-loading"><i class="fa-solid fa-spinner fa-spin"></i></div>
        `;
  if (fileList) fileList.appendChild(fileItem);

  const { data: uploadData, error: uploadError } = await supabaseClient.storage
    .from("chat-files")
    .upload(uniqueFileName, blob);

  if (uploadError) throw uploadError;

  const { data: publicUrlData } = supabaseClient.storage
    .from("chat-files")
    .getPublicUrl(uniqueFileName);
  const fileUrl = publicUrlData.publicUrl;

  const { data: dbData, error: dbError } = await supabaseClient
    .from("uploaded_files")
    .insert([
      {
        file_name: fileName,
        file_url: fileUrl,
        source_url: url
      },
    ])
    .select();

  if (dbError) throw dbError;
  
  try {
    await fetch(`${backend_url}/process-file`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ file_id: dbData[0].id })
    });
  } catch (processError) {
    console.error("Lỗi khi xử lý file web src trên RAG server:", processError);
  }

  corpusFiles.set(String(dbData[0].id), dbData[0]);
  selectedAttachFiles.add(String(dbData[0].id));
  updateSelectedFilesCount();
  setupFileInteraction(fileItem, dbData[0], uniqueFileName);
  
  checkStorageLimit();
}

if (searchBtn && searchInput) {
  searchBtn.addEventListener("click", async () => {
    const query = searchInput.value.trim();
    if (!query) return;
    searchResult.innerHTML =
      '<p style="text-align:center; color:#5f6368; font-size:14px;"><i class="fa-solid fa-spinner fa-spin"></i> Đang tìm kiếm trên web...</p><br>';


    try {
      const url = `${backend_url}/search?q=${encodeURIComponent(query)}`;
      const requestOptions = {
        method: "GET",
      };
      
      const response = await fetch(url, requestOptions);
      const result = await response.json();
      searchResult.innerHTML = "";

      if (result.organic && result.organic.length > 0) {
        const topResults = result.organic.slice(0, 5);

        topResults.forEach((item) => {
          const div = document.createElement("div");
          div.className = "search-result-item";
          div.innerHTML = `
                        <h4>${item.title}</h4>
                        <p>${item.snippet}</p>
                    `;

          div.addEventListener("click", async () => {
            try {
              document.getElementById("close-modal-btn").click();
              await addWebSrcAsFile(item);
              searchInput.value = "";
              searchResult.innerHTML = "";
            } catch (error) {
              console.error("Lỗi khi thêm nguồn:", error);
              searchResult.innerHTML =
                '<p style="color:red; font-size:14px; text-align:center;">Lỗi kết nối. Vui lòng thử lại.</p>';
            }
          });

          searchResult.appendChild(div);
        });
      } else {
        searchResult.innerHTML =
          '<p style="font-size:14px; text-align:center;">Không tìm thấy kết quả nào.</p>';
      }
    } catch (error) {
      console.error("Lỗi API:", error);
      searchResult.innerHTML =
        '<p style="color:red; font-size:14px; text-align:center;">Lỗi kết nối. Vui lòng thử lại.</p>';
    }
  });

  searchInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
      searchBtn.click();
    }
  });
}

// Fetch API backend-RAG server

async function fetchAIResponse(question, fileIds = [], currentChatId) {
  const model = document.getElementById("model-select")?.value || "gemini-2.5-flash";
  const res = await fetch(`${backend_url}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      query: question,
      file_ids: fileIds.map(id => parseInt(id, 10)),
      chatId: currentChatId,
      model: model
    }),
  });
  if (!res.ok) {
    let errorDetail = res.status;
    try {
      const errJson = await res.json();
      if (errJson.detail) errorDetail = errJson.detail;
    } catch (e) {}
    throw new Error(`Lỗi gọi API RAG: ${errorDetail}`);
  }
  return res.json();
}

// Setup
async function initApp() {
  await loadFiles();
  await loadMessages();
  
  // Save settings
  const modelSelect = document.getElementById("model-select");
  const showSourcesToggle = document.getElementById("show-sources-toggle");

  if (modelSelect) {
    const savedModel = localStorage.getItem("rag_model");
    if (savedModel) modelSelect.value = savedModel;
    modelSelect.addEventListener("change", () => localStorage.setItem("rag_model", modelSelect.value));
  }

  if (showSourcesToggle) {
    const savedShowSources = localStorage.getItem("rag_show_sources");
    if (savedShowSources !== null) showSourcesToggle.checked = savedShowSources === "true";
    showSourcesToggle.addEventListener("change", () => localStorage.setItem("rag_show_sources", showSourcesToggle.checked));
  }
}
initApp();
