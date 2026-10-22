"""The ONLY pages the bot may use. Nothing else is ever crawled."""

SOURCES = [
    {"type": "Clinic profile", "url": "https://www.placidway.com/profile/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center"},
    {"type": "Treatment package", "url": "https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC"},
    {"type": "Treatment package", "url": "https://www.placidway.com/package/7902/Alternative-Adrenal-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC"},
    {"type": "Treatment package", "url": "https://www.placidway.com/package/7901/Alternative-Anal-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC"},
    {"type": "Clinic videos", "url": "https://www.placidway.com/profile-videos/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center"},
    {"type": "Price list", "url": "https://www.placidway.com/price-list/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center"},
    {"type": "Price comparison", "url": "https://www.placidway.com/search-medical-pricings/Alternative-Medicine/All/1"},
]
ALLOWED_URLS = {s["url"] for s in SOURCES}

QUOTE_URL = "https://www.placidway.com/request-info"
CONTACT_EMAIL = "info@placidway.com"
CONTACT_PHONE = "+1-888-296-6664"
