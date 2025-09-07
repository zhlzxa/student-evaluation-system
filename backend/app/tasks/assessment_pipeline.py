from __future__ import annotations

import asyncio
import logging
from app.celery_app import celery

# Setup logging for pipeline
logger = logging.getLogger(__name__)
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.assessment import AssessmentRun, Applicant
from app.services.document_intelligence import analyze_layout_file
from app.services.storage import ensure_storage_dir
from pathlib import Path
from sqlalchemy import select
from app.models.assessment import ApplicantDocument
from app.agents.classifier import classify_document, classify_documents_batch
from app.agents.evaluators import (
    english_agent,
    degree_agent,
    experience_agent,
    ps_rl_agent,
    academic_agent,
    compare_agent,
)
from app.agents.detectors import detect_degree_country
from app.config import get_settings as _get_settings
from app.models.evaluation import ApplicantEvaluation, ApplicantGating, ApplicantRanking, PairwiseComparison
from app.services.scoring import weighted_total, is_close
from sqlalchemy.orm import joinedload


@celery.task(name="pipeline.orchestrate_run")
def orchestrate_run(run_id: int) -> str:
    # Analyze documents via Azure Document Intelligence (layout), then mark completed
    db: Session = SessionLocal()
    try:
        run = db.get(AssessmentRun, run_id)
        if not run:
            return "not-found"
        run.status = "processing"
        db.add(run)
        db.commit()

        base = Path(ensure_storage_dir()) / "runs" / f"run_{run_id}"

        # FIXED: Only process documents from the current run
        docs = db.execute(
            select(ApplicantDocument)
            .join(Applicant)
            .filter(Applicant.run_id == run_id)
        ).scalars().all()
        
        # Resolve per-run model overrides (if any)
        run_agent_models: dict[str, str] = run.agent_models or {}

        # First pass: Extract text from documents that need it
        for doc in docs:
            try:
                file_path = base / doc.rel_path
                if not file_path.exists():
                    continue
                # Extract layout if not present
                if not doc.text_preview:
                    result = analyze_layout_file(file_path)
                    if result.get("status") == "ok":
                        paras = result.get("paragraphs") or []
                        preview = "\n".join(paras)
                        doc.text_preview = preview[:8000]
                        db.add(doc)
                        db.commit()
            except Exception as e:
                # Log the error but continue processing other files
                logger.error(f"Failed to process document {doc.original_filename} (ID: {doc.id}): {str(e)}")
                logger.error(f"Document path: {base / doc.rel_path}")
                continue

        # Second pass: Batch classify documents by applicant
        applicants_with_docs = {}
        for doc in docs:
            if doc.text_preview and not doc.doc_type:
                applicant_id = doc.applicant_id
                if applicant_id not in applicants_with_docs:
                    applicants_with_docs[applicant_id] = []
                applicants_with_docs[applicant_id].append(doc)
        
        # Batch classify documents for each applicant
        for applicant_id, unclassified_docs in applicants_with_docs.items():
            if not unclassified_docs:
                continue
                
            try:
                # Prepare batch data
                batch_docs = []
                for doc in unclassified_docs:
                    batch_docs.append({
                        'doc_id': str(doc.id),
                        'filename': doc.original_filename,
                        'text': doc.text_preview
                    })
                
                logger.info(f"Batch classifying {len(batch_docs)} documents for applicant {applicant_id}")
                
                # Call batch classification
                classifications = classify_documents_batch(batch_docs, model_override=run_agent_models.get("batch_classifier"))
                
                # Apply results
                for doc in unclassified_docs:
                    doc_id_str = str(doc.id)
                    if doc_id_str in classifications:
                        doc.doc_type = classifications[doc_id_str]
                        db.add(doc)
                        logger.info(f"Classified {doc.original_filename} as {doc.doc_type}")
                
                db.commit()
                
            except Exception as e:
                logger.error(f"Failed to batch classify documents for applicant {applicant_id}: {str(e)}")
                # Fallback to individual classification
                for doc in unclassified_docs:
                    try:
                        if doc.text_preview and not doc.doc_type:
                            label = classify_document(doc.text_preview, model_override=run_agent_models.get("classifier"))
                            if label:
                                doc.doc_type = label
                                db.add(doc)
                                db.commit()
                    except Exception as fallback_e:
                        logger.error(f"Failed to classify document {doc.original_filename}: {str(fallback_e)}")
                        continue

        # Build applicant-level text blobs
        applicants = (
            db.execute(
                select(Applicant)
                .where(Applicant.run_id == run_id)
                .options(joinedload(Applicant.documents))
            )
            .unique()
            .scalars()
            .all()
        )

        # Get checklists, target degree class, and English policy from rule set metadata if any
        checklists = {}
        english_policy = None
        target_degree_class = "UPPER_SECOND"
        english_level_hint = None
        
        try:
            # First priority: Use existing rule_set_id if available
            if run.rule_set_id:
                from app.models import AdmissionRuleSet

                rs = db.get(AdmissionRuleSet, run.rule_set_id)
                if rs and rs.metadata_json and isinstance(rs.metadata_json, dict):
                    checklists = rs.metadata_json.get("checklists", {}) or {}
                    tdc = rs.metadata_json.get("degree_requirement_class") if isinstance(rs.metadata_json, dict) else None
                    if isinstance(tdc, str) and tdc:
                        target_degree_class = tdc.upper()
                    english_level_hint = rs.metadata_json.get("english_level") if isinstance(rs.metadata_json, dict) else None
                if rs and rs.english_rule_id:
                    from app.models import EnglishRule
                    er = db.get(EnglishRule, rs.english_rule_id)
                    if er:
                        english_policy = {
                            "nationality_exempt_countries": er.nationality_exempt_countries,
                            "degree_obtained_exempt_countries": er.degree_obtained_exempt_countries,
                            "levels": er.levels,
                        }
            
            # Second priority: Extract rules from source_url if no rule_set_id
            elif run.rule_set_url:
                logger.info(f"No rule_set_id found, extracting rules from rule_set_url: {run.rule_set_url}")
                
                # Import URL rules extractor
                from app.agents.url_rules_extractor import extract_rules_from_url
                from app.services.logging_service import log_agent_event
                
                try:
                    log_agent_event(run_id, "url_rules_extractor", "start", f"Starting URL extraction from {run.rule_set_url}")
                    
                    # Extract rules from URL with custom requirements
                    url_rules = asyncio.run(extract_rules_from_url(
                        url=run.rule_set_url,
                        custom_requirements=run.custom_requirements,
                        model_override=run_agent_models.get("url_rules_extractor")
                    ))
                    
                    logger.info(f"URL extraction completed. Results: {url_rules}")
                    log_agent_event(run_id, "url_rules_extractor", "completed", 
                                  f"URL extraction completed. Extracted {len(url_rules.get('checklists', {}))} agent checklists")
                    
                    if url_rules and url_rules.get('checklists'):
                        checklists = url_rules['checklists']
                        
                        # Log the extracted checklists for debugging
                        for agent, agent_checklist in checklists.items():
                            logger.info(f"Extracted checklist for {agent}: {len(agent_checklist)} items")
                            log_agent_event(run_id, "url_rules_extractor", "checklist", 
                                          f"Extracted {len(agent_checklist)} items for {agent}: {agent_checklist}")
                        
                        # Extract target degree class
                        if url_rules.get('degree_requirement_class'):
                            target_degree_class = url_rules['degree_requirement_class'].upper()
                            logger.info(f"Extracted degree requirement class: {target_degree_class}")
                        
                        # Extract english level hint
                        english_level_hint = url_rules.get('english_level')
                        if english_level_hint:
                            logger.info(f"Extracted english level hint: {english_level_hint}")
                        
                        # Create a temporary rule set for this run to avoid re-extraction
                        from app.models import AdmissionRuleSet
                        programme_title = url_rules.get('programme_title', f"Auto-extracted from {run.rule_set_url}")
                        
                        temp_rule_set = AdmissionRuleSet(
                            name=programme_title,
                            description=f"Auto-generated from {run.rule_set_url}",
                            metadata_json={
                                'checklists': checklists,
                                'english_level': english_level_hint,
                                'degree_requirement_class': target_degree_class,
                                'rule_set_url': run.rule_set_url,
                                'text_length': url_rules.get('text_length', 0),
                                'auto_generated': True
                            }
                        )
                        
                        # Save the temporary rule set and link it to the run
                        db.add(temp_rule_set)
                        db.flush()  # Get the ID without committing
                        
                        run.rule_set_id = temp_rule_set.id
                        db.add(run)
                        db.commit()
                        
                        logger.info(f"Created temporary rule set {temp_rule_set.id} for run {run.id}")
                        log_agent_event(run_id, "url_rules_extractor", "success", 
                                      f"Created temporary rule set {temp_rule_set.id} with {len(checklists)} agent checklists")
                    else:
                        logger.warning(f"Failed to extract rules from {run.rule_set_url}, url_rules: {url_rules}")
                        log_agent_event(run_id, "url_rules_extractor", "warning", 
                                      f"Failed to extract useful rules from {run.rule_set_url}")
                        
                except Exception as url_error:
                    logger.error(f"Error during URL rules extraction: {str(url_error)}")
                    log_agent_event(run_id, "url_rules_extractor", "error", f"URL extraction failed: {str(url_error)}")
                    # Continue with empty checklists as fallback
                    
        except Exception as e:
            logger.error(f"Error processing rules for run {run.id}: {str(e)}")
            checklists = {}
            english_policy = None

        if english_policy is None:
            # Fallback to latest EnglishRule
            try:
                from sqlalchemy import select as _select
                from app.models import EnglishRule as _ER
                er = db.execute(_select(_ER).order_by(_ER.last_verified_at.desc().nullslast(), _ER.id.desc())).scalars().first()
                if er:
                    english_policy = {
                        "nationality_exempt_countries": er.nationality_exempt_countries,
                        "degree_obtained_exempt_countries": er.degree_obtained_exempt_countries,
                        "levels": er.levels,
                    }
            except Exception:
                english_policy = None

        # Evaluate each applicant using intelligent document access
        for a in applicants:
            # Create a small text sample for country detection only
            text_sample = "\n".join([d.text_preview or "" for d in a.documents[:3] if d.text_preview])[:2000]
            
            # Detect degree country to select special context when applicable
            detected = detect_degree_country(text_sample)
            iso3 = (detected.get("country_code_iso3") or "").upper() if isinstance(detected, dict) else ""
            special_context = None
            if iso3 in {"CHN", "IND"}:
                settings_local = _get_settings()
                try:
                    base_dir = Path(".")
                    if iso3 == "CHN":
                        p = settings_local.CHINA_RULES_TXT_PATH or "China.txt"
                    else:
                        p = settings_local.INDIA_RULES_TXT_PATH or "India.txt"
                    sp = Path(p)
                    if not sp.is_absolute():
                        sp = (Path.cwd() / sp).resolve()
                    if sp.exists():
                        special_context = sp.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    special_context = None
            
            # FIXED: Agents are async, but this is now a sync function
            # Use already imported asyncio at module scope
            
            async def run_agents():
                # Check existing evaluations to avoid re-running agents
                existing_evals = db.query(ApplicantEvaluation).filter_by(applicant_id=a.id).all()
                existing_agents = {eval.agent_name for eval in existing_evals}
                
                # Check if we need to run any agents
                needed_agents = []
                for agent_name in ["english", "degree", "experience", "ps_rl", "academic"]:
                    if agent_name not in existing_agents:
                        needed_agents.append(agent_name)
                
                if needed_agents:
                    logger.info(f"Starting {len(needed_agents)} evaluation agents concurrently for applicant {a.id}: {needed_agents}")
                    
                    # Use Semantic Kernel concurrent orchestration with existing Azure AI agents
                    from app.agents.concurrent_evaluators import run_concurrent_evaluation
                    
                    try:
                        # Log the checklists being passed to agents for debugging
                        logger.info(f"Passing checklists to concurrent evaluators for applicant {a.id}:")
                        logger.info(f"  - degree_agent: {len(checklists.get('degree_agent', []))} items: {checklists.get('degree_agent', [])}")
                        logger.info(f"  - experience_agent: {len(checklists.get('experience_agent', []))} items: {checklists.get('experience_agent', [])}")
                        logger.info(f"  - ps_rl_agent: {len(checklists.get('ps_rl_agent', []))} items: {checklists.get('ps_rl_agent', [])}")
                        logger.info(f"  - academic_agent: {len(checklists.get('academic_agent', []))} items: {checklists.get('academic_agent', [])}")
                        
                        from app.services.logging_service import log_agent_event
                        log_agent_event(run_id, "concurrent_evaluators", "checklist_summary", 
                                      f"Starting evaluation for applicant {a.id} with checklists: "
                                      f"degree={len(checklists.get('degree_agent', []))}, "
                                      f"experience={len(checklists.get('experience_agent', []))}, "
                                      f"ps_rl={len(checklists.get('ps_rl_agent', []))}, "
                                      f"academic={len(checklists.get('academic_agent', []))}", applicant_id=a.id)
                        
                        results = await run_concurrent_evaluation(
                            applicant_id=a.id,
                            run_id=run_id,
                            english_level_hint=english_level_hint,
                            english_policy=english_policy,
                            target_degree_class=target_degree_class,
                            degree_checklists=checklists.get("degree_agent"),
                            experience_checklists=checklists.get("experience_agent"),
                            ps_rl_checklists=checklists.get("ps_rl_agent"),
                            academic_checklists=checklists.get("academic_agent"),
                            special_context=special_context,
                            detected_country_iso3=iso3 or None,
                            agent_models=run_agent_models,
                        )
                        
                        # Process and save results
                        for agent_name, result in results.items():
                            if agent_name in needed_agents:  # Only save agents that were needed
                                if "error" in result:
                                    logger.error(f"Agent {agent_name} failed with error: {result.get('error')}")
                                    db.add(ApplicantEvaluation(
                                        applicant_id=a.id, 
                                        agent_name=agent_name, 
                                        score=None, 
                                        details=result
                                    ))
                                else:
                                    # Save successful evaluation
                                    db.add(ApplicantEvaluation(
                                        applicant_id=a.id, 
                                        agent_name=agent_name, 
                                        score=result.get("score"), 
                                        details=result
                                    ))
                        
                        logger.info(f"Completed {len(needed_agents)} evaluation agents concurrently for applicant {a.id}")
                        
                    except Exception as e:
                        logger.error(f"Concurrent orchestration failed for applicant {a.id}: {e}")
                        # Fallback to individual agent failures
                        for agent_name in needed_agents:
                            db.add(ApplicantEvaluation(
                                applicant_id=a.id, 
                                agent_name=agent_name, 
                                score=None, 
                                details={"error": f"Orchestration failed: {str(e)}"}
                            ))
                
                db.commit()
            
            # Run the async agents within the sync pipeline
            asyncio.run(run_agents())

        # Gating
        for a in applicants:
            evals = db.query(ApplicantEvaluation).filter_by(applicant_id=a.id).all()
            d = {e.agent_name: e for e in evals}
            decision = "MIDDLE"
            reasons: list[str] = []
            # Hard rejects
            if d.get("background") and d["background"].details and d["background"].details.get("fit") is False:
                decision = "REJECT"; reasons.append("Background not satisfied")
            if d.get("degree") and d["degree"].details and d["degree"].details.get("meets_requirement") is False:
                decision = "REJECT"; reasons.append("Degree below requirement")
            if d.get("degree") and d["degree"].details and isinstance(d["degree"].details.get("qs_rank"), int) and d["degree"].details.get("qs_rank") > 800:
                decision = "REJECT"; reasons.append("QS rank below threshold")
            if d.get("english") and d["english"].details and not d["english"].details.get("exemption") and d["english"].details.get("test_overall") is None:
                decision = "REJECT"; reasons.append("No English test and no exemption")
            # Clear accepts
            if decision != "REJECT":
                good_qs = d.get("degree") and d["degree"].details and isinstance(d["degree"].details.get("qs_rank"), int) and d["degree"].details.get("qs_rank") <= 100
                strong_degree = d.get("degree") and d["degree"].score and d["degree"].score >= 8
                if good_qs and strong_degree:
                    decision = "ACCEPT"; reasons.append("High QS and strong degree")

            existing = db.query(ApplicantGating).filter_by(applicant_id=a.id).one_or_none()
            if existing:
                existing.decision = decision
                existing.reasons = reasons
                db.add(existing)
            else:
                db.add(ApplicantGating(applicant_id=a.id, decision=decision, reasons=reasons))
            db.commit()

        # Ranking for MIDDLE
        mids = [a for a in applicants if (db.query(ApplicantGating).filter_by(applicant_id=a.id).one().decision == "MIDDLE")]
        scores: list[tuple[int, float]] = []
        for a in mids:
            evals = db.query(ApplicantEvaluation).filter_by(applicant_id=a.id).all()
            d = {e.agent_name: e for e in evals}
            total = weighted_total(
                english=d.get("english").score if d.get("english") else None,
                degree=d.get("degree").score if d.get("degree") else None,
                academic=d.get("academic").score if d.get("academic") else None,
                experience=d.get("experience").score if d.get("experience") else None,
                ps_rl=d.get("ps_rl").score if d.get("ps_rl") else None,
            )
            scores.append((a.id, total))
        scores.sort(key=lambda x: x[1], reverse=True)
        for rank, (aid, sc) in enumerate(scores, start=1):
            existing = db.query(ApplicantRanking).filter_by(applicant_id=aid).one_or_none()
            if existing:
                existing.weighted_score = sc
                existing.final_rank = rank
                db.add(existing)
            else:
                db.add(ApplicantRanking(applicant_id=aid, weighted_score=sc, final_rank=rank))
        db.commit()

        # Bradley–Terry adjustments: K passes of adjacent close comparisons
        from app.config import get_settings
        settings = get_settings()
        K = max(0, int(settings.PAIRWISE_K))
        # Clean previous pairwise comparisons for this run (idempotency on reruns)
        db.query(PairwiseComparison).filter(PairwiseComparison.run_id == run_id).delete()
        db.commit()
        for pass_idx in range(K):
            # refresh ranks sorted by current ranking.final_rank
            scores.sort(key=lambda x: x[1], reverse=True)
            for i in range(len(scores) - 1):
                aid1, sc1 = scores[i]
                aid2, sc2 = scores[i + 1]
                if not is_close(sc1, sc2, eps=float(settings.PAIRWISE_EPS)):
                    continue
                # Build compact evaluation dicts
                evs1 = db.query(ApplicantEvaluation).filter_by(applicant_id=aid1).all()
                evs2 = db.query(ApplicantEvaluation).filter_by(applicant_id=aid2).all()
                d1 = {e.agent_name: {"score": e.score, "details": e.details} for e in evs1}
                d2 = {e.agent_name: {"score": e.score, "details": e.details} for e in evs2}
                # Allow per-run override for compare agent
                import asyncio as _asyncio
                verdict = _asyncio.run(compare_agent(d1, d2, model_override=run_agent_models.get("compare")))
                winner = verdict.get("winner")
                reason = verdict.get("reason") or ""
                # persist comparison
                db.add(PairwiseComparison(run_id=run_id, applicant_a_id=aid1, applicant_b_id=aid2, winner=winner or "tie", reason=reason, pass_index=pass_idx))
                db.commit()
                r1 = db.query(ApplicantRanking).filter_by(applicant_id=aid1).one_or_none()
                r2 = db.query(ApplicantRanking).filter_by(applicant_id=aid2).one_or_none()
                if winner == "A" and sc1 < sc2:
                    # swap order to favor A
                    sc1, sc2 = sc2, sc1
                    scores[i] = (aid1, sc1)
                    scores[i + 1] = (aid2, sc2)
                elif winner == "B" and sc2 < sc1:
                    sc1, sc2 = sc2, sc1
                    scores[i] = (aid1, sc1)
                    scores[i + 1] = (aid2, sc2)
                # annotate notes
                if r1:
                    r1.notes = ((r1.notes or "") + f"BT vs {aid2}: {winner} ({reason}). ").strip()
                    db.add(r1)
                if r2:
                    r2.notes = ((r2.notes or "") + f"BT vs {aid1}: {winner} ({reason}). ").strip()
                    db.add(r2)
                db.commit()
            # assign ranks based on updated scores
            scores.sort(key=lambda x: x[1], reverse=True)
            for rank, (aid, sc) in enumerate(scores, start=1):
                r = db.query(ApplicantRanking).filter_by(applicant_id=aid).one_or_none()
                if r:
                    r.final_rank = rank
                    db.add(r)
            db.commit()

        run.status = "completed"
        db.add(run)
        db.commit()
        return "ok"
    finally:
        db.close()
