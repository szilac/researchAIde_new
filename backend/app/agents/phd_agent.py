import logging
from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict

from pydantic_ai import Agent

from app.services.llm.prompt_manager import PromptManager
from app.models.operation_models import (
    ChromaSearchResult,
    ChromaQuerySummary,
    FormulatedQuery,
    FormulatedQueriesOutput,
    PaperRelevanceAssessment,
    PaperRelevanceOutput,
    LiteratureAnalysisOutput,
    ResearchGap,
    IdentifiedGapsOutput,
    ResearchDirection,
    GeneratedDirectionsOutput
)

# Placeholder for actual service imports - will be updated as services are implemented/refactored
# from ..services.arxiv_service import ArxivService
# from ..services.chroma_service import ChromaDBService # Assuming ChromaDBService from Task 7
# from ..services.llm_service import LLMManager # Assuming LLMManager from Task 4

logger = logging.getLogger(__name__)

# --- Dependency Definitions ---

@dataclass
class PhDAgentDependencies:
    prompt_manager: PromptManager
    arxiv_service: Any = None 
    chromadb_service: Any = None 
    llm_manager: Any = None 
    # Potentially other shared services or configurations

# --- Output Model Definitions --- MOVED TO operation_models.py ---

# --- PhD Student Agent Definition ---

