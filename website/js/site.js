(() => {
  const root = document.documentElement;
  const navToggle = document.querySelector("[data-nav-toggle]");
  const navLinks = document.querySelector("[data-nav-links]");
  const revealItems = document.querySelectorAll("[data-reveal]");
  const copyButtons = document.querySelectorAll("[data-copy]");
  const hero = document.querySelector("[data-hero-glow]");
  const yearTarget = document.querySelector("[data-year]");
  const releaseFields = document.querySelectorAll("[data-release-field]");
  const releaseLinks = document.querySelectorAll("[data-download-link]");
  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  if (yearTarget) {
    yearTarget.textContent = String(new Date().getFullYear());
  }

  if (navToggle && navLinks) {
    navToggle.addEventListener("click", () => {
      const isOpen = navLinks.classList.toggle("is-open");
      navToggle.setAttribute("aria-expanded", String(isOpen));
    });

    navLinks.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => {
        navLinks.classList.remove("is-open");
        navToggle.setAttribute("aria-expanded", "false");
      });
    });
  }

  if (revealItems.length) {
    if (prefersReducedMotion) {
      revealItems.forEach((item) => item.classList.add("is-visible"));
    } else {
      const observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (!entry.isIntersecting) {
              return;
            }
            entry.target.classList.add("reveal-ready", "is-visible");
            observer.unobserve(entry.target);
          });
        },
        {
          threshold: 0.16,
          rootMargin: "0px 0px -40px 0px",
        }
      );

      revealItems.forEach((item) => {
        item.classList.add("reveal-ready");
        observer.observe(item);
      });
    }
  }

  copyButtons.forEach((button) => {
    button.addEventListener("click", async () => {
      const selector = button.getAttribute("data-copy");
      const target = selector ? document.querySelector(selector) : null;
      if (!target) {
        return;
      }

      const original = button.textContent;
      try {
        await navigator.clipboard.writeText(target.textContent.trim());
        button.textContent = "Copied";
      } catch {
        button.textContent = "Select code";
      }

      window.setTimeout(() => {
        button.textContent = original;
      }, 1400);
    });
  });

  if (hero && !prefersReducedMotion) {
    window.addEventListener("pointermove", (event) => {
      const rect = hero.getBoundingClientRect();
      const insideX = ((event.clientX - rect.left) / rect.width) * 100;
      const insideY = ((event.clientY - rect.top) / rect.height) * 100;

      if (insideX >= 0 && insideX <= 100 && insideY >= 0 && insideY <= 100) {
        root.style.setProperty("--pointer-x", `${insideX}%`);
        root.style.setProperty("--pointer-y", `${insideY}%`);
      }
    });
  }

  if (releaseFields.length || releaseLinks.length) {
    const setField = (field, value) => {
      document.querySelectorAll(`[data-release-field="${field}"]`).forEach((node) => {
        node.textContent = value;
      });
    };

    const updateLink = (key, artifact) => {
      if (!artifact) {
        return;
      }

      document.querySelectorAll(`[data-download-link="${key}"]`).forEach((node) => {
        node.setAttribute("href", artifact.download_path.replace(/^website\//, ""));
        node.setAttribute("download", artifact.name);
      });
    };

    const formatBytes = (value) => {
      if (!Number.isFinite(value) || value <= 0) {
        return "--";
      }

      const units = ["B", "KB", "MB", "GB"];
      let size = value;
      let index = 0;

      while (size >= 1024 && index < units.length - 1) {
        size /= 1024;
        index += 1;
      }

      return `${size.toFixed(index === 0 ? 0 : 2)} ${units[index]}`;
    };

    const formatTimestamp = (value) => {
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) {
        return value;
      }

      return date.toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      });
    };

    fetch("downloads/release-manifest.json", { cache: "no-store" })
      .then((response) => {
        if (!response.ok) {
          throw new Error("Release manifest unavailable");
        }
        return response.json();
      })
      .then((manifest) => {
        const setup = manifest.artifacts?.setup;
        const portable = manifest.artifacts?.portable;
        const checksumLines = [];

        setField("version", manifest.version || "Unknown");
        setField("generated", formatTimestamp(manifest.generated_at || ""));

        if (setup) {
          setField("setup-name", setup.name);
          setField("setup-size", formatBytes(setup.size_bytes));
          setField("setup-signing", setup.signature_label || setup.signature_status || "Unknown");
          checksumLines.push(`${setup.sha256}  ${setup.name}`);
          updateLink("setup", setup);
        }

        if (portable) {
          setField("portable-name", portable.name);
          setField("portable-size", formatBytes(portable.size_bytes));
          setField("portable-signing", portable.signature_label || portable.signature_status || "Unknown");
          checksumLines.push(`${portable.sha256}  ${portable.name}`);
          updateLink("portable", portable);
        }

        if (checksumLines.length) {
          setField("checksums", checksumLines.join("\n"));
        }
      })
      .catch(() => {
        setField("generated", "Manifest unavailable");
        setField("checksums", "Release manifest unavailable.");
      });
  }
})();

