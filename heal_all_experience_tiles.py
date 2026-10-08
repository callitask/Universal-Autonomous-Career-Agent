import time
import json
import re
from playwright.sync_api import sync_playwright

RESUME_BULLETS = {
    "cognizant": [
        "Establish and enforce IT governance standards across banking platform delivery, ensuring adherence to enterprise architecture frameworks and regulatory compliance requirements.",
        "Lead a cross-functional engineering team using smart sprint management practices to deliver scalable banking solutions for a prominent US-based financial services client.",
        "Coordinate delivery priorities across banking configurations and core infrastructure activities, aligning technical execution with client-specific operational requirements and stakeholder expectations.",
        "Apply senior-level ownership across team delivery, banking configuration, infrastructure oversight, and cross-regional execution for complex financial services environments.",
        "Implement strict infrastructure monitoring and end-to-end management protocols across core banking environments to maintain high platform availability and operational resilience.",
        "Direct the configuration and deployment of critical product catalogs, banking services, equipment profiles, and intricate fee schedules, leveraging in-depth knowledge of banking domain standards.",
        "Oversee multi-regional banking fee configurations and critical fee structures, including MMSC charges, across European markets including Poland, Germany, and the United Kingdom."
    ],
    "infosys": [
        "Managed stakeholder engagement and governance across multi-geography teams, driving alignment between technical delivery and business objectives at the senior leadership level.",
        "Architected and implemented robust enterprise integration solutions using Java, Spring Boot, Apache Camel (EIPs), and IBM MQ, supporting 10 million daily transactions with 99.99% delivery success.",
        "Modernized system architecture by building scalable microservices and standardizing integration patterns using enterprise architecture frameworks, reducing system fragmentation and cutting development turnaround for new integrations.",
        "Drove operational excellence by mentoring engineering staff and conducting Agile coaching, improving team velocity and establishing consistent, reusable orchestration patterns.",
        "Managed full-cycle technical recruitment, evaluating profiles, conducting technical interviews, and onboarding talent aligned with client and project delivery standards.",
        "Directed a cross-functional team of 20 engineers in the end-to-end delivery of mission-critical projects for a leading US telecom provider, ensuring on-time delivery across 4 consecutive major releases.",
        "Spearheaded global technical roadmaps across US and India-based teams, aligning complex telecom offerings with long-term client strategic goals and enterprise architecture principles.",
        "Designed data architecture strategies for high-volume telecom data processing leveraging Cassandra and Oracle, enabling analytics-ready data flows and reducing integration errors significantly."
    ],
    "tcs": [
        "Supported client architectural reviews, designing scalable decision-making models for retail banking while ensuring strict regulatory adherence and data integrity.",
        "Spearheaded technical recruitment by evaluating 30-40 candidates and conducting up to 10 technical interviews monthly.",
        "Reduced manual deployment efforts, accelerated release velocity, and maintained 99.95%+ platform availability across 10+ microservices.",
        "Architected the refactoring of a legacy data processing module by optimizing data access patterns and introducing strategic caching mechanisms.",
        "Engineered autonomous Java Spring Boot microservices and Apache Spark (RDD) data pipelines for a premier European bank, processing over 200GB+ of daily financial data (currency rates, MRE).",
        "Built resilient CI/CD pipelines utilizing Jenkins, GitLab, and Bitbucket, orchestrating zero-downtime deployments to OpenShift Production and Disaster Recovery (DR) environments."
    ],
    "tata": [
        "Supported client architectural reviews, designing scalable decision-making models for retail banking while ensuring strict regulatory adherence and data integrity.",
        "Spearheaded technical recruitment by evaluating 30-40 candidates and conducting up to 10 technical interviews monthly.",
        "Reduced manual deployment efforts, accelerated release velocity, and maintained 99.95%+ platform availability across 10+ microservices.",
        "Architected the refactoring of a legacy data processing module by optimizing data access patterns and introducing strategic caching mechanisms.",
        "Engineered autonomous Java Spring Boot microservices and Apache Spark (RDD) data pipelines for a premier European bank, processing over 200GB+ of daily financial data (currency rates, MRE).",
        "Built resilient CI/CD pipelines utilizing Jenkins, GitLab, and Bitbucket, orchestrating zero-downtime deployments to OpenShift Production and Disaster Recovery (DR) environments."
    ],
    "cl educate": [
        "Architected and maintained 200+ RESTful APIs for the 'aspiration.al' platform, supporting over 200,000 active users across web and mobile ecosystems.",
        "Developed an optimized Java parsing engine that reduced question paper processing cycles from 120+ hours to under 5 minutes, significantly automating publishing workflows.",
        "Established comprehensive monitoring, centralized logging, and proactive error-handling mechanisms to elevate API reliability and maintainability."
    ],
    "navyug": [
        "Engineered backend services for the Zaky application using Spring Boot, delivering secure, maintainable, and high-throughput REST APIs.",
        "Transitioned legacy monolithic components to microservice-ready architectures, cutting system downtime by 50% and enhancing architectural scalability.",
        "Profiled and optimized database queries to efficiently sustain rapid user traffic growth."
    ],
    "adobe": [
        "Executed regression testing, defect validation, and test automation initiatives for Adobe FrameMaker, improving release stability and cycle time.",
        "Collaborated with geographically distributed product teams to enhance cross-functional engineering processes and deliver quality releases."
    ],
    "ibm": [
        "Conducted system analysis, health checks, and performance monitoring for high-volume enterprise platforms, ensuring operational continuity and minimizing downtime.",
        "Applied process optimization techniques to improve incident turnaround times and service delivery standards."
    ],
    "irctc": [
        "Participated across the full Software Development Life Cycle (SDLC), implementing coding standards and collaborative version control practices.",
        "Developed a web application module utilizing Java EE, enhancing core system functionality and end-user workflow efficiency."
    ],
    "nec": [
        "Collaborated with engineering peers and mentors across structured technical problem-solving sessions, strengthening core software engineering fundamentals.",
        "Explored Moodle.org architecture to design and optimize e-learning platforms, enhancing digital learning experiences and system workflow efficiency.",
        "Gained hands-on experience in Content Management Systems (CMS) and Learning Management Systems (LMS)."
    ]
}

