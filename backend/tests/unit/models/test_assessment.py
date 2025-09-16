import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from app.models.assessment import AssessmentRun, Applicant, ApplicantDocument
from app.models.user import User


@pytest.mark.requires_db
class TestAssessmentRunModel:
    """Test cases for AssessmentRun model functionality."""

    def test_assessment_run_creation(self, test_db_session):
        """Test basic assessment run creation."""
        assessment_run = AssessmentRun(
            name="Test Assessment",
            status="created"
        )
        test_db_session.add(assessment_run)
        test_db_session.commit()

        assert assessment_run.id is not None
        assert assessment_run.name == "Test Assessment"
        assert assessment_run.status == "created"
        assert isinstance(assessment_run.created_at, datetime)
        assert isinstance(assessment_run.updated_at, datetime)

    def test_assessment_run_with_owner(self, test_db_session):
        """Test assessment run creation with owner user."""
        # Create a user first
        user = User(
            email="owner@example.com",
            hashed_password="owner_password"
        )
        test_db_session.add(user)
        test_db_session.commit()

        assessment_run = AssessmentRun(
            name="Owned Assessment",
            owner_user_id=user.id,
            status="running"
        )
        test_db_session.add(assessment_run)
        test_db_session.commit()

        assert assessment_run.owner_user_id == user.id

    def test_assessment_run_with_agent_models(self, test_db_session):
        """Test assessment run with agent models configuration."""
        agent_models = {
            "english": "gpt-4o",
            "degree": "o3-mini",
            "academic": "gpt-4"
        }

        assessment_run = AssessmentRun(
            name="Custom Models Assessment",
            agent_models=agent_models
        )
        test_db_session.add(assessment_run)
        test_db_session.commit()

        assert assessment_run.agent_models == agent_models

    def test_assessment_run_with_custom_requirements(self, test_db_session):
        """Test assessment run with custom requirements."""
        requirements = [
            "Minimum 3 years work experience",
            "Bachelor's degree in Computer Science",
            "IELTS 7.0 or equivalent"
        ]

        assessment_run = AssessmentRun(
            name="Custom Requirements Assessment",
            custom_requirements=requirements
        )
        test_db_session.add(assessment_run)
        test_db_session.commit()

        assert assessment_run.custom_requirements == requirements

    def test_assessment_run_default_status(self, test_db_session):
        """Test that default status is 'created'."""
        assessment_run = AssessmentRun(name="Default Status Test")
        test_db_session.add(assessment_run)
        test_db_session.commit()

        assert assessment_run.status == "created"


@pytest.mark.requires_db
class TestApplicantModel:
    """Test cases for Applicant model functionality."""

    def test_applicant_creation(self, test_db_session):
        """Test basic applicant creation."""
        # Create assessment run first
        assessment_run = AssessmentRun(name="Test Assessment")
        test_db_session.add(assessment_run)
        test_db_session.commit()

        applicant = Applicant(
            run_id=assessment_run.id,
            display_name="John Doe",
            email="john.doe@example.com",
            folder_name="john_doe_folder"
        )
        test_db_session.add(applicant)
        test_db_session.commit()

        assert applicant.id is not None
        assert applicant.run_id == assessment_run.id
        assert applicant.display_name == "John Doe"
        assert applicant.email == "john.doe@example.com"
        assert applicant.folder_name == "john_doe_folder"
        assert isinstance(applicant.created_at, datetime)

    def test_applicant_relationship_with_run(self, test_db_session):
        """Test applicant relationship with assessment run."""
        assessment_run = AssessmentRun(name="Relationship Test")
        test_db_session.add(assessment_run)
        test_db_session.commit()

        applicant = Applicant(
            run_id=assessment_run.id,
            folder_name="test_folder"
        )
        test_db_session.add(applicant)
        test_db_session.commit()

        # Test relationship
        assert applicant.run == assessment_run
        assert applicant in assessment_run.applicants

    def test_applicant_cascade_delete(self, test_db_session):
        """Test that applicants are deleted when assessment run is deleted."""
        assessment_run = AssessmentRun(name="Cascade Test")
        test_db_session.add(assessment_run)
        test_db_session.commit()

        applicant = Applicant(
            run_id=assessment_run.id,
            folder_name="cascade_folder"
        )
        test_db_session.add(applicant)
        test_db_session.commit()

        applicant_id = applicant.id

        # Delete assessment run
        test_db_session.delete(assessment_run)
        test_db_session.commit()

        # Applicant should be deleted too
        deleted_applicant = test_db_session.query(Applicant).filter(Applicant.id == applicant_id).first()
        assert deleted_applicant is None


