import logging
from dataclasses import dataclass
from typing import List, Optional, Any, Dict

from pydantic import BaseModel, Field as PydanticField
from pydantic_ai import Agent

# Assuming PromptManager will be used
from app.services.llm.prompt_manager import PromptManager
# Assuming CollectionManager will be used for semantic search capabilities
from app.services.collection_manager import CollectionManager

logger = logging.getLogger(__name__)

# --- Input Model Placeholder ---
# This should ideally align with PhDAgent's ResearchDirection output or a shared model.
class ResearchDirectionInput(BaseModel):
    direction_id: str
    title: str
    description: str
    rationale: str
    related_gap_ids: List[str] = PydanticField(default_factory=list)
    # Add other fields as expected from PhDAgent's output or for assessment context
    # For example, if PhDAgent provides novelty/feasibility scores, they could be inputs here
    # or PostDoc could be designed to re-evaluate them from scratch.


# --- Dependency Definitions ---
@dataclass
class PostDocAgentDependencies:
    prompt_manager: PromptManager
    chromadb_service: Optional[CollectionManager] = None
    llm_manager: Any = None # Placeholder for future LLM-specific configurations
    # chromadb_service: Any = None # If direct Chroma access is needed for context


# --- Output Model Definitions ---

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
    # E.g., "This direction is highly novel (9/10) due to X but faces feasibility challenges (4/10) in Y. To improve, consider Z."

class PostDocEvaluationOutput(BaseModel):
    evaluated_directions: List[OverallAssessment] = PydanticField(description="A list of comprehensive evaluations for each research direction provided.")


# --- PostDoc Agent Definition ---

