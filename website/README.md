# MRL Website

Static product website for MRL (Multi Runtime Language), an official Mr. Rathore Company product.

## Local Preview

Serve the `website/` folder with any static server:

```bash
python -m http.server 8080
```

Then open `http://localhost:8080/website/`.

## Deploy

### GitHub Pages

1. Push the repository to GitHub.
2. Configure Pages to publish from the branch and folder that contains `website/`.
3. Use `website/` as the published root.

### Netlify

1. Create a new site from the repository.
2. Netlify will read `netlify.toml` automatically and publish from `website`.
3. No build command is required.
4. Static routes like `/download`, `/docs`, `/features`, `/about`, and `/thank-you` are already configured.
5. Form submissions from the download page are saved in Netlify Forms.

## Build Windows Release

Run the release script from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_release.ps1
```

This script:

- rebuilds `dist/mrl.exe` with the current MRL version metadata
- compiles the Inno Setup installer
- copies versioned and stable download files into `website/downloads/`
- generates `website/downloads/release-manifest.json`
- generates `website/downloads/SHA256SUMS.txt`

## SmartScreen Note

Browser and Windows reputation warnings for `.exe` downloads are not fully solved by HTML alone. To remove the "isn't commonly downloaded" warning reliably, ship an Authenticode-signed release and build reputation on that certificate.

## Saved Data

- Form name: `mrl-global-access`
- Storage: Netlify Forms dashboard
- Use: collect global download interest, country, company, and partnership requests

## Included Downloads

- `downloads/mrl-windows-x64-setup.exe`: official Windows setup installer linked from `download.html`
- `downloads/mrl-windows-x64.exe`: portable Windows executable offered as an alternate download
