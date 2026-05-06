// =========================
// HealVision Auth JS (Login & Signup Pages)
// =========================

document.addEventListener("DOMContentLoaded", () => {
  const signupForm = document.getElementById("signupForm");
  const signupMessage = document.getElementById("signupMessage");
  const loginForm = document.getElementById("loginForm");
  const loginMessage = document.getElementById("loginMessage");

  // =========================
  // ✅ Google OAuth Redirect Handler
  // =========================
  const params = new URLSearchParams(window.location.search);
  const tokenFromURL = params.get("token");

  if (tokenFromURL) {
    console.log("✅ Google OAuth token received:", tokenFromURL);
    localStorage.setItem("token", tokenFromURL);

    // Clean URL
    const cleanUrl = window.location.origin + window.location.pathname;
    window.history.replaceState({}, document.title, cleanUrl);

    // Redirect user to dashboard
    setTimeout(() => {
      window.location.href = "index.html";
    }, 200);

    return;
  }

  // =========================
  // Signup Form Submit
  // =========================
  signupForm?.addEventListener("submit", async (e) => {
    e.preventDefault();

    const name = document.getElementById("signupName")?.value.trim();
    const email = document.getElementById("signupEmail")?.value.trim();
    const password = document.getElementById("signupPassword")?.value.trim();

    if (!name || !email || !password) {
      signupMessage.textContent = "⚠️ Please fill out all fields.";
      signupMessage.style.color = "red";
      return;
    }

    try {
      const res = await fetch("http://127.0.0.1:5000/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, password }),
      });

      const data = await res.json();

      if (res.ok) {
        signupMessage.textContent = "✅ Signup successful! Redirecting to login...";
        signupMessage.style.color = "green";
        signupForm.reset();
        setTimeout(() => { window.location.href = "login.html"; }, 1800);
      } else {
        signupMessage.textContent = "❌ " + (data.message || data.error || "Signup failed");
        signupMessage.style.color = "red";
      }
    } catch (err) {
      console.error("Signup error:", err);
      signupMessage.textContent = "❌ Error connecting to server.";
      signupMessage.style.color = "red";
    }
  });

  // =========================
  // Login Form Submit
  // =========================
  loginForm?.addEventListener("submit", async (e) => {
    e.preventDefault();

    const email = document.getElementById("loginEmail")?.value.trim();
    const password = document.getElementById("loginPassword")?.value.trim();

    if (!email || !password) {
      loginMessage.textContent = "⚠️ Please enter both email and password.";
      loginMessage.style.color = "red";
      return;
    }

    try {
      const res = await fetch("http://127.0.0.1:5000/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = await res.json();

      if (res.ok && data.token) {
        loginMessage.textContent = "✅ Login successful! Redirecting...";
        loginMessage.style.color = "green";

        // Save token and user info
        localStorage.setItem("token", data.token);
        localStorage.setItem(
          "user",
          JSON.stringify({
            id: data.user?.id || "",
            name: data.user?.name || "",
            email: data.user?.email || "",
            age: data.user?.age || "",
            gender: data.user?.gender || "",
          })
        );

        setTimeout(() => { window.location.href = "index.html"; }, 1500);
      } else {
        loginMessage.textContent = "❌ " + (data.error || data.message || "Login failed");
        loginMessage.style.color = "red";
      }
    } catch (err) {
      console.error("Login error:", err);
      loginMessage.textContent = "❌ Error connecting to server.";
      loginMessage.style.color = "red";
    }
  });
});