class PhDAgent:
    """
    The PhD Student Agent focuses on literature analysis, gap identification, 
    and research direction generation.
    Uses PromptManager for dynamic prompts.
    """
    # Constants
    MAX_CONTENT_LENGTH_FOR_ANALYSIS = 30000 # Limit context window for analysis agent

    def __init__(self, dependencies: PhDAgentDependencies, llm_model_name: str = "gemini-2.0-flash-lite"):
        self.dependencies = dependencies
        self.llm_model_name = llm_model_name
        self.logger = logging.getLogger(self.__class__.__name__)

        # Initialize sub-agents WITHOUT system_prompt at init time
        self._query_formulation_agent = Agent(
            description="Formulates search queries based on a research topic.",
            model=self.llm_model_name,
            deps_type=PhDAgentDependencies,
            output_type=FormulatedQueriesOutput
            # system_prompt removed
        )

        self._relevance_assessment_agent = Agent(
            description="Assesses the relevance of a paper to a research topic.",
            model=self.llm_model_name,
            deps_type=PhDAgentDependencies,
            output_type=PaperRelevanceOutput
            # system_prompt removed
        )

        self._literature_analyzer_agent = Agent(
            description="Analyzes and synthesizes literature based on provided content.",
            model=self.llm_model_name,
            deps_type=PhDAgentDependencies,
            output_type=LiteratureAnalysisOutput
            # system_prompt removed
        )
        
        self._gap_identification_agent = Agent(
            description="Identifies research gaps based on literature analysis and vector search summaries.",
            model=self.llm_model_name,
            deps_type=PhDAgentDependencies,
            output_type=IdentifiedGapsOutput
            # system_prompt removed
        )
        self._direction_generation_agent = Agent(
            description="Generates research directions based on literature analysis and identified gaps.",
            model=self.llm_model_name,
            deps_type=PhDAgentDependencies,
            output_type=GeneratedDirectionsOutput
            # system_prompt removed
        )
        self._direction_refinement_agent = Agent(
            description="Refines research directions based on user feedback.",
            model=self.llm_model_name,
            deps_type=PhDAgentDependencies,
            output_type=GeneratedDirectionsOutput
            # system_prompt removed
        )
        self.logger.info(f"PhDAgent initialized. Sub-agents will load prompts at runtime.")

    async def formulate_search_queries(self, research_topic: str, general_area: Optional[str] = None) -> FormulatedQueriesOutput:
        self.logger.info(f"Formulating search a query for topic: {research_topic}")
        try:
            template = self.dependencies.prompt_manager.get_template('phd_query_formulation')
            # Ensure query_formulation.j2 uses research_topic and general_area for full instructions.
            rendered_instructions = template.render(research_topic=research_topic, general_area=general_area or "")
            self.logger.info(f"Rendered instructions for query_formulation:\n{rendered_instructions}")
        except Exception as e:
            self.logger.error(f"Failed to load/render query_formulation prompt: {e}")
            raise

        # Simplified user_prompt_content, assuming instructions in template are comprehensive.
        user_prompt_content = f"Formulate search queries for research topic: {research_topic}"
        if general_area:
            user_prompt_content += f" (General Area: {general_area})"


        llm_result = await self._query_formulation_agent.run(
            user_prompt_content,
            instructions=rendered_instructions, 
            deps=self.dependencies
        )
        
        # Ensure only one query is returned, even if LLM provides more
        final_queries = []
        if llm_result.output and llm_result.output.queries:
            final_queries.append(llm_result.output.queries[0]) # Take the first query
            if len(llm_result.output.queries) > 1:
                self.logger.warning(f"LLM generated {len(llm_result.output.queries)} queries, but only the first one will be used as per agent design.")
        
        self.logger.info(f"Formulated queries output: {final_queries}")
        
        return FormulatedQueriesOutput(
            queries=final_queries,
            original_topic=research_topic # or llm_result.output.original_topic if it exists and is preferred
        )
        

    async def assess_paper_relevance(
        self, paper_id: str, title: str, abstract: str, research_topic: str
    ) -> PaperRelevanceOutput:
        self.logger.info(f"Assessing relevance of paper '{paper_id}' for topic: {research_topic}")
        try:
            template = self.dependencies.prompt_manager.get_template('phd_relevance_assessment')
            # Ensure relevance_assessment.j2 uses all provided variables for full instructions.
            rendered_instructions = template.render(research_topic=research_topic, paper_id=paper_id, title=title, abstract=abstract)
        except Exception as e:
            self.logger.error(f"Failed to load/render relevance_assessment prompt: {e}")
            raise

        # Simplified user_prompt_content, assuming instructions in template are comprehensive.
        user_prompt_content = f"Assess paper relevance for ID: {paper_id} concerning topic: {research_topic}"
        
        result = await self._relevance_assessment_agent.run(
            user_prompt_content,
            instructions=rendered_instructions,
            deps=self.dependencies
        )
        return result.output

    async def analyze_literature(
        self, research_topic: str, relevant_paper_ids: List[str], session_id: Optional[str] = None
    ) -> LiteratureAnalysisOutput:
        self.logger.info(
            f"Analyzing literature for topic: {research_topic} based on {len(relevant_paper_ids)} paper IDs."
        )
        
        paper_contents: List[str] = []
        collection_manager = self.dependencies.chromadb_service # Assumed to be CollectionManager instance

        if not relevant_paper_ids:
            self.logger.info("No relevant paper IDs provided, proceeding with empty content for analysis.")
        elif not session_id:
            self.logger.warning(
                "Session ID not provided. Cannot fetch papers from a session-specific collection. "
                "Proceeding with empty paper_contents."
            )
        elif collection_manager and hasattr(collection_manager, 'get_research_collection'):
            try:
                # In a fully async app, sync calls like get_research_collection and collection.get
                # should be wrapped (e.g., asyncio.to_thread) if chromadb_service methods are sync.
                # For now, assuming direct call is acceptable for the context or service is designed for async.
                collection = collection_manager.get_research_collection(session_id=session_id)
                
                if collection and hasattr(collection, 'get'):
                    self.logger.debug(f"Retrieved collection '{collection.name}' for session '{session_id}'. Fetching documents.")
                    # ChromaDB's collection.get is synchronous.
                    retrieved_data = collection.get(ids=relevant_paper_ids, include=["documents"])
                    
                    if retrieved_data and retrieved_data.get('documents'):
                        # Filter out None values if any documents were not found for the given IDs
                        fetched_docs = retrieved_data['documents']
                        paper_contents = [doc for doc in fetched_docs if doc is not None]
                        if len(paper_contents) < len(relevant_paper_ids):
                            self.logger.warning(
                                f"Fetched {len(paper_contents)} documents out of {len(relevant_paper_ids)} requested IDs "
                                f"from collection '{collection.name}'. Some IDs might not have been found."
                            )
                    else:
                         self.logger.warning(
                            f"Collection '{collection.name}' returned no documents field or empty documents for IDs: {relevant_paper_ids}"
                        )
                    if not paper_contents and relevant_paper_ids:
                         self.logger.warning(
                            f"No documents successfully fetched for IDs: {relevant_paper_ids} from collection '{collection.name}'."
                        )
                elif relevant_paper_ids:
                    self.logger.warning(
                        f"Could not retrieve collection for session_id: '{session_id}' or collection has no 'get' method. "
                        f"Proceeding with empty paper_contents."
                    )
            except Exception as e:
                self.logger.error(
                    f"Error fetching documents via CollectionManager for session '{session_id}', IDs {relevant_paper_ids}: {e}",
                    exc_info=True
                )
                # Proceed with empty paper_contents after error
        elif relevant_paper_ids: # relevant_paper_ids is True, but collection_manager or its method is missing
            self.logger.warning(
                "ChromaDB service (CollectionManager) or 'get_research_collection' method is not available. "
                "Proceeding with empty paper_contents for analysis."
            )

        if not paper_contents and relevant_paper_ids:
            self.logger.info(
                f"No paper contents were available for IDs: {relevant_paper_ids} (session: {session_id}). "
                f"Literature analysis will be based on an empty content set."
            )
            paper_contents = [] # Ensure it's an empty list if all attempts fail

        combined_content = "\n\n---\nPaper Break\n---\n\n".join(paper_contents)

        # Truncate combined_content first if it exceeds MAX_CONTENT_LENGTH_FOR_ANALYSIS
        if len(combined_content) > self.MAX_CONTENT_LENGTH_FOR_ANALYSIS:
            self.logger.warning(
                f"Combined content length {len(combined_content)} exceeds max "
                f"{self.MAX_CONTENT_LENGTH_FOR_ANALYSIS}. Truncating before template rendering."
            )
            combined_content = combined_content[:self.MAX_CONTENT_LENGTH_FOR_ANALYSIS] + "... [TRUNCATED]"

        template_data = {
            "research_topic": research_topic,
            "combined_content": combined_content
        }
        # No other individual fields to truncate here via _truncate_input_data for this specific method,
        # as combined_content is handled specially due to its potentially very large size.

        try:
            template = self.dependencies.prompt_manager.get_template('phd_literature_analyzer')
            rendered_instructions = template.render(**template_data) # Use the potentially truncated data
            self.logger.debug(f"Rendered instructions for literature_analyzer:\n{rendered_instructions}") # Log the rendered prompt
        except Exception as e:
            self.logger.error(f"Failed to load/render literature_analyzer prompt: {e}")
            raise

        # The user_prompt can be minimal as the detailed instructions and content are in rendered_instructions
        user_prompt_content = f"Analyze literature for topic: {research_topic}"

        result = await self._literature_analyzer_agent.run(
            user_prompt_content, 
            instructions=rendered_instructions, 
            deps=self.dependencies
        )
        return result.output
    
    async def identify_research_gaps(
        self, 
        research_topic: str, 
        literature_analysis: LiteratureAnalysisOutput, 
        chroma_query_summaries: Optional[List[ChromaQuerySummary]] = None
    ) -> IdentifiedGapsOutput:
        self.logger.info(f"Identifying research gaps for topic: {research_topic}")
        try:
            template = self.dependencies.prompt_manager.get_template('phd_gap_identification')
            rendered_instructions = template.render(
                research_topic=research_topic,
                literature_analysis=literature_analysis.model_dump(), 
                chroma_query_summaries=[s.model_dump() for s in chroma_query_summaries] if chroma_query_summaries else []
            )
        except Exception as e:
            self.logger.error(f"Failed to load/render gap_identification prompt: {e}")
            raise

        user_prompt_content = f"Identify research gaps for: {research_topic}, based on provided analysis and summaries."

        result = await self._gap_identification_agent.run(
            user_prompt_content, 
            instructions=rendered_instructions, 
            deps=self.dependencies
        )
        return result.output

    async def generate_research_directions(
        self, identified_gaps: IdentifiedGapsOutput, literature_analysis_results: LiteratureAnalysisOutput # Updated type hint
    ) -> GeneratedDirectionsOutput:
        """
        Generates potential research directions based on identified gaps and literature.
        Formats directions with title, description, rationale, impact, and challenges.
        """
        self.logger.info("Generating research directions based on identified gaps and literature analysis.")
        try:
            template = self.dependencies.prompt_manager.get_template('phd_direction_generation')
            rendered_instructions = template.render(
                identified_gaps=identified_gaps.model_dump(),
                literature_analysis_results=literature_analysis_results.model_dump()
            )
        except Exception as e:
            self.logger.error(f"Failed to load/render direction_generation prompt: {e}")
            raise

        user_prompt_content = "Generate research directions based on the provided literature analysis and identified research gaps."

        result = await self._direction_generation_agent.run(
            user_prompt_content,
            instructions=rendered_instructions,
            deps=self.dependencies
        )
        return result.output

    async def refine_directions(
        self, current_directions: GeneratedDirectionsOutput, user_feedback: str
    ) -> GeneratedDirectionsOutput:
        """
        Refines generated research directions based on user feedback.
        """
        self.logger.info("Refining research directions based on user feedback.")
        try:
            template = self.dependencies.prompt_manager.get_template('phd_direction_refinement')
            rendered_instructions = template.render(
                current_directions=current_directions.model_dump(),
                user_feedback=user_feedback
            )
        except Exception as e:
            self.logger.error(f"Failed to load/render direction_refinement prompt: {e}")
            raise

        user_prompt_content = "Refine the provided research directions based on the user feedback."

        result = await self._direction_refinement_agent.run(
            user_prompt_content,
            instructions=rendered_instructions,
            deps=self.dependencies
        )
        return result.output

