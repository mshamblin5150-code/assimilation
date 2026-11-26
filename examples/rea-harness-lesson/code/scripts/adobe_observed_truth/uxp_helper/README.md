# Observed-truth UXP helper

Lets the harness run any Photoshop menu command by the number `menuBarInfo` reports, which
ExtendScript cannot do. The plugin polls `http://127.0.0.1:47615` (the only address its
manifest allows), runs what the harness queued (`ping` or `menu_command`), and posts the
result back. It presses no buttons: the harness records and cancels any dialog a command
opens, and never presses Generate, Submit, Share, Upload, Create link or Sign Out.

## Installation (permanent)

Installed 2026-11-09 as a Creative Cloud plugin, so it loads when Photoshop starts
(`loadEvent: startup`) with no developer tools:

```
python -c "from pathlib import Path; from scripts.adobe_observed_truth.uxp_bridge import package_helper; print(package_helper(Path('<corpus>/uxp-helper')))"
"C:\Program Files\Common Files\Adobe\Adobe Desktop Common\RemoteComponents\UPI\UnifiedPluginInstallerAgent\UnifiedPluginInstallerAgent.exe" /install <the .ccx printed above>
```

Bump `version` in `manifest.json` before reinstalling a change, then restart Photoshop.
Remove with `UnifiedPluginInstallerAgent.exe /remove "Adobe observed-truth helper"`.
It is installed for every Photoshop on the machine; the harness only accepts answers from
Photoshop 27 (`require_photoshop`). Developer Mode is no longer needed for it.

## Check it

```
python -m scripts.adobe_observed_truth.uxp_bridge   # prints {'reply': 'pong', 'version': '27.11.0'}
```