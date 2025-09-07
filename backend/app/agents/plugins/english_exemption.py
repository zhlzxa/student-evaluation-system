from __future__ import annotations

from typing import Annotated
from sqlalchemy.orm import Session
from semantic_kernel.functions import kernel_function

from app.db.session import SessionLocal
from app.models.rules import EnglishRule


class EnglishExemptionPlugin:
    """Standardized English exemption checking plugin.
    
    This plugin provides deterministic logic for checking English language exemptions
    based on standardized country lists stored in the database, rather than relying
    on semantic understanding by the LLM.
    """

    def __init__(self):
        self._cached_rules = None

    def _get_english_rules(self) -> EnglishRule | None:
        """Get the latest English rules from database with caching."""
        if self._cached_rules is None:
            db: Session = SessionLocal()
            try:
                self._cached_rules = db.query(EnglishRule).order_by(EnglishRule.id.desc()).first()
            finally:
                db.close()
        return self._cached_rules

    @kernel_function(description="Check if a nationality grants English language exemption.")
    def check_nationality_exemption(
        self,
        nationality: Annotated[str, "The applicant's nationality (e.g., 'British', 'American', 'Canadian')"],
    ) -> Annotated[dict, "Returns {is_exempt: bool, matched_country: str|None, reason: str}"]:
        """Check if the given nationality is in the exemption list."""
        rules = self._get_english_rules()
        if not rules or not rules.nationality_exempt_countries:
            return {
                "is_exempt": False,
                "matched_country": None,
                "reason": "No English exemption rules found in database"
            }

        nationality_lower = nationality.lower().strip()
        
        # Direct matching attempts
        for country in rules.nationality_exempt_countries:
            country_lower = country.lower()
            
            # Exact match
            if nationality_lower == country_lower:
                return {
                    "is_exempt": True,
                    "matched_country": country,
                    "reason": f"Nationality '{nationality}' matches exempt country '{country}'"
                }
            
            # Common nationality variations - comprehensive mapping
            nationality_mappings = {
                # Major English-speaking countries
                "british": ["united kingdom", "uk", "england", "scotland", "wales", "northern ireland"],
                "english": ["united kingdom", "uk", "england"],
                "scottish": ["united kingdom", "uk", "scotland"],
                "welsh": ["united kingdom", "uk", "wales"],
                "northern irish": ["united kingdom", "uk", "northern ireland"],
                "american": ["united states of america", "usa", "us"],
                "australian": ["australia"],
                "canadian": ["canada"],
                "irish": ["ireland"],
                "new zealander": ["new zealand"],
                "maltese": ["malta"],
                
                # Caribbean countries
                "jamaican": ["jamaica"],
                "trinidadian": ["trinidad and tobago"],
                "tobagonian": ["trinidad and tobago"],
                "barbadian": ["barbados"],
                "bahamian": ["the bahamas", "bahamas"],
                "antiguan": ["antigua and barbuda"],
                "barbudan": ["antigua and barbuda"],
                "belizean": ["belize"],
                "dominican": ["dominica"],  # Note: different from Dominican Republic
                "grenadian": ["grenada"],
                "guyanese": ["guyana"],
                "kittitian": ["st kitts and nevis"],
                "nevisian": ["st kitts and nevis"],
                "saint lucian": ["st lucia"],
                "vincentian": ["st vincent and the grenadines"],
                
                # African countries  
                "south african": ["south africa"],
                "kenyan": ["kenya"],
                "ugandan": ["uganda"],
                "tanzanian": ["tanzania"],
                "zambian": ["zambia"],
                "zimbabwean": ["zimbabwe"],
                "malawian": ["malawi"],
                "botswanan": ["botswana"],
                "gambian": ["gambia"],
                "ghanaian": ["ghana"],
                "nigerian": ["nigeria"],
                "cameroonian": ["cameroon"],
                "swazi": ["swaziland"],
                "mauritian": ["mauritius"],
                
                # Asian/Pacific countries
                "singaporean": ["singapore"],
                "fijian": ["fiji"],
                
                # European
                "dutch": ["the netherlands", "netherlands"],
                
                # British territories (specific for nationality exemption)
                "british overseas territory citizen": ["the british overseas territories"],
                "overseas territory citizen": ["the british overseas territories"],
            }
            
            if nationality_lower in nationality_mappings:
                for country_variant in nationality_mappings[nationality_lower]:
                    for country in rules.nationality_exempt_countries:
                        country_lower_db = country.lower()
                        if country_variant in country_lower_db or country_lower_db in country_variant:
                            return {
                                "is_exempt": True,
                                "matched_country": country,
                                "reason": f"Nationality '{nationality}' corresponds to exempt country '{country}'"
                            }
        
        return {
            "is_exempt": False,
            "matched_country": None,
            "reason": f"Nationality '{nationality}' not found in exempt countries list"
        }

    @kernel_function(description="Check if a degree country grants English language exemption.")
    def check_degree_exemption(
        self,
        degree_country: Annotated[str, "Country where the degree was obtained (e.g., 'United Kingdom', 'Canada', 'Australia')"],
        institution_name: Annotated[str, "Name of the institution (optional, used for additional context)"] = "",
    ) -> Annotated[dict, "Returns {is_exempt: bool, matched_country: str|None, conditions: str|None, reason: str}"]:
        """Check if the degree country is in the exemption list."""
        rules = self._get_english_rules()
        if not rules or not rules.degree_obtained_exempt_countries:
            return {
                "is_exempt": False,
                "matched_country": None,
                "conditions": None,
                "reason": "No English degree exemption rules found in database"
            }

        country_lower = degree_country.lower().strip()
        
        # Direct matching attempts
        for country in rules.degree_obtained_exempt_countries:
            country_lower_db = country.lower()
            
            # Exact match or partial match for complex names
            if (country_lower == country_lower_db or 
                country_lower in country_lower_db or 
                country_lower_db in country_lower):
                
                # Check for special conditions
                conditions = None
                if hasattr(rules, 'levels') and rules.levels:
                    degree_conditions = rules.levels.get('degree_exempt_conditions', {})
                    conditions = degree_conditions.get(country)
                
                return {
                    "is_exempt": True,
                    "matched_country": country,
                    "conditions": conditions,
                    "reason": f"Degree country '{degree_country}' matches exempt country '{country}'" + 
                             (f" with conditions: {conditions}" if conditions else "")
                }
        
        # Common country name variations - comprehensive mapping
        country_mappings = {
            # English-speaking major countries
            "uk": "United Kingdom",
            "britain": "United Kingdom",
            "great britain": "United Kingdom", 
            "england": "United Kingdom",
            "scotland": "United Kingdom",
            "wales": "United Kingdom",
            "northern ireland": "United Kingdom",
            "usa": "United States of America",
            "us": "United States of America",
            "america": "United States of America",
            "united states": "United States of America",
            "australia": "Australia",
            "canada": "Canada",
            "ireland": "Ireland",
            "new zealand": "New Zealand",
            "malta": "Malta",
            
            # Caribbean variations
            "jamaica": "Jamaica",
            "trinidad": "Trinidad and Tobago",
            "tobago": "Trinidad and Tobago",
            "barbados": "Barbados",
            "bahamas": "The Bahamas",
            "antigua": "Antigua and Barbuda",
            "barbuda": "Antigua and Barbuda",
            "belize": "Belize",
            "dominica": "Dominica",
            "grenada": "Grenada",
            "guyana": "Guyana",
            "st kitts": "St Kitts and Nevis",
            "saint kitts": "St Kitts and Nevis",
            "nevis": "St Kitts and Nevis",
            "st lucia": "St Lucia",
            "saint lucia": "St Lucia",
            "st vincent": "St Vincent and the Grenadines",
            "saint vincent": "St Vincent and the Grenadines",
            "grenadines": "St Vincent and the Grenadines",
            
            # African countries
            "south africa": "South Africa",
            "kenya": "Kenya",
            "uganda": "Uganda",
            "tanzania": "Tanzania",
            "zambia": "Zambia",
            "zimbabwe": "Zimbabwe",
            "malawi": "Malawi",
            "botswana": "Botswana",
            "gambia": "Gambia",
            "ghana": "Ghana",
            "nigeria": "Nigeria",
            "cameroon": "Cameroon",
            "swaziland": "Swaziland",
            "mauritius": "Mauritius",
            
            # Asian/Pacific
            "singapore": "Singapore",
            "fiji": "Fiji",
            
            # European
            "netherlands": "The Netherlands",
            "holland": "The Netherlands",
            
            # Caribbean regional terms
            "west indies": "Caribbean / West Indies (English-speaking Caribbean Commonwealth territories)",
            "caribbean": "Caribbean / West Indies (English-speaking Caribbean Commonwealth territories)",
            
            # British territories
            "british overseas territories": "The British overseas territories",
            "overseas territories": "The British overseas territories",
        }
        
        if country_lower in country_mappings:
            mapped_country = country_mappings[country_lower]
            for country in rules.degree_obtained_exempt_countries:
                if mapped_country.lower() in country.lower():
                    conditions = None
                    if hasattr(rules, 'levels') and rules.levels:
                        degree_conditions = rules.levels.get('degree_exempt_conditions', {})
                        conditions = degree_conditions.get(country)
                    
                    return {
                        "is_exempt": True,
                        "matched_country": country,
                        "conditions": conditions,
                        "reason": f"Degree country '{degree_country}' maps to exempt country '{country}'" +
                                 (f" with conditions: {conditions}" if conditions else "")
                    }
        
        return {
            "is_exempt": False,
            "matched_country": None,
            "conditions": None,
            "reason": f"Degree country '{degree_country}' not found in exempt countries list"
        }

    @kernel_function(description="Get the list of nationality exempt countries for reference.")
    def get_nationality_exempt_countries(self) -> Annotated[list[str], "List of countries that grant nationality-based English exemption"]:
        """Return the list of nationality exempt countries."""
        rules = self._get_english_rules()
        if not rules or not rules.nationality_exempt_countries:
            return []
        return rules.nationality_exempt_countries
    
    @kernel_function(description="Get the list of degree exempt countries for reference.")
    def get_degree_exempt_countries(self) -> Annotated[list[str], "List of countries that grant degree-based English exemption"]:
        """Return the list of degree exempt countries."""
        rules = self._get_english_rules()
        if not rules or not rules.degree_obtained_exempt_countries:
            return []
        return rules.degree_obtained_exempt_countries

    @kernel_function(description="Get comprehensive exemption check for both nationality and degree.")
    def check_comprehensive_exemption(
        self,
        nationality: Annotated[str, "The applicant's nationality"] = "",
        degree_country: Annotated[str, "Country where degree was obtained"] = "",
        institution_name: Annotated[str, "Institution name for context"] = "",
    ) -> Annotated[dict, "Returns comprehensive exemption status with all details"]:
        """Perform both nationality and degree exemption checks."""
        nationality_result = {"is_exempt": False, "reason": "No nationality provided"}
        degree_result = {"is_exempt": False, "reason": "No degree country provided"}
        
        if nationality.strip():
            nationality_result = self.check_nationality_exemption(nationality)
        
        if degree_country.strip():
            degree_result = self.check_degree_exemption(degree_country, institution_name)
        
        is_exempt = nationality_result["is_exempt"] or degree_result["is_exempt"]
        
        exemption_reasons = []
        if nationality_result["is_exempt"]:
            exemption_reasons.append(f"Nationality: {nationality_result['reason']}")
        if degree_result["is_exempt"]:
            exemption_reasons.append(f"Degree: {degree_result['reason']}")
        
        return {
            "is_exempt": is_exempt,
            "nationality_exempt": nationality_result["is_exempt"],
            "degree_exempt": degree_result["is_exempt"],
            "matched_nationality_country": nationality_result.get("matched_country"),
            "matched_degree_country": degree_result.get("matched_country"),
            "degree_conditions": degree_result.get("conditions"),
            "exemption_reasons": exemption_reasons,
            "overall_reason": "; ".join(exemption_reasons) if exemption_reasons else "No exemptions found"
        }