# Example usage (for testing locally, not part of the final class structure)
async def main_test():
    logging.basicConfig(level=logging.DEBUG) # Use DEBUG for more verbose logs from agent
    logger.info("Starting PhDAgent main_test...")

    from pathlib import Path
    # Assuming a standard project structure where this script is in backend/app/agents
    # and prompts are in backend/app/agents/prompts
    # Adjust the path if your structure is different.
    # Path to the backend directory
    backend_dir = Path(__file__).resolve().parent.parent # Moves up from agents -> app -> backend
    # Path to the specific prompts folder for phd agent
    # This should be backend/app/agents/prompts
    # If PromptManager expects the *parent* of /phd, then it's backend/app/agents/prompts
    # If PromptManager expects to be told where "phd" subdirectory is, it's backend/app/agents/prompts/phd
    # Let's assume PromptManager constructor takes the folder containing subdirectories like 'phd'
    # Correct path to the folder containing the 'phd' subdirectory of prompts
    # This is backend/app/agents/prompts
    # From current file: backend/app/agents/phd_agent.py
    # ../prompts => backend/app/agents/prompts
    prompts_base_dir = Path(__file__).resolve().parent / "prompts"

    # Mock dependencies
    # Bring ChromaQuerySummary from the new location for the mock summaries
    from app.models.operation_models import ChromaQuerySummary 

    class MockChromaDBService: # This will now act as a mock CollectionManager
        def get_research_collection(self, session_id: str):
            if session_id == "test_session_123":
                # Return a mock Collection object
                class MockCollection:
                    def __init__(self, name):
                        self.name = name
                    def get(self, ids: List[str], include: List[str]):
                        # Simulate ChromaDB's get behavior
                        docs_content = {
                            "paper_id_1": "Reinforcement learning (RL) has demonstrated significant potential in optimizing diagnostic pathways, particularly in oncological imaging. Our recent study indicates that RL models can reduce time-to-diagnosis by approximately 15%. However, a critical challenge remains in ensuring fairness and equity across diverse demographic groups. Future work must focus on developing reward shaping mechanisms that explicitly account for and mitigate potential biases to ensure equitable outcomes.",
                            "paper_id_2": "A comparative analysis of Q-learning and SARSA algorithms for early sepsis prediction using electronic health record (EHR) data reveals Q-learning's superior predictive accuracy by a margin of 7%. A key limitation identified is the model's sensitivity to incomplete data streams, which are common in real-world healthcare environments. This suggests an urgent need for future research into robust RL techniques capable of handling missing data and addressing biases introduced by imputation methods, especially when considering equitable application across varied patient populations.",
                            "paper_id_3": None # Simulate a document not found or with no content
                        }
                        returned_docs = []
                        returned_ids = []
                        # ChromaDB returns documents in the order of requested IDs, with None if not found.
                        for paper_id in ids:
                            returned_ids.append(paper_id)
                            returned_docs.append(docs_content.get(paper_id))
                        
                        return {
                            "ids": returned_ids,
                            "documents": returned_docs,
                            "metadatas": [{} for _ in ids], # Dummy metadatas
                            "embeddings": None # Not requesting embeddings
                        }
                return MockCollection(name=f"research_session_{session_id}")
            return None

    class MockArxivService: pass
    class MockLLMManager: pass
    # Removed MockPromptManager

    try:
        # Initialize the actual PromptManager
        # The PromptManager expects the path to the folder *containing* the 'phd' directory
        actual_prompt_manager = PromptManager(template_dir=prompts_base_dir)
    except Exception as e:
        logger.error(f"Failed to initialize PromptManager: {e}. Check path: {prompts_base_dir}")
        return

    deps = PhDAgentDependencies(
        arxiv_service=MockArxivService(),
        chromadb_service=MockChromaDBService(), # Instance of our mock CollectionManager
        llm_manager=MockLLMManager(),
        prompt_manager=actual_prompt_manager # Use the real PromptManager
    )
    
    phd_agent = PhDAgent(dependencies=deps, llm_model_name="gemini-1.5-flash-latest") 
    
    topic = "Applications of reinforcement learning in healthcare diagnostics focusing on equity"
    research_area = "AI in Healthcare"
    session_id_test = "test_session_123"

    try:
        # 1. Formulate queries
        queries_output = await phd_agent.formulate_search_queries(research_topic=topic, general_area=research_area)
        print("\n--- Formulated Queries ---")
        for query in queries_output.queries:
            print(f"- Query: {query.query_string} (Topic: {query.source_topic})")
        print(f"Original Topic: {queries_output.original_topic}")

        # 2. Assess paper relevance (simplified for test)
        sample_paper_metadata = {
            "paper_id": "2303.10130",
            "title": "A Survey of Reinforcement Learning for Healthcare",
            "abstract": "This paper surveys the recent advances in reinforcement learning (RL) for healthcare... but lacks focus on equity considerations."
        }
        assessment_output = await phd_agent.assess_paper_relevance(
            paper_id=sample_paper_metadata["paper_id"],
            title=sample_paper_metadata["title"],
            abstract=sample_paper_metadata["abstract"],
            research_topic=topic
        )
        print("\n--- Paper Relevance Assessment ---")
        for assessment in assessment_output.assessments:
            print(f"Paper ID: {assessment.paper_id}, Relevant: {assessment.is_relevant}, Score: {assessment.relevance_score}")

        # 3. Analyze literature (using the new method, expecting structured output)
        # In a real test, provide meaningful content. Here, using placeholders.
        mock_paper_ids_for_analysis = ["paper_id_1", "paper_id_2", "paper_id_3"] 
        
        analyzed_lit = await phd_agent.analyze_literature(
            research_topic=topic,
            relevant_paper_ids=mock_paper_ids_for_analysis,
            session_id=session_id_test
        )

        print("\n--- Literature Analysis Output ---")
        print(f"Overall Summary: {analyzed_lit.overall_summary}")
        print(f"Key Themes: {analyzed_lit.key_themes}")
        print(f"Common Methodologies: {analyzed_lit.common_methodologies}")
        print(f"Identified Limitations: {analyzed_lit.identified_limitations}")
        print(f"Future Work Suggestions: {analyzed_lit.future_work_suggestions}")

        # 4. Test Gap Identification (Example - depends on LiteratureAnalysisOutput)
        if 'analyzed_lit' in locals() and analyzed_lit is not None:
            try:
                logger.info(f"Testing gap identification based on previous analysis...")
                # Example chroma summaries (replace with actual if testing with ChromaDB)
                example_chroma_summaries = [
                    ChromaQuerySummary(query="LLM code generation techniques", num_results=10, summary_of_findings="Many papers on general techniques, few on specific language X."),
                    ChromaQuerySummary(query="LLM code security", num_results=3, summary_of_findings="Limited research on vulnerability detection in LLM-generated code.")
                ]
                gaps_output = await phd_agent.identify_research_gaps(
                    research_topic=analyzed_lit.research_topic,
                    literature_analysis=analyzed_lit,
                    chroma_query_summaries=example_chroma_summaries
                )
                logger.info(f"Identified Gaps Output for '{gaps_output.research_topic}':")
                for gap in gaps_output.gaps:
                    print(f"  Gap ID: {gap.gap_id}")
                    print(f"  Title: {gap.title}")
                    print(f"  Description: {gap.description}")
                    print(f"  Supporting Evidence: {gap.supporting_evidence_summary}")
                    print(f"  Keywords: {', '.join(gap.keywords)}")
                    print(f"  Potential Questions: {'; '.join(gap.potential_questions_to_explore)}")
                    print("---")
            except Exception as e:
                logger.error(f"Error in gap identification test: {e}", exc_info=True)

    except Exception as e:
        logger.error(f"Error in PhDAgent main_test: {e}", exc_info=True)


if __name__ == "__main__":
    import asyncio
    # To run the main_test, you'd need to have pydantic-ai and an LLM provider configured
    # (e.g., set GOOGLE_API_KEY in your environment if using Gemini)
    # Ensure that self.dependencies.chromadb_service.search_collection is an async method if you uncomment its direct calls.
    asyncio.run(main_test())
    print("PhDAgent class structure updated with literature analysis agent and logic.") 