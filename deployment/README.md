# Desktop packaging

The tagged-release workflow in `.github/workflows/release.yml` builds native packages on GitHub-hosted Windows x64 and macOS arm64 runners. PyInstaller bundles must be built on their target operating system; they are not cross-compiled. The Windows bundle is wrapped in an Inno Setup installer, and the macOS `.app` is placed in a compressed DMG with an Applications shortcut.

## Local build

Install the release tools and generate the platform icon files:

```bash
python -m pip install ".[release]"
python scripts/build_icon_assets.py
```

Build in one-directory mode with `--icon build/icons/app-icon.ico` on Windows or `--icon build/icons/app-icon.icns` on macOS:

```bash
python -m PyInstaller --noconfirm --clean --windowed --onedir --name AtomicStructureExplorer --collect-data atomic_structure_explorer --icon PLATFORM_ICON main.py
```

The distributable application is under `dist/`. On Windows, compile `deployment/windows/installer.iss` with `ISCC.exe`. On macOS, use `hdiutil create` with the `.app` and an Applications symlink as demonstrated in the release workflow. Test the final installer or disk image on a clean machine before publishing it.

## Signing

CI releases are currently unsigned. A production Windows release should be code-signed before packaging. A production macOS release should be signed with a Developer ID certificate, notarized, and stapled before distribution. Store signing credentials only as protected repository or environment secrets; never add them to the repository.

The reference-data manifest must be audited as part of every release. Packaging must not include a dataset without explicit, verified redistribution permission.
