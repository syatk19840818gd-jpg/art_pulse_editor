from phase1_exhibitions_text_utils import should_include_target_year_page

tests = [
    "https://arcadiamissa.com/condo-2025-243-luz-roland-ross",
    "https://arcadiamissa.com/condo-2025-veda",
]

for url in tests:
    ok, reason = should_include_target_year_page(page_url=url, html="", target_year=2025)
    print(url)
    print("ok:", ok, "reason:", reason)
    print("---")