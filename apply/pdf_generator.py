import markdown as md_lib
from pathlib import Path
from playwright.async_api import async_playwright

TEMPLATE_PATH = Path(__file__).parent.parent / "templates" / "cv_template.html"

async def generate_pdf(cv_markdown: str, output_path: str) -> str:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    html_content = md_lib.markdown(cv_markdown, extensions=["tables", "fenced_code"])
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    full_html = template.replace("{{CONTENT}}", html_content)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(full_html, wait_until="load")
        await page.pdf(path=output_path, format="A4", margin={"top": "20mm", "bottom": "20mm", "left": "15mm", "right": "15mm"})
        await browser.close()
    return output_path
