# MileSage branded launcher icon — Alpha 1.4.9

Approved artwork: silver metallic **MS** framed by Red Dirt Code curly braces, a sunset highway, electric-blue border, and MileSage wordmark.

- App launcher image: `android/app/src/main/res/drawable-nodpi/ic_milesage_brand.webp` (160x160 WebP, optimized from the approved master artwork).
- Manifest `android:icon` now points to that artwork.
- App launcher name is `MileSage`.
- Version is `1.4.9-ms-branded-side-by-side`; package ID is `io.reddirtcode.milesage.alpha149brandedtest`, **different** from earlier test builds to avoid installation rejection when their debug signing certificates differ.
- Application behavior, storage and scanner features are unchanged from the 1.4.8 branch.
- Full-resolution master artwork and multi-density PNG files were exported separately to the MileSage Android launcher asset package for archival and future release.

**Testing:** install this as a **separate test app** after making a Full mobile JSON backup from the installed app. Do not uninstall the working app or clear its storage. This new package starts with empty app-specific storage, so import a backup into the new test copy and verify both real vehicle histories. Its debug signature is not a stable production/update key. The package ID must not be reused as an updatable release until a persistent signing key is configured.
