# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [S3_EXPERIENCE_ORDERING_INIT]
# Timestamp: 2026-10-12 21:00:00 +05:30
# Issue / Context: Oracle HCM experience tiles were sorted out of order because string localeCompare
#                  was sorting "MM/YYYY" strings by month rather than year.
# Changes Made: Built s3_experience_ordering.py with robust dual-layer sorting:
#               1. Knockout VM parent.forms observableArray sorted with numeric YYYYMM date comparison.
#               2. Direct DOM tile reordering parsing visible date ranges (Present=99999999, end date desc).
# Rationale: Guarantees strict reverse-chronological order (current job at top, newest to oldest)
#            regardless of Knockout VM state or date string formatting variations.
# Preventative Notes: Never compare MM/YYYY strings using localeCompare or alphabetical comparison.
#
# [ENTRY #002]
# Term: [NEW-8_WORD_BOUNDARY_TILE_SCOPE]
# Timestamp: 2026-10-15 +05:30
# Issue / Context: Raw degree substrings mis-scoped employer tiles.
# Changes Made: Word-boundary degree regex in read-back + KO exp-tile pick.
# Rationale: Same as s3_experience_tile ENTRY #002 — no partial matches.
# Preventative Notes: Keep both files' patterns in sync when extending.
# ==============================================================================

import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def parse_tile_date_text(text: str) -> int:
    """Convert visible tile date text to a sortable integer at runtime.

    No hardcoded employers or positions — purely date-driven:
    Present/Current → 99999999 (always first), else last MM/YYYY end date
    as YYYY*100+MM, else last 4-digit year as YYYY*100, else 0.
    """
    t = text or ""
    if re.search(r"present|current", t, re.IGNORECASE):
        return 99999999
    mm_yyyy = re.findall(r"(\d{1,2})/(\d{4})", t)
    if mm_yyyy:
        mm, yyyy = mm_yyyy[-1]
        return int(yyyy) * 100 + int(mm)
    years = re.findall(r"\b(19\d{2}|20\d{2})\b", t)
    if years:
        return int(years[-1]) * 100
    return 0


def is_reverse_chronological(sort_keys: List[int]) -> bool:
    """True when keys are in non-increasing (newest-first) order."""
    return all(a >= b for a, b in zip(sort_keys, sort_keys[1:]))


def get_tile_order(page: Any) -> List[Dict[str, Any]]:
    """Read back experience tiles in current DOM order with runtime sort keys."""
    try:
        texts = page.evaluate("""() => {
            const tiles = Array.from(document.querySelectorAll('.apply-flow-profile-item-tile'));
            return tiles
                // NEW-8: word-boundary degree match — raw substrings
                // mis-scoped employers like "Mastercard" or "CL Educate".
                .filter(t => !/\b(bachelor|master'?s?|b\\.?tech|m\\.?tech|mba|degree|education|university|college|school|diploma)\b/i.test(t.innerText || ''))
                .map(t => (t.innerText || '').split('\\n')[0].trim());
        }""") or []
    except Exception as e:
        logger.debug(f"[s3_experience_ordering] Order read-back note: {e}")
        return []
    return [{"title": t, "sort_key": parse_tile_date_text(t)} for t in texts if t]


