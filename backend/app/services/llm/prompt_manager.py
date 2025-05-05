"""
Prompt Manager

Provides functionality to load, manage, and format prompts for LLM interaction.
"""

import string
from typing import Dict, Any

class PromptTemplate:
    """Represents a single prompt template."""
    def __init__(self, template_string: str):
        # Basic validation to ensure it's a valid template string
        try:
            self.template = string.Template(template_string)
        except ValueError as e:
            raise ValueError(f"Invalid template string provided: {e}")

    def format(self, **kwargs) -> str:
        """
        Formats the template using the provided keyword arguments.

        Args:
            **kwargs: Variables to substitute into the template.

        Returns:
            The formatted prompt string.
        
        Raises:
            KeyError: If a placeholder in the template is missing from kwargs.
        """
        try:
            return self.template.substitute(**kwargs)
        except KeyError as e:
            print(f"Missing variable '{e}' for prompt template.")
            # Re-raise or handle as appropriate (e.g., return partially formatted string?)
            raise
        except TypeError as e:
            # Catches issues like trying to substitute non-string values if template isn't prepared for it
            print(f"Type error during template formatting: {e}")
            raise

class PromptManager:
    """
    Manages a collection of prompt templates.
    
    For now, templates are added directly. Future versions could load from files (YAML, JSON).
    """
    def __init__(self):
        self._templates: Dict[str, PromptTemplate] = {}

    def add_template(self, name: str, template_string: str):
        """
        Adds a new prompt template to the manager.

        Args:
            name: A unique name to identify the template.
            template_string: The prompt template string (using $variable syntax).
        
        Raises:
            ValueError: If the template name already exists or the template string is invalid.
        """
        if name in self._templates:
            raise ValueError(f"Template '{name}' already exists.")
        try:
            self._templates[name] = PromptTemplate(template_string)
            print(f"Prompt template '{name}' added successfully.")
        except ValueError as e:
             # Propagate error from PromptTemplate constructor
             raise ValueError(f"Failed to add template '{name}': {e}")

    def get_template(self, name: str) -> PromptTemplate:
        """
        Retrieves a specific prompt template by name.

        Args:
            name: The name of the template to retrieve.

        Returns:
            The PromptTemplate object.

        Raises:
            KeyError: If the template name does not exist.
        """
        if name not in self._templates:
            raise KeyError(f"Prompt template '{name}' not found.")
        return self._templates[name]

    def format_prompt(self, name: str, **kwargs) -> str:
        """
        Retrieves a template by name and formats it with the given variables.

        Args:
            name: The name of the template.
            **kwargs: Variables to substitute into the template.

        Returns:
            The formatted prompt string.
            
        Raises:
            KeyError: If the template name does not exist or formatting fails due to missing variables.
        """
        template = self.get_template(name) # Raises KeyError if not found
        return template.format(**kwargs) # Raises KeyError if variables missing

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