class PostDocAgent:
    """
    The PostDoc Agent specializes in critical assessment, evaluating novelty
    and feasibility of proposed research directions, and providing constructive feedback.
    It aims to act as a critical reviewer.
    """

    def __init__(self, dependencies: PostDocAgentDependencies, llm_model_name: str = "gemini-pro"):
        self.dependencies = dependencies
        self.llm_model_name = llm_model_name
        self.logger = logging.getLogger(self.__class__.__name__)

        # Initialize sub-agents for distinct assessment tasks
        # These agents will use specific prompts.
        self._novelty_assessor = Agent(
            description="Assesses the novelty of a given research direction against provided context or general knowledge.",
            model=self.llm_model_name,
            deps_type=PostDocAgentDependencies,
            output_type=NoveltyAssessmentOutput
        )
        self._feasibility_assessor = Agent(
            description="Assesses the feasibility of a given research direction, considering practical aspects.",
            model=self.llm_model_name,
            deps_type=PostDocAgentDependencies,
            output_type=FeasibilityAssessmentOutput
        )
        self._critique_synthesizer = Agent(
            description="Synthesizes novelty and feasibility assessments into an overall critique and recommendation.",
            model=self.llm_model_name,
            deps_type=PostDocAgentDependencies,
            output_type=OverallAssessment # This agent will produce the final combined assessment for one direction
        )
        self.logger.info(f"PostDocAgent initialized with LLM: {self.llm_model_name}. Sub-agents ready.")

    async def assess_novelty(
        self, research_direction: ResearchDirectionInput, literature_context_summary: Optional[str] = None,
        session_id: Optional[str] = None # Added session_id for semantic search context
    ) -> NoveltyAssessmentOutput:
        """Assesses the novelty of a single research direction, optionally using semantic search."""
        self.logger.info(f"Assessing novelty for: {research_direction.title} (ID: {research_direction.direction_id})")
        
        semantic_matches_for_prompt = []
        if self.dependencies.chromadb_service and session_id:
            try:
                query_text = f"{research_direction.title} {research_direction.description} {research_direction.rationale}"
                # Assuming search_research_collection returns a list of dicts/objects with id, document, metadata, distance/similarity
                # And that metadata contains title, and document itself can be used as a snippet or part of it.
                # We might need a specific method in CollectionManager to get formatted snippets + scores.
                # For now, let's assume a conceptual `search_similar_documents` method.
                # This method would ideally return something like: [{'id': str, 'title': str, 'similarity_score': float, 'snippet': str}]
                
                # Placeholder for actual search call structure - this will need to align with CollectionManager's capabilities
                # search_results = await self.dependencies.chromadb_service.search_similar_documents(
                #     query_text=query_text,
                #     session_id=session_id,
                #     top_n=3 # Get top 3 similar documents
                # )
                # For testing, let's mock this part until CollectionManager method is confirmed/implemented
                search_results = [] # Mock: no results
                # Example of mocked results if search was successful:
                # search_results = [
                #     {'id': 'doc1', 'title': 'Very Similar Existing Paper A', 'similarity_score': 0.92, 'snippet': 'This paper discusses almost the exact same concept...'},
                #     {'id': 'doc2', 'title': 'Related Work B', 'similarity_score': 0.85, 'snippet': 'Focuses on a related sub-problem using method Y...'}
                # ]

                if search_results:
                    self.logger.info(f"Found {len(search_results)} semantic matches for novelty assessment.")
                    semantic_matches_for_prompt = search_results
                else:
                    self.logger.info("No direct semantic matches found via chromadb_service for novelty context.")
            except Exception as e:
                self.logger.error(f"Error during semantic search for novelty assessment: {e}", exc_info=True)
                # Proceed without semantic matches if search fails
        elif not session_id and self.dependencies.chromadb_service:
            self.logger.warning("chromadb_service is available, but no session_id provided for semantic search context.")

        prompt_name = "postdoc_postdoc_novelty_assessment" 
        template_vars = {
            "direction": research_direction.model_dump(),
            "context": literature_context_summary if literature_context_summary else "No specific textual literature context summary was provided.",
            "semantic_matches": semantic_matches_for_prompt # Pass the search results to the template
        }

        try:
            instructions = self.dependencies.prompt_manager.format_prompt(prompt_name, **template_vars)
            self.logger.debug(f"Rendered instructions for {prompt_name}:\n{instructions}")

            # User prompt for pydantic-ai agent can be minimal if instructions are comprehensive
            user_prompt_content = f"Assess the novelty of research direction: {research_direction.title}"
            
            result = await self._novelty_assessor.run(
                user_prompt_content,
                instructions=instructions,
                deps=self.dependencies
            )
            # Ensure the direction_id in the output matches the input
            if result.output.direction_id != research_direction.direction_id:
                self.logger.warning(
                    f"Novelty assessment for {research_direction.direction_id} returned with mismatched ID {result.output.direction_id}. Overwriting."
                )
                result.output.direction_id = research_direction.direction_id
            return result.output
        except KeyError as e:
            self.logger.error(f"Prompt template '{prompt_name}' not found: {e}")
            # Fallback or re-raise, for now, creating a default error-indicating output
            return NoveltyAssessmentOutput(
                direction_id=research_direction.direction_id,
                novelty_score=0.0,
                novelty_justification=f"Error: Prompt template '{prompt_name}' not found.",
                related_work_references=[]
            )
        except Exception as e:
            self.logger.error(f"Error during novelty assessment for {research_direction.direction_id}: {e}", exc_info=True)
            # Fallback or re-raise
            return NoveltyAssessmentOutput(
                direction_id=research_direction.direction_id,
                novelty_score=0.0,
                novelty_justification=f"An unexpected error occurred during novelty assessment: {str(e)}",
                related_work_references=[]
            )

    async def assess_feasibility(
        self, research_direction: ResearchDirectionInput
    ) -> FeasibilityAssessmentOutput:
        """Assesses the feasibility of a single research direction."""
        self.logger.info(f"Assessing feasibility for: {research_direction.title} (ID: {research_direction.direction_id})")
        
        prompt_name = "postdoc_postdoc_feasibility_assessment"
        template_vars = {
            "direction": research_direction.model_dump()
        }

        try:
            instructions = self.dependencies.prompt_manager.format_prompt(prompt_name, **template_vars)
            self.logger.debug(f"Rendered instructions for {prompt_name}:\n{instructions}")

            user_prompt_content = f"Assess the feasibility of research direction: {research_direction.title}"
            
            result = await self._feasibility_assessor.run(
                user_prompt_content,
                instructions=instructions,
                deps=self.dependencies
            )
            if result.output.direction_id != research_direction.direction_id:
                self.logger.warning(
                    f"Feasibility assessment for {research_direction.direction_id} returned with mismatched ID {result.output.direction_id}. Overwriting."
                )
                result.output.direction_id = research_direction.direction_id
            return result.output
        except KeyError as e:
            self.logger.error(f"Prompt template '{prompt_name}' not found: {e}")
            return FeasibilityAssessmentOutput(
                direction_id=research_direction.direction_id,
                feasibility_score=0.0,
                feasibility_justification=f"Error: Prompt template '{prompt_name}' not found.",
                identified_challenges=[],
                suggested_mitigations=[]
            )
        except Exception as e:
            self.logger.error(f"Error during feasibility assessment for {research_direction.direction_id}: {e}", exc_info=True)
            return FeasibilityAssessmentOutput(
                direction_id=research_direction.direction_id,
                feasibility_score=0.0,
                feasibility_justification=f"An unexpected error occurred during feasibility assessment: {str(e)}",
                identified_challenges=[],
                suggested_mitigations=[]
            )

    async def synthesize_critique(
        self,
        research_direction: ResearchDirectionInput,
        novelty_assessment: NoveltyAssessmentOutput,
        feasibility_assessment: FeasibilityAssessmentOutput
    ) -> OverallAssessment:
        """Synthesizes novelty and feasibility into an overall critique and recommendation."""
        self.logger.info(f"Synthesizing critique for: {research_direction.title} (ID: {research_direction.direction_id})")

        prompt_name = "postdoc_postdoc_critique_synthesis"
        template_vars = {
            "direction": research_direction.model_dump(),
            "novelty": novelty_assessment.model_dump(),
            "feasibility": feasibility_assessment.model_dump()
        }

        try:
            instructions = self.dependencies.prompt_manager.format_prompt(prompt_name, **template_vars)
            self.logger.debug(f"Rendered instructions for {prompt_name}:\n{instructions}")

            user_prompt_content = f"Synthesize critique for research direction: {research_direction.title}"
            
            result = await self._critique_synthesizer.run(
                user_prompt_content,
                instructions=instructions,
                deps=self.dependencies
            )

            # Ensure the main direction_id and nested assessments are consistent
            # The LLM is asked to copy novelty/feasibility, but we verify.
            output_assessment = result.output
            if output_assessment.direction_id != research_direction.direction_id:
                self.logger.warning(
                    f"Critique synthesis for {research_direction.direction_id} returned with mismatched ID {output_assessment.direction_id}. Overwriting."
                )
                output_assessment.direction_id = research_direction.direction_id
            
            # Ensure nested assessments are the ones we provided as input, as LLM might regenerate them
            output_assessment.novelty_assessment = novelty_assessment
            output_assessment.feasibility_assessment = feasibility_assessment
            
            return output_assessment
        except KeyError as e:
            self.logger.error(f"Prompt template '{prompt_name}' not found: {e}")
            # Fallback: return an OverallAssessment with input assessments and error message in critique
            return OverallAssessment(
                direction_id=research_direction.direction_id,
                novelty_assessment=novelty_assessment,
                feasibility_assessment=feasibility_assessment,
                overall_recommendation_score=0.0,
                constructive_critique=f"Error: Prompt template '{prompt_name}' not found."
            )
        except Exception as e:
            self.logger.error(f"Error during critique synthesis for {research_direction.direction_id}: {e}", exc_info=True)
            return OverallAssessment(
                direction_id=research_direction.direction_id,
                novelty_assessment=novelty_assessment,
                feasibility_assessment=feasibility_assessment,
                overall_recommendation_score=0.0,
                constructive_critique=f"An unexpected error occurred during critique synthesis: {str(e)}"
            )

    async def evaluate_direction(
        self, research_direction: ResearchDirectionInput, literature_context_summary: Optional[str] = None,
        session_id: Optional[str] = None # Propagate session_id
    ) -> OverallAssessment:
        """
        Performs a full evaluation (novelty, feasibility, critique) for a single research direction.
        """
        self.logger.info(f"Starting full evaluation for direction ID: {research_direction.direction_id} - '{research_direction.title}'")
        
        novelty_output = await self.assess_novelty(research_direction, literature_context_summary, session_id)
        feasibility_output = await self.assess_feasibility(research_direction)
        
        overall_assessment = await self.synthesize_critique(
            research_direction=research_direction,
            novelty_assessment=novelty_output,
            feasibility_assessment=feasibility_output
        )
        
        self.logger.info(f"Completed full evaluation for direction ID: {research_direction.direction_id}")
        return overall_assessment

    async def evaluate_directions_batch(
        self,
        research_directions: List[ResearchDirectionInput],
        literature_context_summary: Optional[str] = None
    ) -> PostDocEvaluationOutput:
        """
        Evaluates a batch of research directions.
        For simplicity, this implementation iterates and calls evaluate_direction.
        In a production system, one might explore batching calls to the LLM if the underlying
        pydantic-ai Agent or LLM provider supports it for efficiency.
        """
        self.logger.info(f"Evaluating a batch of {len(research_directions)} research directions.")
        evaluations: List[OverallAssessment] = []
        for direction in research_directions:
            assessment = await self.evaluate_direction(direction, literature_context_summary)
            evaluations.append(assessment)
        
        return PostDocEvaluationOutput(evaluated_directions=evaluations)

