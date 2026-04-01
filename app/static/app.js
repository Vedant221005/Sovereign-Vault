const state = {
  token: localStorage.getItem("access_token") || "",
  refreshToken: localStorage.getItem("refresh_token") || "",
  username: localStorage.getItem("username") || "",
  role: localStorage.getItem("role") || "",
};

const statusText = document.getElementById("status-text");
const authView = document.getElementById("auth-view");
const appShell = document.getElementById("app-shell");
const userDashboard = document.getElementById("user-dashboard");
const adminDashboard = document.getElementById("admin-dashboard");
const sessionUser = document.getElementById("session-user");
const sessionRole = document.getElementById("session-role");
const filesBody = document.getElementById("files-body");
const adminFilesBody = document.getElementById("admin-files-body");
const usersBody = document.getElementById("users-body");
const statFiles = document.getElementById("stat-files");
const statUsers = document.getElementById("stat-users");
const showRegisterBtn = document.getElementById("show-register-btn");
const registerForm = document.getElementById("register-form");
const topAdminUsersBtn = document.getElementById("top-admin-users-btn");
const topAdminFilesBtn = document.getElementById("top-admin-files-btn");
const adminUsersSection = document.getElementById("admin-users-section");
const adminFilesSection = document.getElementById("admin-files-section");

let adminActiveTab = "users";

function renderAdminTab() {
  if (!adminUsersSection || !adminFilesSection) {
    return;
  }
  const usersActive = adminActiveTab === "users";
  adminUsersSection.hidden = !usersActive;
  adminFilesSection.hidden = usersActive;
  adminUsersSection.classList.toggle("hidden", !usersActive);
  adminFilesSection.classList.toggle("hidden", usersActive);
  adminUsersSection.style.display = usersActive ? "grid" : "none";
  adminFilesSection.style.display = usersActive ? "none" : "grid";
  if (topAdminUsersBtn) {
    topAdminUsersBtn.classList.toggle("text-secondary", usersActive);
  }
  if (topAdminFilesBtn) {
    topAdminFilesBtn.classList.toggle("text-secondary", !usersActive);
  }
}

const toastWrap = document.createElement("div");
toastWrap.className = "toast-wrap";
document.body.appendChild(toastWrap);

function notify(message, type = "success") {
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;
  toastWrap.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(6px)";
    setTimeout(() => toast.remove(), 150);
  }, 2600);
}

function notifySuccess(message) {
  notify(message, "success");
}

function notifyError(message) {
  notify(message, "error");
}

function setStatus(message, isError = false) {
  if (!statusText) {
    return;
  }
  statusText.textContent = message;
  statusText.className = isError ? "status-warn" : "status-ok";
}

function parseJwt(token) {
  try {
    const payload = token.split(".")[1];
    return JSON.parse(atob(payload));
  } catch (_err) {
    return {};
  }
}

function saveSession(accessToken, refreshToken = "") {
  state.token = accessToken;
  if (refreshToken) {
    state.refreshToken = refreshToken;
    localStorage.setItem("refresh_token", state.refreshToken);
  }
  const payload = parseJwt(accessToken);
  state.username = payload.username || "unknown";
  state.role = payload.role || "user";
  localStorage.setItem("access_token", state.token);
  localStorage.setItem("username", state.username);
  localStorage.setItem("role", state.role);
  renderSession();
}

function clearSession() {
  state.token = "";
  state.refreshToken = "";
  state.username = "";
  state.role = "";
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("username");
  localStorage.removeItem("role");
  renderSession();
}

