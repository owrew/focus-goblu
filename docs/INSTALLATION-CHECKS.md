# Windows installer checks · 0.3.0 · 2026-11-03

- Built using Inno Setup 7.1.1, obtained from its official release. Compiler installer Authenticode status was Valid (Pyrsys B.V.). The app's generated installer is **unsigned**; no signing certificate is configured.
- Packaged executable self-test passed: UI loaded, logo loaded, global pause registered, five primary tabs, MediaPipe FaceMesh initialized. The render-cache change was also confirmed in the built Python archive.
- First installation into the isolated project work/install-smoke directory succeeded. The initial diagnostic wait limit was too short; its installer log confirmed successful completion. The bounded test timeout was extended, then an in-place reinstall succeeded with exit code 0.
- Installed FocusGoblin.exe self-test passed with the same results.
- The included uninstaller exited successfully and removed the isolated test application and uninstall registration. The user's original project and previous release archives were preserved.
- Existing real local session count and settings payload were compared before/after installation, reinstall and uninstall and were unchanged. No startup task was selected during testing.

This verifies the install/update/uninstall cycle on the current Windows computer. It is not a clean-VM test, an older-Windows compatibility certification, or proof of antivirus/SmartScreen reputation. Source startup registration was implemented as an opt-in per-user Run entry; actual sign-out/sign-in startup was not performed. The native global shortcut's registration and message dispatch were verified separately.

Use FocusGoblin-Setup-0.3.0.exe for a normal per-user installation and Start menu shortcut. Later installers using the same application ID upgrade the same path and preserve the LocalAppData/FocusGoblin data folder. The Settings update picker requires an installer you have already downloaded and explicitly confirm; there is no hosted automatic updater.