# --- Main Test Function Placeholder ---
async def main_postdoc_test():
    logging.basicConfig(level=logging.DEBUG)
    logger.info("Starting PostDocAgent main_test...")

    # Setup real PromptManager
    from pathlib import Path
    # Assuming this script is in backend/app/agents/postdoc_agent.py
    # Prompts are in backend/app/agents/prompts/
    # The PromptManager expects the path to the *directory containing* the agent-specific prompt folders (e.g., 'phd', 'postdoc')
    prompts_base_dir = Path(__file__).resolve().parent / "prompts"
    
    try:
        # Ensure the 'postdoc' subdirectory exists if PromptManager expects it to be created beforehand
        # or if it scans for specific subdirectories. For now, we assume it can handle it.
        actual_prompt_manager = PromptManager(template_dir=str(prompts_base_dir))
        # Test if it can load a specific prompt (optional sanity check)
        # actual_prompt_manager.get_template("postdoc_novelty_assessment") 
    except Exception as e:
        logger.error(f"Failed to initialize PromptManager for PostDoc test: {e} at path {prompts_base_dir}", exc_info=True)
        return

    deps = PostDocAgentDependencies(prompt_manager=actual_prompt_manager)
    # Consider using a more cost-effective model for testing if available, e.g., gemini-1.5-flash-latest or similar
    postdoc_agent = PostDocAgent(dependencies=deps, llm_model_name="gemini-1.5-flash-latest") 

    sample_direction = ResearchDirectionInput(
        direction_id="test_dir_001",
        title="Quantum Entanglement for Faster-Than-Light Communication",
        description="This research proposes to leverage principles of quantum entanglement to achieve instantaneous communication across vast interstellar distances, bypassing the limitations of the speed of light.",
        rationale="Current communication technologies are bottlenecked by light speed, hindering deep space exploration. Quantum entanglement offers a theoretical loophole. The primary gap is the lack of experimental validation for information transfer.",
        related_gap_ids=["gap_ftl_comm_01"]
    )
    sample_context = ("Existing literature extensively covers quantum entanglement (Einstein-Podolsky-Rosen paradox, Bell's theorem) and its non-local correlations. However, the No-Communication Theorem is a widely accepted principle stating that entanglement cannot be used to transmit classical information faster than light. Some fringe theories propose loopholes, but lack experimental backing. The proposed direction directly challenges this theorem.")
    sample_session_id = "test_session_123" # Added for testing semantic search path

    try:
        logger.info(f"--- Testing single direction evaluation for '{sample_direction.title}' ---")
        # Pass session_id to evaluate_direction
        evaluation_result = await postdoc_agent.evaluate_direction(sample_direction, sample_context, sample_session_id)
        print("\n--- Evaluation Result --- \n")
        print(evaluation_result.model_dump_json(indent=2))

        # logger.info(f"--- Testing batch direction evaluation --- ")
        # # Add another sample direction for batch testing if desired
        # batch_result = await postdoc_agent.evaluate_directions_batch([sample_direction], sample_context)
        # print("\n--- Batch Evaluation Result --- \n")
        # print(batch_result.model_dump_json(indent=2))

    except Exception as e:
        logger.error(f"Error in PostDocAgent main_test: {e}", exc_info=True)

if __name__ == "__main__":
    import asyncio
    # To run this test, ensure GOOGLE_API_KEY (or other relevant LLM provider key) is set in your environment.
    asyncio.run(main_postdoc_test())
    # print("PostDocAgent class structure and methods implemented.") 