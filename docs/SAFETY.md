# Security, privacy, licensing, verification

Assimilation is intended for public sharing. It includes only **generalized** ideas from Open Brain, not Open Brain content dumps, live connectors, tokens, user-specific medical information, internal file paths, or the private DAVID 2 repository. Do not add such content later. Clinical Skills is a separately maintained public project; it illustrates the skill-document format but **is not a dependency** of this starter package.

**Before sharing:** inspect staged files with `git diff --cached`, verify `vendor/`, `.agents/`, `.assimilation-stage-*`, and `.assimilation-install.lock` are ignored (except the optional curated local skills under `skills/`), check no private data, patient information, account IDs, keys, secrets or unlicensed material is included. Never assume scanners are complete. No workflow here grants authority to inspect private projects or post on anyone else's behalf.

**Trust of upstream sources:** `install` fetches code and Markdown from published GitHub repositories but does not run upstream setup scripts. Treat each changed source commit as an external dependency. Review its diff and licenses before using any newly changed executable tools or giving agents file/system permissions. Monthly automation **only proposes review**.

**Citations and attribution:** external works retain their own notices in installed source trees. Matt Pocock's skills are MIT-licensed (copyright 2026 Matt Pocock); P-Stack is MIT-licensed (copyright 2026 Lauren Tan), based on inspected upstream license files. This starter package is independently written; do not represent it as official upstream documentation. **Public URLs or public licenses do not imply permission to expose private user data.**

**Engineering and physical risk:** no claim of physical strength, fitness for purpose, medical accuracy, or security is valid without appropriate testing and expert oversight. The claim-and-refutation review is an evidence check, not a guarantee. Real mechanical designs must consider load cases, print orientation, material strength, fasteners, temperature, and tolerances.

**Authority and verification:** a ZERO_BLOCKING_FOG declaration confirms no unresolved **known blocking design decisions** for a defined scope. It is not permission for commits, merges, external communications, releases, credential access, or deployment. Those follow operator and platform permissions separately.

**Stopped installations:** retained stages can contain the only original backups, private local skills, or fetched Git configuration. Never publish them or delete them merely to clear a guard. Follow [recovery without data loss](RECOVERY.md).
