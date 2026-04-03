"""SOUL Personality System - Template loader and variable substitution."""

import os
import re
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class SoulLoader:
    """Loads and manages SOUL personality templates."""

    def __init__(self, template_dir: str = None):
        """Initialize SOUL loader.

        Args:
            template_dir: Directory containing SOUL templates
        """
        if template_dir is None:
            base_dir = Path(__file__).parent
            template_dir = base_dir / "templates"
        
        self.template_dir = Path(template_dir)
        self._cache: Dict[str, str] = {}
        self._debate_styles: Dict[str, Dict] = {}
        
    def load_template(self, role: str) -> str:
        """Load personality template for a role.

        Args:
            role: Agent role (manager, developer, designer, researcher)

        Returns:
            Template content
        """
        if role in self._cache:
            return self._cache[role]
        
        template_file = self.template_dir / f"{role}.md"
        
        if not template_file.exists():
            logger.warning(f"Template not found: {template_file}")
            return ""
        
        try:
            content = template_file.read_text(encoding="utf-8")
            self._cache[role] = content
            return content
        except Exception as e:
            logger.error(f"Error loading template {role}: {e}")
            return ""

    def apply_variables(
        self,
        template: str,
        variables: Optional[Dict[str, str]] = None,
    ) -> str:
        """Apply variables to template.

        Args:
            template: Template content
            variables: Dict of variable names to values

        Returns:
            Template with variables substituted
        """
        if not variables:
            variables = {}
        
        result = template
        
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            result = result.replace(placeholder, value)
        
        remaining = re.findall(r"\{\{(\w+)\}\}", result)
        if remaining:
            for var in remaining:
                placeholder = "{{" + var + "}}"
                result = result.replace(placeholder, "")
        
        return result

    def load_debate_style(self, style_name: str) -> Dict:
        """Load debate style guidelines.

        Args:
            style_name: Style name (assertive, diplomatic, analytical)

        Returns:
            Dict with style guidelines
        """
        if style_name in self._debate_styles:
            return self._debate_styles[style_name]
        
        base_dir = Path(__file__).parent
        style_file = base_dir / "debate_styles" / f"{style_name}.md"
        
        if not style_file.exists():
            logger.warning(f"Debate style not found: {style_name}")
            return {"guidelines": []}
        
        try:
            content = style_file.read_text(encoding="utf-8")
            lines = content.strip().split("\n")
            guidelines = []
            
            for line in lines:
                line = line.strip()
                if line.startswith("-"):
                    guidelines.append(line[1:].strip())
            
            style_data = {"description": style_name, "guidelines": guidelines}
            self._debate_styles[style_name] = style_data
            return style_data
        except Exception as e:
            logger.error(f"Error loading debate style {style_name}: {e}")
            return {"guidelines": []}

    def get_personalized_prompt(
        self,
        role: str,
        shared_memory: str = "",
        debate_style: str = "diplomatic",
    ) -> str:
        """Get personalized system prompt.

        Args:
            role: Agent role
            shared_memory: Shared memory content
            debate_style: Debate style to apply

        Returns:
            Personalized system prompt
        """
        template = self.load_template(role)
        
        variables = {
            "SHARED_MEMORY": shared_memory or "No shared memory available",
        }
        
        prompt = self.apply_variables(template, variables)
        
        if debate_style:
            style_data = self.load_debate_style(debate_style)
            guidelines = style_data.get("guidelines", [])
            if guidelines:
                guidelines_text = "\n".join([f"- {g}" for g in guidelines])
                prompt += f"\n\n## 토론 가이드라인\n{guidelines_text}"
        
        return prompt

    def clear_cache(self):
        """Clear template cache."""
        self._cache.clear()
        self._debate_styles.clear()


_soul_loader: Optional[SoulLoader] = None


def get_soul_loader() -> SoulLoader:
    """Get singleton SOUL loader instance."""
    global _soul_loader
    if _soul_loader is None:
        _soul_loader = SoulLoader()
    return _soul_loader