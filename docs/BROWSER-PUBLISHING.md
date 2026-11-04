# Publish the Focus Goblu browser companion

## Prepare and test

1. Open `chrome://extensions` or `edge://extensions`, enable Developer mode and use **Load unpacked** on the `extension` directory.
2. Start a one-minute session, close and reopen the popup, then test pause, resume, reset and the completion notification. Check that the support link opens the intended Ko-fi page.
3. ZIP the files inside `extension` so `manifest.json` is at the archive root. Use the same package for both stores. Increment the manifest version for updates.
4. Prepare screenshots, listing text, support contact and a publicly reachable URL for the browser privacy policy. The policy in this private repository needs a public location before submission.

The single purpose is a local task timer. Disclose that `storage` retains the task and timer state, `alarms` schedules completion and `notifications` displays the completion reminder. The companion bundles its code and uses a link for Ko-fi. Describe only browser features in the listing.

## Chrome Web Store

Register a developer account, complete the registration requirements and upload the ZIP as a new item in the developer dashboard. Complete the listing, privacy declarations, distribution settings and test instructions. Submit for review. [Official Chrome publishing guide](https://developer.chrome.com/docs/webstore/publish)

## Microsoft Edge Add-ons

Register as an Edge extension developer in Partner Center. Create a new extension, upload the ZIP, choose visibility and markets, and fill in properties, privacy, listing and certification notes. Submit for certification. [Official Edge publishing guide](https://learn.microsoft.com/en-us/microsoft-edge/extensions/publish/publish-extension)

Chrome Manifest V3 requires bundled executable code. The Ko-fi CDN widget script belongs on a regular site that permits it. [Chrome remote-code rules](https://developer.chrome.com/docs/extensions/develop/migrate/remote-hosted-code)
