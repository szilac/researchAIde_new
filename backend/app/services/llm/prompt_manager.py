"""
Prompt Manager

Provides functionality to load, manage, and format prompts for LLM interaction using Jinja2.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional

import jinja2

logger = logging.getLogger(__name__)

class PromptManager:
    """
    Manages a collection of Jinja2 prompt templates.
    Loads templates from a specified directory.
    """
    def __init__(self, template_dir: Optional[str] = None):
        """
        Initializes the PromptManager.

        Args:
            template_dir: Optional path to the directory containing .j2 template files.
                          If provided, templates will be loaded automatically.
        """
        self._templates: Dict[str, jinja2.Template] = {}
        self.template_env = jinja2.Environment(loader=jinja2.FileSystemLoader('./'), # Base loader, directory changes in load method
                                               autoescape=False, # Disable autoescaping for LLM prompts
                                               trim_blocks=True, 
                                               lstrip_blocks=True)
        
        if template_dir:
            self.load_templates_from_directory(template_dir)

    def _generate_template_name(self, file_path: Path, base_dir: Path) -> str:
        """Generates a structured template name based on relative path.
           e.g., /path/to/templates/phd/query.j2 -> phd_query
        """
        relative_path = file_path.relative_to(base_dir)
        # Remove suffix and replace path separators with underscores
        name_parts = list(relative_path.parts[:-1]) + [relative_path.stem]
        return "_".join(name_parts).replace('-', '_')
        
    def load_templates_from_directory(self, directory_path: str):
        """
        Loads all Jinja2 templates (*.j2) from the specified directory and its subdirectories.
        Template names are generated based on their relative path and filename.
        
        Args:
            directory_path: The path to the directory containing templates.
        
        Raises:
            FileNotFoundError: If the directory_path does not exist.
            jinja2.TemplateSyntaxError: If a template file has syntax errors.
        """
        base_dir = Path(directory_path)
        if not base_dir.is_dir():
            raise FileNotFoundError(f"Template directory not found: {directory_path}")
            
        # Update the environment loader to the specified directory
        self.template_env.loader = jinja2.FileSystemLoader(str(base_dir))

        logger.info(f"Loading prompt templates from: {base_dir.resolve()}")
        
        template_files = list(base_dir.rglob('*.j2')) # Recursively find all .j2 files
        
        if not template_files:
            logger.warning(f"No *.j2 template files found in {directory_path}")
            return

        for file_path in template_files:
            relative_file_path = file_path.relative_to(base_dir)
            template_name = self._generate_template_name(file_path, base_dir)
            
            if template_name in self._templates:
                logger.warning(f"Template name conflict: '{template_name}' from {file_path} already loaded. Skipping.")
                continue
                
            try:
                # Use environment to load templates correctly respecting the loader path
                template = self.template_env.get_template(str(relative_file_path))
                self._templates[template_name] = template
                logger.debug(f"Loaded template '{template_name}' from {relative_file_path}")
            except jinja2.TemplateSyntaxError as e:
                logger.error(f"Syntax error in template {file_path}: {e}")
                # Decide whether to raise, or just log and continue
                # raise # Option: re-raise to halt loading on error
            except Exception as e:
                logger.error(f"Error loading template {file_path}: {e}")
                # raise # Option: re-raise
                
        logger.info(f"Finished loading templates. Total loaded: {len(self._templates)}")

    def get_template(self, name: str) -> jinja2.Template:
        """
        Retrieves a specific Jinja2 template by its generated name.

        Args:
            name: The generated name of the template (e.g., 'phd_query_formulation').

        Returns:
            The jinja2.Template object.

        Raises:
            KeyError: If the template name does not exist.
        """
        if name not in self._templates:
            raise KeyError(f"Prompt template '{name}' not found. Available: {list(self._templates.keys())}")
        return self._templates[name]

    def format_prompt(self, name: str, **kwargs) -> str:
        """
        Retrieves a template by name and renders it with the given variables.

        Args:
            name: The name of the template.
            **kwargs: Variables to substitute into the template.

        Returns:
            The rendered prompt string.
            
        Raises:
            KeyError: If the template name does not exist.
            jinja2.UndefinedError: If a variable in the template is not provided in kwargs.
        """
        template = self.get_template(name) # Raises KeyError if not found
        try:
            return template.render(**kwargs)
        except jinja2.UndefinedError as e:
            logger.error(f"Missing variable for template '{name}': {e}")
            raise # Re-raise the specific Jinja2 error
        except Exception as e:
            logger.error(f"Error rendering template '{name}': {e}")
            raise

# Example Usage:
# if __name__ == "__main__":
#     manager = PromptManager()

#     # Add some templates
#     manager.add_template(
#         "summarize", 
#         "Please summarize the following text: \n\n$text_to_summarize"
#     )
#     manager.add_template(
#         "qa",
#         "Context: \n$context\n\nQuestion: $question\n\nAnswer:"
#     )

#     # Format a prompt
#     try:
#         summary_prompt = manager.format_prompt("summarize", text_to_summarize="This is a long piece of text...")
#         print(f"Formatted Summarize Prompt:\n{summary_prompt}")

#         qa_prompt = manager.format_prompt(
#             "qa", 
#             context="The sky is blue due to Rayleigh scattering.", 
#             question="Why is the sky blue?"
#         )
#         print(f"\nFormatted QA Prompt:\n{qa_prompt}")
        
#         # Example of missing variable error
#         print("\nAttempting format with missing variable:")
#         manager.format_prompt("qa", context="Some context.") 
#     except KeyError as e:
#         print(f"Caught expected error: {e}")
#     except ValueError as e:
#         print(f"Caught template error: {e}") 