def get_bullets_for_employer(emp_name):
    low = emp_name.lower()
    for key, bullets in RESUME_BULLETS.items():
        if key in low:
            return bullets
    return None

def main():
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp('http://127.0.0.1:9222')
    ctx = browser.contexts[0]
    pages = [p for p in ctx.pages if 'jpmc.fa.oraclecloud.com' in p.url and 'apply' in p.url]
    if not pages:
        print("Error: Oracle apply page not found!")
        return
    page = pages[0]
    print(f"Connected to page: {page.url}")
    
    # Check if education or experience section
    tiles = page.locator('.apply-flow-profile-item-tile, .timeline-item')
    total_tiles = tiles.count()
    print(f"Found {total_tiles} total tiles on Section 3.")
    
    # Process each experience tile (skip index 0 which is Education)
    for i in range(1, total_tiles):
        # Re-query tiles as DOM re-renders after each save
        tiles = page.locator('.apply-flow-profile-item-tile, .timeline-item')
        if i >= tiles.count():
            print(f"Index {i} exceeds current tile count {tiles.count()}, breaking.")
            break
            
        tile = tiles.nth(i)
        tile_text = tile.inner_text().replace('\n', ' | ')
        print(f"\n==========================================")
        print(f"Processing Tile {i}: {tile_text[:80]}")
        
        # Scroll tile into view before interacting
        tile.scroll_into_view_if_needed()
        time.sleep(0.5)
        
        # Click edit pencil icon on this tile
        edit_btn = tile.locator('.apply-flow-profile-item-tile__edit-item-icon, button[aria-label*="Edit" i]').first
        if edit_btn.count() == 0 or not edit_btn.is_visible():
            print(f"Warning: Edit button not found or invisible on tile {i}")
            continue
            
        edit_btn.click(force=True)
        time.sleep(1.5)
        
        # Check if form opened
        emp_input = page.locator("input[id^='employerName']:visible").first
        if emp_input.count() == 0:
            print(f"Error: Experience form did not open for tile {i}")
            continue
            
        emp_name = emp_input.input_value().strip()
        print(f"Form opened for Employer: '{emp_name}'")
        
        # 1. Country: India
        country_inp = page.locator("input[id^='countryCode']:visible").first
        if country_inp.count() > 0:
            cur_country = country_inp.input_value().strip()
            if cur_country != "India":
                print(f"Current Country: '{cur_country}', setting to India...")
                country_inp.fill("India")
                time.sleep(1.0)
                # Click dropdown option
                selected = page.evaluate("""() => {
                    const items = Array.from(document.querySelectorAll('.cx-select__list-item, .cx-select-list-item, [role="gridcell"], [role="option"], li'))
                        .filter(el => (el.offsetWidth > 0 || el.offsetHeight > 0) && el.innerText.trim() === "India");
                    if (items.length > 0) {
                        items[0].click();
                        return true;
                    }
                    return false;
                }""")
                time.sleep(0.5)
                print(f"Country India selection clicked: {selected}")
            else:
                print("Country is already set to India.")
                
        # 2. City
        city_inp = page.locator("input[id^='employerCity']:visible").first
        if city_inp.count() > 0:
            cur_city = city_inp.input_value().strip()
            if not cur_city:
                low_emp = emp_name.lower()
                if "infosys" in low_emp or "cognizant" in low_emp:
                    target_city = "Bengaluru"
                elif any(k in low_emp for k in ["tcs", "tata", "navyug", "adobe", "ibm", "nec"]):
                    target_city = "Noida"
                else:
                    target_city = "Delhi"
                print(f"Setting City to '{target_city}'...")
                city_inp.fill(target_city)
                city_inp.dispatch_event("input")
                city_inp.dispatch_event("change")
            else:
                print(f"City already set to '{cur_city}'.")
                
        # 3. Internal Candidate: No
        no_pill = page.locator(".standard-apply-flow-profile-item:has(input[id^='employerName']) button:has-text('No')").first
        if no_pill.count() > 0 and no_pill.is_visible():
            is_active = "active" in (no_pill.get_attribute("class") or "").lower() or no_pill.get_attribute("aria-pressed") == "true"
            if not is_active:
                no_pill.click()
                print("Clicked Internal Candidate: No")
            else:
                print("Internal Candidate 'No' already active.")
                
        # 4. Achievements / Description
        ach_area = page.locator("textarea[id^='achievements']:visible").first
        if ach_area.count() > 0:
            bullets = get_bullets_for_employer(emp_name)
            if bullets:
                formatted_text = "\n\n".join([f"\u2022 {b}" for b in bullets])
                ach_area.fill(formatted_text)
                ach_area.dispatch_event("input")
                ach_area.dispatch_event("change")
                print(f"Formatted achievements with {len(bullets)} authentic bullet points from resume.")
            else:
                cur_text = ach_area.input_value().strip()
                if cur_text:
                    lines = [re.sub(r'^[•\-\*\s]+', '', l).strip() for l in cur_text.split('\n') if l.strip()]
                    formatted_text = "\n\n".join([f"\u2022 {l}" for l in lines if l])
                    ach_area.fill(formatted_text)
                    ach_area.dispatch_event("input")
                    ach_area.dispatch_event("change")
                    print(f"Formatted existing text with {len(lines)} bullet points.")
                    
        # 5. Save Button
        save_btn = page.locator(".standard-apply-flow-profile-item:has(input[id^='employerName']) button:has-text('SAVE')").first
        if save_btn.count() > 0 and save_btn.is_visible():
            save_btn.click()
            print("Clicked SAVE button, waiting for form to close...")
            try:
                page.wait_for_selector("input[id^='employerName']:visible", state="hidden", timeout=5000)
                print(f"Successfully saved and closed tile {i} ({emp_name})")
            except Exception as e:
                print(f"Warning: Form did not close after SAVE: {e}")
                # Check for errors
                errs = page.locator(".cx-messages__message--error:visible, .cx-form-control__error-message:visible").all_inner_texts()
                if errs:
                    print(f"Errors present on form: {errs}")
                    return
        time.sleep(1.0)
        
    print("\n==========================================")
    print("All Experience Tiles processed. Final inspection:")
    
    # Verify open forms count
    open_forms = page.locator("input[id^='employerName']:visible, input[id^='school']:visible").count()
    print(f"Open forms: {open_forms} (expected: 0)")
    
    # Check for any validation error messages on page
    errors = page.locator(".cx-messages__message--error:visible, .cx-form-control__error-message:visible").all_inner_texts()
    print(f"Active errors on Section 3: {errors}")
    
    # Summary of tiles
    tiles = page.locator('.apply-flow-profile-item-tile, .timeline-item')
    print(f"Total tiles rendered: {tiles.count()}")
    for idx in range(tiles.count()):
        print(f"  Tile {idx}: {tiles.nth(idx).inner_text().replace(chr(10), ' | ')[:80]}")
        
    browser.close()
    pw.stop()

if __name__ == "__main__":
    main()
