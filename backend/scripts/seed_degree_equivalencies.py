
import asyncio
import logging
import sys
from pathlib import Path

import pycountry
import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.db.session import SessionLocal
from app.models.rules import CountryDegreeEquivalency

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

URL = "https://www.ucl.ac.uk/prospective-students/international/graduate-equivalent-international-qualifications-202425"
TABLE_HEADERS = ["Second Higher", "Second Lower", "Above Honours"]
UK_CLASS_MAP = {
    "Second Higher": "UPPER_SECOND",
    "Second Lower": "LOWER_SECOND",
    "Above Honours": "FIRST",
}


def get_country_code(country_name: str) -> str | None:
    country_name_map = {
        "Bolivia": "BOL",
        "Brunei": "BRN",
        "Caribbean / West Indies": None,  # This is a region, not a country
        "Congo (DR)": "COD",
        "Cyprus (Greek Cypriot and Turkish Cypriot communities)": "CYP",
        "Czech Republic": "CZE",
        "Hong Kong (SAR)": "HKG",
        "Iran": "IRN",
        "Ivory Coast": "CIV",
        "Macau (SAR)": "MAC",
        "Moldova": "MDA",
        "Myanmar (Burma)": "MMR",
        "South Korea": "KOR",
        "Swaziland/Eswatini": "SWZ",
        "Syria": "SYR",
        "Taiwan": "TWN",
        "Tanzania": "TZA",
        "Trinidad & Tobago": "TTO",
        "Turkey (including Turkish sector of Cyprus)": "TUR",
        "United Arab Emirates (UAE)": "ARE",
        "United States of America": "USA",
        "Venezuela": "VEN",
        "Vietnam": "VNM",
        "Russia": "RUS",
    }
    if country_name in country_name_map:
        return country_name_map[country_name]
    try:
        country = pycountry.countries.get(name=country_name)
        if country:
            return country.alpha_3
    except Exception:
        return None
    return None


async def seed_equivalencies():
    logger.info("Starting to seed degree equivalencies.")
    db: Session = SessionLocal()
    try:
        logger.info("Truncating country_degree_equivalencies table.")
        db.query(CountryDegreeEquivalency).delete()
        db.commit()

        logger.info(f"Fetching data from {URL}")
        response = requests.get(URL)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")

        for header_text in TABLE_HEADERS:
            uk_class = UK_CLASS_MAP[header_text]
            logger.info(f"Processing table for uk_class: {uk_class}")
            header = soup.find("h2", string=header_text)
            if not header:
                logger.warning(f"Could not find table for header: {header_text}")
                continue

            table = header.find_next_sibling("table")
            if not table:
                logger.warning(f"Could not find table for header: {header_text}")
                if header_text == "Above Honours":
                    print(header.find_next_sibling())
                continue

            tbody = table.find("tbody")
            rows = tbody.find_all("tr") if tbody else table.find_all("tr")

            for row in rows:
                cells = row.find_all("td")
                if len(cells) == 2:
                    country_name = cells[0].text.strip()
                    requirement_html = cells[1].decode_contents().strip()
                    country_code = get_country_code(country_name)

                    if not country_code:
                        logger.warning(f"Could not find country code for: {country_name}")
                        continue

                    equivalency = CountryDegreeEquivalency(
                        country_code=country_code,
                        country_name=country_name,
                        uk_class=uk_class,
                        requirement={"html": requirement_html},
                        source_url=URL,
                    )
                    db.add(equivalency)

        db.commit()
        logger.info("Successfully seeded degree equivalencies.")

    except Exception as e:
        db.rollback()
        logger.error(f"An error occurred: {e}")
    finally:
        db.close()


def main():
    """Main function for degree equivalencies seeding"""
    asyncio.run(seed_equivalencies())

if __name__ == "__main__":
    main()