async function refreshAccessToken() {
  if (!state.refreshToken) {
    return false;
  }

  const response = await fetch("/refresh", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${state.refreshToken}`,
    },
  });

  if (!response.ok) {
    return false;
  }

  const payload = await response.json();
  if (!payload.access_token) {
    return false;
  }

  saveSession(payload.access_token);
  return true;
}

function renderSession() {
  const isLoggedIn = Boolean(state.token);
  authView.hidden = isLoggedIn;
  appShell.hidden = !isLoggedIn;
  userDashboard.hidden = !isLoggedIn || state.role !== "user";
  adminDashboard.hidden = !isLoggedIn || state.role !== "admin";

  // Keep view toggling resilient even if cached CSS or classes conflict.
  authView.classList.toggle("hidden", isLoggedIn);
  appShell.classList.toggle("hidden", !isLoggedIn);
  userDashboard.classList.toggle("hidden", !isLoggedIn || state.role !== "user");
  adminDashboard.classList.toggle("hidden", !isLoggedIn || state.role !== "admin");

  authView.style.display = isLoggedIn ? "none" : "flex";
  appShell.style.display = isLoggedIn ? "block" : "none";
  userDashboard.style.display = isLoggedIn && state.role === "user" ? "block" : "none";
  adminDashboard.style.display = isLoggedIn && state.role === "admin" ? "block" : "none";

  sessionUser.textContent = state.username || "none";
  sessionRole.textContent = state.role || "none";
  if (topAdminUsersBtn) {
    topAdminUsersBtn.classList.toggle("hidden", !isLoggedIn || state.role !== "admin");
  }
  if (topAdminFilesBtn) {
    topAdminFilesBtn.classList.toggle("hidden", !isLoggedIn || state.role !== "admin");
  }
  if (isLoggedIn && state.role === "admin") {
    renderAdminTab();
  }
}

async function api(path, options = {}) {
  const retryOnAuthFailure = options.retryOnAuthFailure !== false;
  const headers = options.headers || {};
  if (state.token) {
    headers.Authorization = `Bearer ${state.token}`;
  }

  const response = await fetch(path, {
    ...options,
    headers,
  });

  const contentType = response.headers.get("content-type") || "";
  if (
    response.status === 401 &&
    retryOnAuthFailure &&
    path !== "/refresh" &&
    path !== "/login" &&
    path !== "/register"
  ) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      return api(path, { ...options, retryOnAuthFailure: false });
    }
    clearSession();
  }

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    if (contentType.includes("application/json")) {
      const err = await response.json();
      message = err.error || message;
    }
    throw new Error(message);
  }

  if (contentType.includes("application/json")) {
    return response.json();
  }
  return response;
}

function makeActionButton(label, onClick, extraClass = "") {
  const btn = document.createElement("button");
  btn.textContent = label;
  btn.className = `action-btn ${extraClass}`.trim();
  btn.addEventListener("click", onClick);
  return btn;
}

function formatLocalTimestamp(value) {
  if (!value) {
    return "Never";
  }
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) {
    return "Invalid timestamp";
  }
  const y = dt.getFullYear();
  const m = String(dt.getMonth() + 1).padStart(2, "0");
  const d = String(dt.getDate()).padStart(2, "0");
  const hh = String(dt.getHours()).padStart(2, "0");
  const mm = String(dt.getMinutes()).padStart(2, "0");
  const ss = String(dt.getSeconds()).padStart(2, "0");
  const tz = Intl.DateTimeFormat(undefined, { timeZoneName: "short" })
    .formatToParts(dt)
    .find((part) => part.type === "timeZoneName")?.value || "local";
  return `${y}-${m}-${d} ${hh}:${mm}:${ss} ${tz}`;
}

async function loadFiles() {
  try {
    const files = await api("/files");
    filesBody.innerHTML = "";
    if (adminFilesBody) {
      adminFilesBody.innerHTML = "";
    }

    for (const file of files) {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td class="py-3">${file.filename}</td>
        <td class="py-3">${file.owner_id}</td>
        <td class="py-3">${formatLocalTimestamp(file.created_at)}</td>
        <td class="py-3"></td>
      `;

      const actions = row.querySelector("td:last-child");
      const downloadBtn = makeActionButton("Download", async () => {
        try {
          const response = await api(`/download/${file.id}`);
          const blob = await response.blob();
          const link = document.createElement("a");
          link.href = URL.createObjectURL(blob);
          link.download = file.filename;
          document.body.appendChild(link);
          link.click();
          link.remove();
          URL.revokeObjectURL(link.href);
          setStatus(`Downloaded ${file.filename}`);
          notifySuccess(`Downloaded ${file.filename}`);
        } catch (err) {
          setStatus(err.message, true);
          notifyError(err.message);
        }
      });

      const deleteBtn = makeActionButton("Delete", async () => {
        if (!confirm(`Delete file ${file.filename}?`)) {
          return;
        }
        try {
          await api(`/file/${file.id}`, { method: "DELETE" });
          setStatus(`Deleted ${file.filename}`);
          notifySuccess(`Deleted ${file.filename}`);
          await loadFiles();
        } catch (err) {
          setStatus(err.message, true);
          notifyError(err.message);
        }
      }, "outline");

      actions.appendChild(downloadBtn);
      actions.appendChild(deleteBtn);
      if (state.role === "admin" && adminFilesBody) {
        const compact = document.createElement("tr");
        compact.innerHTML = `
          <td class="py-3">${file.owner_username || "unknown"}</td>
          <td class="py-3">${file.filename}</td>
          <td class="py-3 font-mono text-xs">${file.encrypted_string || ""}</td>
          <td class="py-3">${formatLocalTimestamp(file.last_downloaded_at)}</td>
          <td class="py-3"></td>
        `;
        const adminDownloadBtn = makeActionButton("Download", async () => {
          try {
            const response = await api(`/download/${file.id}`);
            const blob = await response.blob();
            const link = document.createElement("a");
            link.href = URL.createObjectURL(blob);
            link.download = file.filename;
            document.body.appendChild(link);
            link.click();
            link.remove();
            URL.revokeObjectURL(link.href);
            notifySuccess(`Downloaded ${file.filename}`);
          } catch (err) {
            notifyError(err.message);
          }
        });
        compact.querySelector("td:last-child").appendChild(adminDownloadBtn);
        const delBtn = makeActionButton("Delete", async () => {
          if (!confirm(`Delete file ${file.filename}?`)) {
            return;
          }
          try {
            await api(`/file/${file.id}`, { method: "DELETE" });
            notifySuccess(`Deleted ${file.filename}`);
            await loadFiles();
          } catch (err) {
            notifyError(err.message);
          }
        }, "outline");
        compact.querySelector("td:last-child").appendChild(delBtn);
        adminFilesBody.appendChild(compact);
      } else {
        filesBody.appendChild(row);
      }
    }

    if (statFiles) {
      statFiles.textContent = String(files.length);
    }

    setStatus(`Loaded ${files.length} file(s)`);
  } catch (err) {
    filesBody.innerHTML = "";
    if (adminFilesBody) {
      adminFilesBody.innerHTML = "";
    }
    setStatus(err.message, true);
    notifyError(err.message);
  }
}

