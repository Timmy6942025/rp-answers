// ==UserScript==
// @name         Reading Plus Book Highlighter
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Highlight Reading Plus books that have answers in the database
// @author       Your Name
// @match        https://readingplus.com/*
// @require      https://code.jquery.com/jquery-3.6.0.min.js
// @grant        GM_xmlhttpRequest
// @connect      raw.githubusercontent.com
// ==/UserScript==

(function() {
    'use strict';

    const MANIFEST_URL = 'https://raw.githubusercontent.com/YOUR_USER/YOUR_REPO/main/data/book_manifest.json';

    const CONFIG = {
        selector: '.book-item, .story-card, .book-card, [class*="book"], [class*="story"]',
        highlightClass: 'rp-has-answers',
        badgeHtml: '<span class="rp-answer-badge" style="position:absolute;top:4px;right:4px;background:#22c55e;color:#fff;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:bold;z-index:100;">Has Answers</span>',
        debugMode: false
    };

    let bookManifest = [];

    function normalizeText(text) {
        return text.toLowerCase().trim().replace(/\s+/g, ' ');
    }

    function fuzzyMatch(title, manifestTitle) {
        const t1 = normalizeText(title);
        const t2 = normalizeText(manifestTitle);

        if (t1 === t2) return 1.0;
        if (t1.includes(t2) || t2.includes(t1)) return 0.9;

        const words1 = t1.split(' ').filter(w => w.length > 2);
        const words2 = t2.split(' ').filter(w => w.length > 2);

        if (words1.length === 0 || words2.length === 0) return 0;

        const matches = words1.filter(w => words2.some(w2 => w2.startsWith(w) || w.startsWith(w2)));
        return matches.length / Math.max(words1.length, words2.length);
    }

    function findMatchingBook(domTitle) {
        let bestMatch = null;
        let bestScore = 0;

        for (const book of bookManifest) {
            const score = fuzzyMatch(domTitle, book.title);
            if (score > bestScore && score >= 0.6) {
                bestScore = score;
                bestMatch = book;
            }
        }

        return bestMatch;
    }

    function highlightBook(element, bookInfo) {
        element.classList.add(CONFIG.highlightClass);
        element.style.position = 'relative';
        element.style.border = '2px solid #22c55e';

        const existingBadge = element.querySelector('.rp-answer-badge');
        if (!existingBadge) {
            const badge = document.createElement('div');
            badge.innerHTML = CONFIG.badgeHtml;
            element.appendChild(badge.firstChild);
        }

        if (CONFIG.debugMode) {
            console.log(`[RP Highlighter] Matched: "${bookInfo.title}" (${bookInfo.count} questions, Level ${bookInfo.level})`);
        }
    }

    function processBooks() {
        const elements = document.querySelectorAll(CONFIG.selector);

        if (CONFIG.debugMode) {
            console.log(`[RP Highlighter] Found ${elements.length} potential book elements`);
            window.rpDebugElements = elements;
        }

        elements.forEach((element, index) => {
            const titleElement = element.querySelector('h2, h3, .title, [class*="title"]');
            const domTitle = titleElement ? titleElement.textContent.trim() : element.textContent.trim().slice(0, 100);

            if (CONFIG.debugMode) {
                console.log(`[RP Highlighter] Element ${index}: "${domTitle}"`);
            }

            const matchedBook = findMatchingBook(domTitle);
            if (matchedBook) {
                highlightBook(element, matchedBook);
            }
        });
    }

    function init() {
        if (CONFIG.debugMode) {
            console.log('[RP Highlighter] Discovery Mode Active');
            console.log('[RP Highlighter] Run RP.getElements() to get all found elements');
            window.RP = { getElements: () => document.querySelectorAll(CONFIG.selector) };
        }

        GM_xmlhttpRequest({
            method: 'GET',
            url: MANIFEST_URL,
            onload: function(response) {
                try {
                    bookManifest = JSON.parse(response.responseText);
                    console.log(`[RP Highlighter] Loaded ${bookManifest.length} books from manifest`);

                    if (document.readyState === 'loading') {
                        document.addEventListener('DOMContentLoaded', () => setTimeout(processBooks, 500));
                    } else {
                        setTimeout(processBooks, 500);
                    }
                } catch (e) {
                    console.error('[RP Highlighter] Failed to parse manifest:', e);
                }
            },
            onerror: function(error) {
                console.error('[RP Highlighter] Failed to fetch manifest:', error);
            }
        });
    }

    init();
})();