@pytest.mark.requires_db
class TestApplicantDocumentModel:
    """Test cases for ApplicantDocument model functionality."""

    def test_applicant_document_creation(self, test_db_session):
        """Test basic applicant document creation."""
        # Create assessment run and applicant
        assessment_run = AssessmentRun(name="Document Test")
        test_db_session.add(assessment_run)
        test_db_session.commit()

        applicant = Applicant(
            run_id=assessment_run.id,
            folder_name="document_test_folder"
        )
        test_db_session.add(applicant)
        test_db_session.commit()

        document = ApplicantDocument(
            applicant_id=applicant.id,
            rel_path="documents/cv.pdf",
            original_filename="john_doe_cv.pdf",
            content_type="application/pdf",
            size_bytes=1024000,
            text_preview="John Doe - Software Engineer...",
            doc_type="cv"
        )
        test_db_session.add(document)
        test_db_session.commit()

        assert document.id is not None
        assert document.applicant_id == applicant.id
        assert document.rel_path == "documents/cv.pdf"
        assert document.original_filename == "john_doe_cv.pdf"
        assert document.content_type == "application/pdf"
        assert document.size_bytes == 1024000
        assert document.text_preview == "John Doe - Software Engineer..."
        assert document.doc_type == "cv"

    def test_applicant_document_with_table_data(self, test_db_session):
        """Test applicant document with table data."""
        assessment_run = AssessmentRun(name="Table Test")
        test_db_session.add(assessment_run)
        test_db_session.commit()

        applicant = Applicant(
            run_id=assessment_run.id,
            folder_name="table_test_folder"
        )
        test_db_session.add(applicant)
        test_db_session.commit()

        table_data = [
            {"subject": "Mathematics", "grade": "A", "credits": 6},
            {"subject": "Physics", "grade": "B+", "credits": 6},
            {"subject": "Computer Science", "grade": "A", "credits": 8}
        ]

        document = ApplicantDocument(
            applicant_id=applicant.id,
            rel_path="transcripts/transcript.xlsx",
            original_filename="academic_transcript.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            table_data=table_data,
            doc_type="transcript"
        )
        test_db_session.add(document)
        test_db_session.commit()

        assert document.table_data == table_data

    def test_applicant_document_relationship(self, test_db_session):
        """Test document relationship with applicant."""
        assessment_run = AssessmentRun(name="Relationship Test")
        test_db_session.add(assessment_run)
        test_db_session.commit()

        applicant = Applicant(
            run_id=assessment_run.id,
            folder_name="relationship_folder"
        )
        test_db_session.add(applicant)
        test_db_session.commit()

        document = ApplicantDocument(
            applicant_id=applicant.id,
            rel_path="test/document.pdf",
            original_filename="test.pdf"
        )
        test_db_session.add(document)
        test_db_session.commit()

        # Test relationship
        assert document.applicant == applicant
        assert document in applicant.documents

    def test_applicant_document_cascade_delete(self, test_db_session):
        """Test that documents are deleted when applicant is deleted."""
        assessment_run = AssessmentRun(name="Document Cascade Test")
        test_db_session.add(assessment_run)
        test_db_session.commit()

        applicant = Applicant(
            run_id=assessment_run.id,
            folder_name="doc_cascade_folder"
        )
        test_db_session.add(applicant)
        test_db_session.commit()

        document = ApplicantDocument(
            applicant_id=applicant.id,
            rel_path="cascade/test.pdf",
            original_filename="cascade_test.pdf"
        )
        test_db_session.add(document)
        test_db_session.commit()

        document_id = document.id

        # Delete applicant
        test_db_session.delete(applicant)
        test_db_session.commit()

        # Document should be deleted too
        deleted_document = test_db_session.query(ApplicantDocument).filter(ApplicantDocument.id == document_id).first()
        assert deleted_document is None

    def test_applicant_document_large_file(self, test_db_session):
        """Test document with large file size."""
        assessment_run = AssessmentRun(name="Large File Test")
        test_db_session.add(assessment_run)
        test_db_session.commit()

        applicant = Applicant(
            run_id=assessment_run.id,
            folder_name="large_file_folder"
        )
        test_db_session.add(applicant)
        test_db_session.commit()

        # Test with large file size (using BigInteger)
        large_size = 5 * 1024 * 1024 * 1024  # 5GB

        document = ApplicantDocument(
            applicant_id=applicant.id,
            rel_path="large/video.mp4",
            original_filename="presentation_video.mp4",
            content_type="video/mp4",
            size_bytes=large_size
        )
        test_db_session.add(document)
        test_db_session.commit()

        assert document.size_bytes == large_size