"""Acceptance-criterion coverage checks across generated artifacts."""

from sdlc.models import ImplementationOutput, ReviewOutput, TestMapping


def validate_acceptance_criterion_coverage(
    required_ids: set[str],
    implementation: ImplementationOutput,
    tests: list[TestMapping],
    review: ReviewOutput,
    qa_handoff_markdown: str,
) -> dict[str, list[str]]:
    implemented = {
        criterion_id
        for generated_file in implementation.files
        for criterion_id in generated_file.acceptance_criterion_ids
        if criterion_id in generated_file.content
    }
    tested = {
        criterion_id
        for mapping in tests
        for criterion_id in mapping.acceptance_criterion_ids
    }
    reviewed = {
        item.acceptance_criterion_id for item in review.criterion_reviews
    }
    handed_off = {
        criterion_id
        for criterion_id in required_ids
        if criterion_id in qa_handoff_markdown
    }
    return {
        "implementation_gaps": sorted(required_ids - implemented),
        "test_gaps": sorted(required_ids - tested),
        "review_gaps": sorted(required_ids - reviewed),
        "handoff_gaps": sorted(required_ids - handed_off),
    }

