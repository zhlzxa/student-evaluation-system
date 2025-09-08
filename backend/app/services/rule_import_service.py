"""Service for importing rules from URLs - unified logic for both assessment and rule management"""

from __future__ import annotations

import logging
from typing import Any, Optional
from datetime import datetime

from sqlalchemy.orm import Session
from app.models import AdmissionRuleSet, EnglishRule
from app.agents.url_rules_extractor import extract_rules_from_url
from app.services.url_extractor import extract_programme_title_from_text
from sqlalchemy import select

logger = logging.getLogger(__name__)


class RuleImportService:
    """Service for importing rules from URLs"""
    
    @staticmethod
    async def preview_url_rules(
        url: str,
        custom_requirements: list[str] | None = None,
        model_override: Optional[str] = None,
    ) -> dict[str, Any]:
        """Preview rules extraction from URL without creating a rule set"""
        logger.info(f"Previewing rules extraction from URL: {url}")
        
        try:
            # Extract rules using the URL rules extractor
            url_rules = await extract_rules_from_url(
                url=url,
                custom_requirements=custom_requirements,
                model_override=model_override,
            )
            
            if not url_rules:
                raise Exception("Failed to extract rules from URL")
            
            # Add extraction method info
            url_rules['extraction_method'] = 'azure_ai' if url_rules.get('_used_azure', True) else 'heuristic'
            
            # Create text preview
            text_preview = (url_rules.get('_source_text', '') or '')[:500]
            url_rules['text_preview'] = text_preview
            
            logger.info(f"Successfully previewed rules from {url}")
            return url_rules
            
        except Exception as e:
            logger.error(f"Failed to preview rules from URL {url}: {str(e)}")
            raise e
    
    @staticmethod
    async def import_rules_from_url(
        db: Session,
        url: str,
        custom_requirements: list[str] | None = None,
        name: str | None = None,
        temporary: bool = False,
        model_override: Optional[str] = None,
    ) -> tuple[AdmissionRuleSet, dict[str, Any]]:
        """Import rules from URL and create a rule set"""
        logger.info(f"Importing rules from URL: {url} (temporary={temporary})")
        
        try:
            # Extract rules using the URL rules extractor
            url_rules = await extract_rules_from_url(
                url=url,
                custom_requirements=custom_requirements,
                model_override=model_override,
            )
            
            if not url_rules:
                raise Exception("Failed to extract rules from URL")
            
            # Determine name
            if not name or name.strip().lower() in ["auto-generated", ""]:
                programme_title = url_rules.get('programme_title')
                if programme_title:
                    name = programme_title
                else:
                    name = f"Rules from {url}" if not temporary else f"Temp rules from {url}"
            
            # Add temporary marker to name if needed
            if temporary:
                name = f"[TEMP] {name}"
            
            # Get the latest English rule for linking
            english_rule = db.execute(
                select(EnglishRule).order_by(
                    EnglishRule.last_verified_at.desc().nullslast(), 
                    EnglishRule.id.desc()
                )
            ).scalars().first()
            
            # Build metadata
            metadata = {
                'checklists': url_rules.get('checklists', {}),
                'english_level': url_rules.get('english_level'),
                'degree_requirement_class': url_rules.get('degree_requirement_class'),
                'rule_set_url': url,
                'text_length': url_rules.get('text_length', 0),
                'auto_generated': True,
                'temporary': temporary,
                'extraction_method': 'azure_ai' if url_rules.get('_used_azure', True) else 'heuristic',
                'created_at': datetime.utcnow().isoformat(),
            }
            
            # Create rule set
            rule_set = AdmissionRuleSet(
                name=name,
                description=f"Auto-generated from {url}" + (" (temporary)" if temporary else ""),
                metadata_json=metadata,
                english_rule_id=english_rule.id if english_rule else None,
            )
            
            db.add(rule_set)
            db.flush()  # Get ID without full commit
            
            # Add rule_set_id to the response data
            url_rules['rule_set_id'] = rule_set.id
            url_rules['rule_set_name'] = name
            url_rules['temporary'] = temporary
            url_rules['extraction_method'] = metadata['extraction_method']
            
            logger.info(f"Created rule set {rule_set.id} from URL {url}")
            
            return rule_set, url_rules
            
        except Exception as e:
            logger.error(f"Failed to import rules from URL {url}: {str(e)}")
            db.rollback()
            raise e
    
    @staticmethod
    def cleanup_temporary_rule_sets(db: Session, max_age_hours: int = 24) -> int:
        """Clean up old temporary rule sets"""
        from datetime import datetime, timedelta
        
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        cutoff_iso = cutoff_time.isoformat()
        
        # Find temporary rule sets older than cutoff
        stmt = select(AdmissionRuleSet).where(
            AdmissionRuleSet.metadata_json.op("@>")('{"temporary": true}')
        )
        
        temp_rule_sets = db.execute(stmt).scalars().all()
        deleted = 0
        
        for rs in temp_rule_sets:
            created_at_str = rs.metadata_json.get('created_at') if rs.metadata_json else None
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(created_at_str)
                    if created_at < cutoff_time:
                        db.delete(rs)
                        deleted += 1
                except ValueError:
                    # If created_at parsing fails, delete it as it's old format
                    db.delete(rs)
                    deleted += 1
        
        if deleted > 0:
            db.commit()
            logger.info(f"Cleaned up {deleted} temporary rule sets")
        
        return deleted