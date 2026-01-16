# Reading Plus Book Highlighter

A Tampermonkey userscript that highlights books/stories on Reading Plus that have answers in the database.

## Installation

1. Install the [Tampermonkey](https://www.tampermonkey.net/) extension for your browser
2. Click the Tampermonkey icon and select "Create a new script"
3. Delete any default code and paste the contents of `reading_plus_highlighter.user.js`
4. Save the script (File → Save or Ctrl+S)

## Configuration

### Updating the Manifest URL

The script uses a placeholder URL for the book manifest. You must update this before using:

```javascript
// Change this line in the script:
const MANIFEST_URL = 'https://raw.githubusercontent.com/YOUR_USER/YOUR_REPO/main/data/book_manifest.json';
```

Replace `YOUR_USER` and `YOUR_REPO` with your GitHub username and repository name.

If your manifest is hosted elsewhere, update the URL accordingly.

### CSS Selector Configuration

The script searches for book elements using a CSS selector. The default may not match Reading Plus's actual structure:

```javascript
const CONFIG = {
    selector: '.book-item, .story-card, .book-card, [class*="book"], [class*="story"]',
    // ...
};
```

To find the correct selector:

1. Enable debug mode by setting `debugMode: true`
2. Open the browser console (F12)
3. Navigate to Reading Plus
4. Run `RP.getElements()` in the console to see all found elements
5. Check the console output for element titles and adjust the selector

Common Reading Plus selectors to try:
- `.book-item`
- `.story-card`
- `.book-card`
- `. passage-card`
- `[data-testid*="book"]`
- `.book-grid item`

### Visual Customization

Modify these values in the CONFIG object:

```javascript
const CONFIG = {
    highlightClass: 'rp-has-answers',
    badgeHtml: '<span class="rp-answer-badge" style="...">Has Answers</span>',
    // Change the border color
    // Change the badge text
};
```

## Features

- **Fuzzy matching**: Matches story titles even with slight differences
- **Visual indicators**: Green border and "Has Answers" badge
- **Debug mode**: Helps identify the correct CSS selectors
- **Console logging**: Shows match details in browser console

## Debug Mode

Enable debug mode for troubleshooting:

```javascript
const CONFIG = {
    debugMode: true,
    // ...
};
```

In debug mode:
- All potential book elements are logged to console
- Run `RP.getElements()` to get a list of all found elements
- Match results are shown with scores

## Troubleshooting

### No elements highlighted

1. Check the browser console for errors
2. Verify the manifest URL is accessible
3. Enable debug mode to see what elements are being found
4. Update the CSS selector to match the actual page structure

### Wrong elements highlighted

Adjust the CSS selector to be more specific, or increase the fuzzy match threshold:

```javascript
// In findMatchingBook(), change 0.6 to a higher value
if (score > bestScore && score >= 0.8) {  // stricter matching
```

### Manifest not loading

- Verify the raw GitHub URL is correct
- Ensure the repository is public
- Check that `book_manifest.json` exists in the specified path
