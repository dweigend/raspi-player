# Distribution outside the Mac App Store

Reviewed on 2026-09-10 for a GitHub-hosted macOS download.

[Apple's Xcode and Apple SDKs Agreement](https://images.apple.com/legal/sla/docs/xcode.pdf),
section 2.4 (PDF page 4), expressly permits distribution of macOS applications
and libraries without a separate written agreement with Apple, provided the
agreement's terms are met. The same section distinguishes distribution through
the App Store, which requires the Apple Developer Program agreement.
[Apple's macOS distribution overview](https://developer.apple.com/macos/distribution/)
also describes distribution outside the store.

Raspi Player is distributed as a GitHub Release DMG. It is ad-hoc signed and not
notarized. This is not an Apple approval or a verified Developer ID. Distribution
permission and Gatekeeper's decision to open a downloaded app are separate matters.
This review addresses the distribution route, not a blanket certification of
compliance with every Apple or third-party license term.

[Apple's opening instructions](https://support.apple.com/de-de/102445) describe
the per-app exception under System Settings > Privacy & Security > Open Anyway
after an initial attempt to open a trusted app. The
[Mac user guide](https://support.apple.com/de-de/guide/mac-help/mh40616/mac)
also documents the login-password prompt. The app can subsequently be opened
normally. Managed computers may restrict this option.

The README explains this process without disabling Gatekeeper globally. The
administrator authorization requested later by Raspberry Pi Imager for writing
an SD card is separate from the first-launch approval. Passwords are entered in
system dialogs, not into Raspi Player or GitHub.
