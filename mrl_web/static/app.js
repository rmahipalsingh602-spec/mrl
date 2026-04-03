// ==========================================
// MRL_WEB v4.0 Frontend Engine
// ==========================================

console.log("🚀 MRL Frontend Loaded");

// ===============================
// SPA Router
// ===============================

function navigate(path) {
    fetch(path)
        .then(res => res.text())
        .then(html => {
            document.open();
            document.write(html);
            document.close();
        });
}

// ===============================
// Dynamic Component Loader
// ===============================

function loadComponent(name) {
    const container = document.getElementById("component-root");

    fetch(`/api/component/${name}`)
        .then(res => res.json())
        .then(data => {
            container.innerHTML = data.html;
        });
}

// ===============================
// API Example Call
// ===============================

function callAPI(endpoint) {
    fetch(`/api/${endpoint}`)
        .then(res => res.json())
        .then(data => {
            alert("API Response: " + JSON.stringify(data));
        });
}

// ===============================
// Modern Animation Helper
// ===============================

function fadeIn(element) {
    element.style.opacity = 0;
    element.style.display = "block";

    let opacity = 0;
    const timer = setInterval(() => {
        opacity += 0.05;
        element.style.opacity = opacity;

        if (opacity >= 1) clearInterval(timer);
    }, 20);
}

// ===============================
// Theme Switcher
// ===============================

function toggleTheme() {
    document.body.classList.toggle("dark-mode");
}

// ===============================
// Auto Bind Navbar Links (SPA)
// ===============================

document.addEventListener("DOMContentLoaded", function() {

    document.querySelectorAll("a").forEach(link => {
        if (link.getAttribute("href").startsWith("/")) {
            link.addEventListener("click", function(e) {
                e.preventDefault();
                navigate(link.getAttribute("href"));
            });
        }
    });

});