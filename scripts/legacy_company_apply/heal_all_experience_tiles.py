import time
import re
import os
import json
from playwright.sync_api import sync_playwright

def parse_resume(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    exp_section = re.search(r'## PROFESSIONAL EXPERIENCE(.*?)(?=## EDUCATION|\Z)', content, re.DOTALL)
    if not exp_section:
        return {}
    
    text = exp_section.group(1)
    roles = re.split(r'### \*\*(.*?)\*\*', text)
    experiences = {}
    
    for i in range(1, len(roles), 2):
        emp_name = roles[i].strip()
        body = roles[i+1]
        
        # Extract location: e.g. *Bangalore, India | March 2026 - Present*
        loc_match = re.search(r'\*(.*?)\|(.*?)\*', body)
        city = "Noida"
        country = "India"
        if loc_match:
            loc_str = loc_match.group(1).strip()
            parts = [p.strip() for p in loc_str.split(',')]
            if len(parts) >= 2:
                city = parts[0]
                country = parts[1]
            elif len(parts) == 1:
                city = parts[0]
        else:
            if "irctc" in emp_name.lower() or "cl educate" in emp_name.lower():
                city = "New Delhi"
            elif "cognizant" in emp_name.lower() or "infosys" in emp_name.lower():
                city = "Bengaluru"
        
        # Standardize city names
        if "bangalore" in city.lower():
            city = "Bengaluru"
        elif "delhi" in city.lower():
            city = "Delhi"
            
        # Extract bullets
        bullets = [re.sub(r'^[•\-\*]\s*', '', line).strip() for line in body.split('\n') if re.match(r'^\s*[•\-\*]\s+', line)]
        experiences[emp_name] = {
            'city': city,
            'country': country,
            'bullets': bullets
        }
    return experiences

def match_experience(emp_name, exps):
    low = emp_name.lower()
    for exp_k, exp_v in exps.items():
        k_low = exp_k.lower()
        if k_low in low or low in k_low:
            return exp_v
        # Keyword matching
        for word in ["cognizant", "infosys", "tata", "tcs", "cl educate", "navyug", "adobe", "ibm", "irctc", "nec"]:
            if word in low and word in k_low:
                return exp_v
    return None

def main():
    resume_path = r"profiles/udaysagar_kandpal/company_site_apply/resume.md"
    exps = parse_resume(resume_path)
    print(f"Loaded {len(exps)} experiences from {resume_path}")

    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp("http://127.0.0.1:9222")
    ctx = browser.contexts[0]
    pages = [p for p in ctx.pages if "jpmc.fa.oraclecloud.com" in p.url and "apply" in p.url]
    if not pages:
        print("Error: Oracle apply page not found!")
        return
    page = pages[0]
    print(f"Connected to page: {page.url}")

    # Ensure we are on Section 3
    if "section/3" not in page.url:
        print(f"Navigating to section 3 from {page.url}...")
        sec3_link = page.locator("a:has-text('3'), button:has-text('3')").first
        if sec3_link.count() > 0:
            sec3_link.click()
            time.sleep(2.0)

    # 1. Inspect all tiles on Section 3
    tiles = page.locator('.apply-flow-profile-item-tile, .timeline-item')
    count = tiles.count()
    print(f"Total tiles on Section 3: {count}")

    # Process all experience tiles (indices 1 to count-1)
    for idx in range(1, count):
        tiles = page.locator('.apply-flow-profile-item-tile, .timeline-item')
        if idx >= tiles.count():
            break
        tile = tiles.nth(idx)
        tile_text = tile.inner_text().replace('\n', ' | ')
        print(f"\n---------------------------------------------")
        print(f"Processing Tile {idx}: {tile_text[:75]}")

        # Check if already has edit button
        edit_btn = tile.locator(".apply-flow-profile-item-tile__edit-item-icon, button[aria-label*='Edit' i]").first
        if edit_btn.count() == 0:
            print(f"Warning: No edit button found on tile {idx}")
            continue

        tile.scroll_into_view_if_needed()
        time.sleep(0.4)
        edit_btn.click(force=True)
        time.sleep(1.2)

        # Check if modal opened
        emp_inp = page.locator("input[id^='employerName']:visible").first
        if emp_inp.count() == 0:
            print(f"Could not open edit modal for tile {idx}")
            continue

        emp_val = emp_inp.input_value().strip()
        print(f"Modal opened for Employer: '{emp_val}'")

        exp_data = match_experience(emp_val, exps)
        city_target = exp_data['city'] if exp_data else "Noida"
        bullets_target = exp_data['bullets'] if exp_data else []

        # 1. Employer Country: India
        country_inp = page.locator("input[id^='countryCode']:visible").first
        if country_inp.count() > 0 and country_inp.input_value().strip() != "India":
            print("Setting Country to India...")
            c_toggle = page.locator("button[id^='countryCode'][id$='-toggle-button']:visible").first
            if c_toggle.count() > 0:
                c_toggle.click()
                time.sleep(0.6)
                page.evaluate("""() => {
                    const items = Array.from(document.querySelectorAll('.cx-select__list-item, [role="gridcell"], [role="option"]'))
                        .filter(el => el.offsetWidth > 0 || el.offsetHeight > 0);
                    const match = items.find(i => i.innerText.trim().toLowerCase() === "india");
                    if (match) match.click();
                }""")
                time.sleep(0.4)
        else:
            print("Country already set to India.")

        # 2. Employer City
        city_inp = page.locator("input[name='employerCity']:visible, input[id^='employerCity']:visible").first
        if city_inp.count() > 0:
            cur_city = city_inp.input_value().strip()
            if not cur_city:
                print(f"Setting City to '{city_target}'...")
                city_inp.fill(city_target)
                city_inp.dispatch_event("input")
                city_inp.dispatch_event("change")
            else:
                print(f"City already set to '{cur_city}'.")

        # 3. Internal Candidate: No
        no_btn = page.locator("button[role='radio']:has-text('No'):visible, button.cx-select-pill-section:has-text('No'):visible, button:has-text('No'):visible").first
        if no_btn.count() > 0:
            is_active = "active" in (no_btn.get_attribute("class") or "").lower() or no_btn.get_attribute("aria-pressed") == "true"
            if not is_active:
                no_btn.click()
                print("Clicked Internal: No")
            else:
                print("Internal 'No' already active.")

        # 4. Achievements with bullet points
        ta = page.locator("textarea[name='achievements']:visible, textarea[id^='achievements']:visible").first
        if ta.count() > 0:
            cur_ta = ta.input_value().strip()
            # If already has bullets and is non-empty, check format
            if bullets_target:
                formatted_text = "\n\n".join([f"• {b}" for b in bullets_target])
                ta.fill(formatted_text)
                ta.dispatch_event("input")
                ta.dispatch_event("change")
                print(f"Filled {len(bullets_target)} bullet points from resume.")
            elif cur_ta:
                lines = [re.sub(r'^[•\-\*\s]+', '', l).strip() for l in cur_ta.split('\n') if l.strip()]
                formatted_text = "\n\n".join([f"• {l}" for l in lines if l])
                ta.fill(formatted_text)
                ta.dispatch_event("input")
                ta.dispatch_event("change")
                print(f"Formatted existing text with {len(lines)} bullet points.")

        # 5. Click SAVE
        save_btn = page.locator("button.save-btn:visible, button:has-text('SAVE'):visible").first
        if save_btn.count() > 0:
            save_btn.click()
            time.sleep(1.5)
            # Wait for modal to hide
            try:
                page.wait_for_selector("input[id^='employerName']:visible", state="hidden", timeout=4000)
                print(f"Tile {idx} saved successfully.")
            except Exception as e:
                print(f"Warning after saving tile {idx}: {e}")

        time.sleep(0.5)

    print("\n=============================================")
    print("All Experience Tiles processed! Applying reverse-chronological reordering...")
    from CompanySiteApply.nails.oracle.jpmc_nail import JPMCNail
    nail = JPMCNail()
    nail.reorder_experience_tiles(page)
    time.sleep(1.0)
    page.screenshot(path="section_3_all_tiles_healed.png")
    print("Screenshot saved to section_3_all_tiles_healed.png")

    browser.close()
    pw.stop()

if __name__ == "__main__":
    main()
