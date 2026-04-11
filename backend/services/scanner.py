import io
import httpx
import pdfplumber
from bs4 import BeautifulSoup

VEGAN_KEYWORDS = [
    # English
    "vegan", "plant-based", "plant based", "dairy-free", "dairy free",
    "no meat", "meat-free", "cruelty-free", "animal-free",
    # German
    "vegan", "pflanzlich", "ohne fleisch", "ohne milch", "laktosefrei",
    "tierfrei", "fleischlos", "vegetarisch",
]


async def scan_restaurant(restaurant_id: str, website: str) -> dict:
    dishes = []

    if website:
        dishes += await _scan_website(website)

    return {
        "restaurant_id": restaurant_id,
        "dishes": dishes,
    }


async def _scan_website(url: str) -> list[dict]:
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            response = await client.get(url)
            content_type = response.headers.get("content-type", "")

            if "pdf" in content_type:
                return _scan_pdf(response.content, source=url)

            soup = BeautifulSoup(response.text, "html.parser")

            # Look for linked PDFs on the page
            pdf_dishes = []
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if href.lower().endswith(".pdf"):
                    pdf_url = href if href.startswith("http") else url.rstrip("/") + "/" + href.lstrip("/")
                    try:
                        pdf_resp = await client.get(pdf_url)
                        pdf_dishes += _scan_pdf(pdf_resp.content, source=pdf_url)
                    except Exception:
                        pass

            # Scan page text
            text = soup.get_text(separator=" ").lower()
            page_dishes = _extract_dishes_from_text(text, source=url)

            return pdf_dishes + page_dishes
    except Exception:
        return []


def _scan_pdf(content: bytes, source: str) -> list[dict]:
    dishes = []
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                text = (page.extract_text() or "").lower()
                dishes += _extract_dishes_from_text(text, source=source)
    except Exception:
        pass
    return dishes


def _extract_dishes_from_text(text: str, source: str) -> list[dict]:
    dishes = []
    lines = text.split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue
        matched_keywords = [kw for kw in VEGAN_KEYWORDS if kw in line]
        if matched_keywords:
            confidence = min(1.0, 0.4 + len(matched_keywords) * 0.2)
            dishes.append({
                "name": line[:120],
                "confidence": round(confidence, 2),
                "matched_keywords": matched_keywords,
                "source": source,
            })
    return dishes
