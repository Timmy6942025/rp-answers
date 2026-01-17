# Reading Plus Highlighter v2.1

A powerful Tampermonkey userscript that automatically highlights Reading Plus stories with answers available in the database.

## 🚀 Quick Installation

1. Install [Tampermonkey](https://www.tampermonkey.net/) or [Violentmonkey](https://violentmonkey.github.io/)
2. Click the extension icon → "Create a new script"
3. Delete all default code
4. Paste contents of `reading_plus_highlighter.user.js`
5. Save (Ctrl+S)
6. Refresh any Reading Plus page

## ✨ Features

| Feature | Description |
|---------|-------------|
| **Auto-Highlighting** | Automatically highlights stories with answers |
| **Fuzzy Search** | Find stories even with partial titles |
| **Level Filtering** | Filter by all 14 Reading Plus levels (A-M + HiE) |
| **Click-to-Copy** | Click question counts to copy them |
| **Keyboard Shortcuts** | Ctrl+/ toggle, F mini mode, D debug mode |
| **Debug Mode** | Toggle with 🐛 button for troubleshooting |
| **Mini Mode** | Compact panel (press F) |
| **Offline Support** | Works offline with cached data (24hr) |
| **Performance Metrics** | Shows load time and search count |
| **Shadow DOM** | Complete CSS isolation |

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + /` | Toggle panel visibility |
| `F` | Toggle mini mode |
| `D` | Toggle debug mode |
| `Esc` | Close panel |

## 🎯 Page Detection

The script automatically detects these Reading Plus pages:

| Page Type | URL Pattern |
|-----------|-------------|
| SeeReader | `/seereader/api/sr/start*` |
| Dashboard | `/dashboard/*` |
| Student Portal | `/student/*` |
| General | `*.readingplus.com/*` |

## 📊 Database Coverage

| Metric | Value |
|--------|-------|
| Total Stories | 62 |
| Total Levels | 14 (A-M + HiE) |
| Questions | 3,359 |
| Cache Duration | 24 hours |

## 🐛 Debug Mode

Enable debug mode for troubleshooting:

1. Click the 🐛 button in the panel header
2. Open browser console (F12)
3. Look for `[RP Highlighter v2.1]` logs

Debug mode shows:
- Element detection attempts
- Match scores
- Load times
- Network requests

## 🔧 Troubleshooting

### No stories highlighted

1. Check browser console for errors
2. Verify internet connection
3. Try refreshing the page
4. Click "Refresh" button in panel
5. Enable debug mode to see detection logs

### Panel not showing

1. Check Tampermonkey is enabled
2. Verify script is installed and enabled
3. Try reloading the page
4. Check for console errors
5. Make sure you're on a Reading Plus URL

### Manifest load failed

- Script will automatically use cached data
- Click "Refresh" to retry
- Check internet connection
- Manifest URL: `https://raw.githubusercontent.com/Timmy6942025/rp-answers/main/data/book_manifest.json`

### Stories highlighting incorrectly

The fuzzy matching threshold can be adjusted in the script:

```javascript
const CONFIG = {
    matchThreshold: 0.6, // Increase to 0.7 or 0.8 for stricter matching
    // ...
};
```

## 🔒 Permissions

The script requires these Tampermonkey permissions:

- `@match` - Access Reading Plus pages
- `@grant GM_xmlhttpRequest` - Fetch manifest from GitHub
- `@grant GM_setValue` - Cache manifest locally
- `@grant GM_getValue` - Retrieve cached manifest
- `@connect` - Connect to raw.githubusercontent.com

## 📱 Mini Mode

Press `F` or click the ◧ button to switch to mini mode:

- Hides search controls
- Shows only stats
- Takes less screen space
- Press `F` again or click header to restore

## 💾 Caching

The script caches the manifest locally for:

- Offline access (up to 24 hours)
- Faster page loads
- Reduced API calls

To clear cache:
1. Disable the script
2. Clear browser localStorage
3. Re-enable the script

## 🔄 Version History

### v2.1 (Current)
- Added mini mode (F key)
- Added page type detection
- Added performance metrics
- Improved offline mode
- Added refresh button
- Enhanced Reading Plus selectors
- Added version badge

### v2.0
- Complete rewrite
- Shadow DOM for style isolation
- Click-to-copy question counts
- Keyboard shortcuts
- Debug mode
- Loading states
- Better error handling

### v1.0
- Initial release
- Basic highlighting
- Simple search

## 📁 Files

```
userscripts/
├── reading_plus_highlighter.user.js  # Main userscript
├── test-suite.html                   # Test suite (for development)
└── README.md                         # This file
```

## 🤝 Contributing

To update the book manifest:

```bash
# Generate updated manifest from database
python3 -c "
import json
data = json.load(open('data/ULTRACOMPLETE_V4_reading_plus.json'))
# ... aggregation logic ...
json.dump(manifest, open('data/book_manifest.json', 'w'))
```

Then commit and push the updated manifest.

## 📄 License

MIT License - See repository for details.

## ⚠️ Disclaimer

This is an unofficial tool. Use at your own risk. Not affiliated with Reading Plus or any educational institution.