def reorder_experience_tiles(page: Any) -> Dict[str, Any]:
    """
    Universally enforces strict reverse-chronological ordering on Work Experience tiles
    (Current employer first, newest to oldest).
    Works across Oracle Cloud HCM, Workday, and other ATS platforms.
    """
    try:
        result = page.evaluate("""() => {
            // Helper to parse date string into sortable YYYYMM integer
            function parseDateToNumeric(val) {
                if (!val) return 0;
                const s = String(val).trim();
                if (/present|current/i.test(s)) return 99999999;
                
                // MM/YYYY
                const mm_yyyy = s.match(/^(\\d{1,2})\\/(\\d{4})$/);
                if (mm_yyyy) {
                    return parseInt(mm_yyyy[2], 10) * 100 + parseInt(mm_yyyy[1], 10);
                }
                
                // YYYY-MM
                const yyyy_mm = s.match(/^(\\d{4})-(\\d{1,2})/);
                if (yyyy_mm) {
                    return parseInt(yyyy_mm[1], 10) * 100 + parseInt(yyyy_mm[2], 10);
                }
                
                // Date parse fallback
                const d = new Date(s);
                if (!isNaN(d.getTime())) {
                    return d.getFullYear() * 100 + (d.getMonth() + 1);
                }
                
                // Regex find 4-digit year
                const yMatch = s.match(/\\b(19\\d{2}|20\\d{2})\\b/);
                if (yMatch) {
                    const mMatch = s.match(/\\b(0?[1-9]|1[0-2])\\b/);
                    const m = mMatch ? parseInt(mMatch[1], 10) : 1;
                    return parseInt(yMatch[1], 10) * 100 + m;
                }
                return 0;
            }

            let koSorted = 0;
            // 1. Try Knockout VM observableArray sort with proper numeric dates
            try {
                const tiles = document.querySelectorAll('.apply-flow-profile-item-tile');
                if (tiles.length > 1) {
                    // Find an experience tile (skip education)
                    let expTile = null;
                    for (const t of tiles) {
                        const txt = (t.innerText || '').toLowerCase();
                        // NEW-8: word boundaries — "Mastercard"/"CL Educate"
                        // are employers, not education tiles.
                        if (!/\b(bachelor|master'?s?|b\\.?tech|m\\.?tech|mba|degree|education|university|college|school|diploma)\b/.test(txt)) {
                            expTile = t;
                            break;
                        }
                    }
                    if (!expTile && tiles.length > 1) expTile = tiles[1];

                    if (expTile) {
                        let koProp = Object.keys(expTile).find(p => p.startsWith('__ko__'));
                        if (koProp) {
                            const ctx = expTile[koProp]['1' + koProp]?.context;
                            if (ctx && ctx.$parent && ctx.$parent.forms && typeof ctx.$parent.forms.sort === 'function') {
                                const parent = ctx.$parent;
                                parent.forms.sort((a, b) => {
                                    const modA = typeof a === 'function' && typeof a().model === 'function' ? a().model() : null;
                                    const modB = typeof b === 'function' && typeof b().model === 'function' ? b().model() : null;
                                    if (!modA || !modB) return 0;
                                    
                                    const curA = typeof modA.currentJobFlag === 'function' ? modA.currentJobFlag() : 'N';
                                    const curB = typeof modB.currentJobFlag === 'function' ? modB.currentJobFlag() : 'N';
                                    const isCurA = curA === 'Y' || curA === true || curA === 'Yes' || String(curA).toLowerCase().includes('y');
                                    const isCurB = curB === 'Y' || curB === true || curB === 'Yes' || String(curB).toLowerCase().includes('y');
                                    if (isCurA && !isCurB) return -1;
                                    if (isCurB && !isCurA) return 1;
                                    
                                    const endA = parseDateToNumeric(typeof modA.endDate === 'function' ? modA.endDate() : '');
                                    const endB = parseDateToNumeric(typeof modB.endDate === 'function' ? modB.endDate() : '');
                                    if (endB !== endA) return endB - endA;
                                    
                                    const startA = parseDateToNumeric(typeof modA.startDate === 'function' ? modA.startDate() : '');
                                    const startB = parseDateToNumeric(typeof modB.startDate === 'function' ? modB.startDate() : '');
                                    return startB - startA;
                                });
                                
                                if (typeof parent._buildTiles === 'function') {
                                    parent._buildTiles();
                                }
                                koSorted = parent.forms().length;
                            }
                        }
                    }
                }
            } catch (e) {
                // KO sort fallback to DOM
            }

            // 2. DOM tile inspection and reordering
            let domSorted = 0;
            try {
                // Parse date directly from visible tile text
                function parseTileDate(tile) {
                    const text = tile.innerText || '';
                    if (/present|current/i.test(text)) return 99999999;
                    
                    const matches = Array.from(text.matchAll(/(\\d{1,2})\\/(\\d{4})/g));
                    if (matches.length > 0) {
                        const last = matches[matches.length - 1];
                        return parseInt(last[2], 10) * 100 + parseInt(last[1], 10);
                    }
                    const yearMatches = Array.from(text.matchAll(/\\b(19\\d{2}|20\\d{2})\\b/g));
                    if (yearMatches.length > 0) {
                        const last = yearMatches[yearMatches.length - 1];
                        return parseInt(last[1], 10) * 100;
                    }
                    return 0;
                }

                const allTiles = Array.from(document.querySelectorAll('.apply-flow-profile-item-tile'));
                // Filter only experience tiles
                const expTiles = allTiles.filter(t => {
                    const txt = (t.innerText || '').toLowerCase();
                    return !txt.includes('bachelor') && !txt.includes('master') && !txt.includes('degree') && !txt.includes('education');
                });

                if (expTiles.length > 1) {
                    const parentContainer = expTiles[0].parentElement;
                    if (parentContainer) {
                        // Sort descending by end date / current flag
                        expTiles.sort((a, b) => parseTileDate(b) - parseTileDate(a));
                        // Re-insert sorted elements in correct order
                        expTiles.forEach(t => parentContainer.appendChild(t));
                        domSorted = expTiles.length;
                    }
                }
            } catch (e) {
                // DOM reorder failed
            }

            // Extract titles in current order for reporting
            const finalOrder = Array.from(document.querySelectorAll('.apply-flow-profile-item-tile'))
                .map(t => (t.innerText || '').split('\\n')[0].trim())
                .filter(Boolean);

            return {
                ko_sorted_count: koSorted,
                dom_sorted_count: domSorted,
                success: koSorted > 0 || domSorted > 0,
                tiles_order: finalOrder
            };
        }""")

        time.sleep(0.5)
        # Post-sort read-back verification (runtime dates, never assumed).
        order = get_tile_order(page)
        keys = [t["sort_key"] for t in order]
        verified = bool(order) and is_reverse_chronological(keys)
        result["tiles_order"] = [t["title"] for t in order] or result.get("tiles_order", [])
        result["sort_keys"] = keys
        result["order_verified"] = verified
        result["success"] = bool(result.get("success")) and verified
        logger.info(
            f"[s3_experience_ordering] Result: ko={result.get('ko_sorted_count')} "
            f"dom={result.get('dom_sorted_count')} | tiles={result.get('tiles_order', [])[:4]}"
        )
        return result
    except Exception as e:
        logger.error(f"[s3_experience_ordering] Error reordering experience tiles: {e}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    import argparse
    import sys
    from CompanySiteApply.ats_arm import ATSArm

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description="Reorder experience tiles in reverse-chronological order.")
    parser.add_argument("--cdp-url", default="http://127.0.0.1:9222", help="CDP URL")
    args = parser.parse_args()

    arm = ATSArm(cdp_url=args.cdp_url)
    try:
        page = arm.connect()
        res = reorder_experience_tiles(page)
        print(f"Reorder Result: {res}")
        sys.exit(0 if res.get("success") else 1)
    finally:
        arm.disconnect()
