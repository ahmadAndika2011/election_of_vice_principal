(() => {
  "use strict";
  let state = null;
  function addLink(parent, label, href) {
    const link = document.createElement("a");
    link.textContent = label;
    link.href = href;
    link.className = "button button-secondary auth-link";
    parent.append(link);
  }
  function render() {
    for (const slot of document.querySelectorAll("[data-auth-nav]")) {
      slot.replaceChildren();
      if (!state.authenticated) {
        addLink(slot, "Login", "/auth/login");
        addLink(slot, "Signup", "/auth/signup");
        continue;
      }
      const name = document.createElement("span");
      name.className = "auth-username";
      name.textContent = state.user.username || "Lengkapi nama lengkap";
      slot.append(name);
      if (!state.profile_complete) addLink(slot, "Lengkapi profil", "/auth/complete-profile");
      const logout = document.createElement("button");
      logout.type = "button";
      logout.className = "button button-secondary auth-link";
      logout.textContent = "Logout";
      logout.addEventListener("click", async () => {
        logout.disabled = true;
        try {
          const response = await fetch("/api/auth/logout", {
            method: "POST", credentials: "same-origin",
            headers: {"X-CSRF-Token": state.csrf_token, Accept: "application/json"}
          });
          if (!response.ok && response.status !== 401) throw new Error();
          window.location.assign("/");
        } catch {
          logout.disabled = false;
          window.alert("Logout belum berhasil. Periksa koneksi dan coba lagi.");
        }
      });
      slot.append(logout);
    }
  }
  window.authReady = (async () => {
    const response = await fetch("/api/auth/me", {
      credentials: "same-origin", cache: "no-store", headers: {Accept: "application/json"},
      signal: AbortSignal.timeout(12000)
    });
    if (!response.ok) throw new Error("Status login belum dapat diperiksa.");
    state = await response.json();
    render();
    return state;
  })();
  window.authReady.catch(() => {
    for (const slot of document.querySelectorAll("[data-auth-nav]")) {
      slot.replaceChildren();
      const retry = document.createElement("button");
      retry.type = "button";
      retry.className = "button button-secondary auth-link";
      retry.textContent = "Cek ulang login";
      retry.addEventListener("click", () => window.location.reload());
      slot.append(retry);
    }
  });
  window.addEventListener("pageshow", event => {
    if (event.persisted) window.location.reload();
  });
})();
