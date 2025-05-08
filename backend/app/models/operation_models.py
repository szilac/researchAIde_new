"""Pydantic models for agent operation inputs and outputs."""
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field as PydanticField

# --- General Input Model --- 
class OrchestratorInputModel(BaseModel):
    user_id: str
    conversation_id: str
    query: str
    session_id: Optional[str] = None # Added session_id for broader use

# --- Models from PhDAgent --- 

class ChromaSearchResult(BaseModel):
    id: str
    document: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    distance: Optional[float] = None

class ChromaQuerySummary(BaseModel):
    query: str
    num_results: int
    summary_of_findings: str

class FormulatedQuery(BaseModel):
    query_string: str = PydanticField(description="The formulated search query string, optimized for Arxiv.")
    source_topic: str = PydanticField(description="The original research topic fragment this query targets.")

class FormulatedQueriesOutput(BaseModel):
    queries: List[FormulatedQuery] = PydanticField(description="A list of formulated search queries.")
    original_topic: str = PydanticField(description="The original research topic provided by the user.")

class PaperRelevanceAssessment(BaseModel):
    paper_id: str = PydanticField(description="Identifier of the paper (e.g., Arxiv ID).")
    is_relevant: bool = PydanticField(description="Boolean indicating if the paper is relevant.")
    relevance_score: float = PydanticField(description="A numerical score of relevance (e.g., 0.0 to 10.0).", ge=0.0, le=10.0)

class PaperRelevanceOutput(BaseModel):
    assessments: List[PaperRelevanceAssessment] = PydanticField(description="List of relevance assessments for papers.")

class LiteratureAnalysisOutput(BaseModel):
    research_topic: str = PydanticField(description="The original research topic provided.")
    overall_summary: str = PydanticField(description="A concise summary synthesizing the key findings, themes, and methodologies from the provided literature relevant to the research topic.")
    key_themes: List[str] = PydanticField(description="List of major recurring themes or concepts identified in the literature.")
    common_methodologies: List[str] = PydanticField(description="List of common methodologies or approaches employed in the literature.")
    identified_limitations: List[str] = PydanticField(description="List of explicitly mentioned limitations or shortcomings in the literature.")
    future_work_suggestions: List[str] = PydanticField(description="List of suggestions for future work or unanswered questions found in the literature.")

class ResearchGap(BaseModel):
    gap_id: str = PydanticField(description="A concise, descriptive, slug-like ID for the research gap.")
    title: str = PydanticField(description="A short, descriptive title for the research gap.")
    description: str = PydanticField(description="A detailed explanation of what is missing or underexplored.")
    supporting_evidence_summary: str = PydanticField(description="Summary of evidence from literature/vector search supporting this gap.")
    keywords: List[str] = PydanticField(description="Keywords associated with this research gap.")
    potential_questions_to_explore: List[str] = PydanticField(description="Potential research questions to explore to address this gap.")

class IdentifiedGapsOutput(BaseModel):
    research_topic: str = PydanticField(description="The original research topic for which gaps were identified.")
    gaps: List[ResearchGap] = PydanticField(description="List of identified research gaps.")

class ResearchDirection(BaseModel):
    direction_id: str = PydanticField(description="A unique identifier for the research direction.")
    title: str = PydanticField(description="A concise title for the research direction.")
    description: str = PydanticField(description="Detailed description of the potential research direction.")
    rationale: str = PydanticField(description="Rationale linking this direction to identified gaps and literature.")
    potential_impact: Optional[str] = PydanticField(default=None, description="Assessment of the potential impact of pursuing this direction.")
    potential_challenges: Optional[str] = PydanticField(default=None, description="Potential challenges in pursuing this direction.")
    related_gap_ids: List[str] = PydanticField(default_factory=list, description="IDs of research gaps this direction addresses.")

class GeneratedDirectionsOutput(BaseModel):
    directions: List[ResearchDirection] = PydanticField(description="List of generated research directions.")
    summary: Optional[str] = PydanticField(default=None, description="Summary of the generated directions.")


# --- Models from PostDocAgent --- (ResearchDirection is already defined above)

class NoveltyAssessmentOutput(BaseModel):
    direction_id: str = PydanticField(description="The ID of the research direction being assessed.")
    novelty_score: float = PydanticField(description="Score from 0.0 (not novel) to 10.0 (highly novel)", ge=0.0, le=10.0)
    novelty_justification: str = PydanticField(description="Explanation for the novelty score, citing evidence or lack thereof from the provided context or general knowledge.")
    related_work_references: Optional[List[str]] = PydanticField(default=None, description="Key references or pointers to existing work that diminishes or supports novelty.")

class FeasibilityAssessmentOutput(BaseModel):
    direction_id: str = PydanticField(description="The ID of the research direction being assessed.")
    feasibility_score: float = PydanticField(description="Score from 0.0 (not feasible) to 10.0 (highly feasible)", ge=0.0, le=10.0)
    feasibility_justification: str = PydanticField(description="Explanation for the feasibility score, considering methodology, resources, time, ethical considerations, etc.")
    identified_challenges: List[str] = PydanticField(default_factory=list, description="Specific challenges identified that impact feasibility.")
    suggested_mitigations: Optional[List[str]] = PydanticField(default=None, description="Potential strategies to overcome identified challenges.")

class OverallAssessment(BaseModel):
    direction_id: str = PydanticField(description="The ID of the research direction.")
    novelty_assessment: NoveltyAssessmentOutput
    feasibility_assessment: FeasibilityAssessmentOutput
    overall_recommendation_score: float = PydanticField(description="An overall score (0.0-10.0) reflecting the combined promise of the direction, considering novelty, feasibility, potential impact, and alignment with research goals.", ge=0.0, le=10.0)
    constructive_critique: str = PydanticField(description="A comprehensive critique addressing strengths, weaknesses, and providing specific, actionable suggestions for improvement.")

class PostDocEvaluationOutput(BaseModel):
    evaluated_directions: List[OverallAssessment] = PydanticField(description="A list of comprehensive evaluations for each research direction provided.") 