async function loadUsers() {
  if (state.role !== "admin") {
    usersBody.innerHTML = "";
    return;
  }

  try {
    const users = await api("/users");
    usersBody.innerHTML = "";

    for (const user of users) {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td class="py-3">${user.username}</td>
        <td class="py-3">${user.role}</td>
        <td class="py-3">${user.failed_attempts}</td>
        <td class="py-3"></td>
      `;

      const actions = row.querySelector("td:last-child");
      const nextRole = user.role === "admin" ? "user" : "admin";

      const roleBtn = makeActionButton(`Role: ${nextRole}`, async () => {
        try {
          await api(`/users/${user.id}/role`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ role: nextRole }),
          });
          notifySuccess(`Updated ${user.username} role to ${nextRole}`);
          await loadUsers();
        } catch (err) {
          notifyError(err.message);
        }
      }, "outline");

      const unlockBtn = makeActionButton("Unlock", async () => {
        try {
          await api(`/users/${user.id}/unlock`, { method: "POST" });
          notifySuccess(`Unlocked ${user.username}`);
          await loadUsers();
        } catch (err) {
          notifyError(err.message);
        }
      }, "outline");

      const deleteBtn = makeActionButton("Delete User", async () => {
        if (!confirm(`Delete user ${user.username}?`)) {
          return;
        }
        try {
          await api(`/users/${user.id}`, { method: "DELETE" });
          notifySuccess(`Deleted user ${user.username}`);
          await loadUsers();
        } catch (err) {
          notifyError(err.message);
        }
      }, "outline");

      actions.appendChild(roleBtn);
      actions.appendChild(unlockBtn);
      actions.appendChild(deleteBtn);
      usersBody.appendChild(row);
    }

    if (statUsers) {
      statUsers.textContent = String(users.length);
    }

    setStatus(`Loaded ${users.length} user(s)`);
  } catch (err) {
    usersBody.innerHTML = "";
    setStatus(err.message, true);
    notifyError(err.message);
  }
}

document.getElementById("login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const username = document.getElementById("login-username").value.trim();
  const password = document.getElementById("login-password").value;

  try {
    const data = await api("/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    saveSession(data.access_token, data.refresh_token || "");
    setStatus("Login successful.");
    notifySuccess("Login successful.");
    await loadFiles();
    await loadUsers();
  } catch (err) {
    setStatus(err.message, true);
    notifyError(err.message);
  }
});

if (showRegisterBtn && registerForm) {
  showRegisterBtn.addEventListener("click", () => {
    const willShow = registerForm.hidden;
    registerForm.hidden = !willShow;
    registerForm.classList.toggle("hidden", !willShow);
    showRegisterBtn.textContent = willShow ? "Hide Create Account" : "Create Account";
  });
}

if (registerForm) {
  registerForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const username = document.getElementById("register-username").value.trim();
    const password = document.getElementById("register-password").value;

    try {
      await api("/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      setStatus("Account created successfully. Please login.");
      notifySuccess("Account created successfully.");
      registerForm.reset();
      registerForm.hidden = true;
      registerForm.classList.add("hidden");
      if (showRegisterBtn) {
        showRegisterBtn.textContent = "Create Account";
      }
    } catch (err) {
      setStatus(err.message, true);
      notifyError(err.message);
    }
  });
}

document.getElementById("logout-btn").addEventListener("click", async () => {
  try {
    if (state.token) {
      await api("/logout", { method: "POST", retryOnAuthFailure: false });
    }
  } catch (_err) {
    // Ignore logout failures and clear local session anyway.
  }

  clearSession();
  filesBody.innerHTML = "";
  usersBody.innerHTML = "";
  setStatus("Session cleared.");
  notifySuccess("Logged out.");
});

document.getElementById("upload-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = document.getElementById("upload-file");
  const file = input.files[0];

  if (!file) {
    setStatus("Select a file before upload.", true);
    return;
  }

  try {
    const formData = new FormData();
    formData.append("file", file);
    await api("/upload", {
      method: "POST",
      body: formData,
    });
    input.value = "";
    setStatus("File encrypted and uploaded.");
    notifySuccess("File encrypted and uploaded.");
    await loadFiles();
  } catch (err) {
    setStatus(err.message, true);
    notifyError(err.message);
  }
});

document.getElementById("refresh-files").addEventListener("click", loadFiles);
document.getElementById("refresh-users").addEventListener("click", loadUsers);
const refreshFilesAdminBtn = document.getElementById("refresh-files-admin");
if (refreshFilesAdminBtn) {
  refreshFilesAdminBtn.addEventListener("click", loadFiles);
}
if (topAdminFilesBtn) {
  topAdminFilesBtn.addEventListener("click", () => {
    adminActiveTab = "files";
    renderAdminTab();
    loadFiles();
  });
}
if (topAdminUsersBtn) {
  topAdminUsersBtn.addEventListener("click", () => {
    adminActiveTab = "users";
    renderAdminTab();
    loadUsers();
  });
}

renderSession();
if (state.token) {
  loadFiles();
  loadUsers();
}
