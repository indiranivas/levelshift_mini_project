import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Pattern, Set, Tuple

from .preprocessing import normalize_text_preserve_tech, extract_section


def _alias_to_regex(alias: str) -> str:
    """
    Convert an alias phrase into a regex that allows flexible separators
    between tokens (space / hyphen / underscore / slash).
    """
    alias = alias.strip().lower()
    if not alias:
        return ""

    parts = re.split(r"\s+", alias)
    if len(parts) == 1:
        return re.escape(alias)

    sep = r"[\s\-/\_]+"
    return sep.join(re.escape(p) for p in parts)


def _compile_skill_pattern(alias: str) -> Pattern:
    alias_re = _alias_to_regex(alias)
    # Avoid matching inside larger word tokens.
    # Keep it simple + deterministic; tech symbols like '+'/'#'/'.' are preserved.
    return re.compile(rf"(?<![a-z0-9_]){alias_re}(?![a-z0-9_])", re.IGNORECASE)


# Canonical skill -> aliases / variants found in resumes + job descriptions.
DEFAULT_SKILL_ALIASES: Dict[str, List[str]] = {
    # Languages
    "python": ["python", "py"],
    "java": ["java"],
    "javascript": ["javascript", "js"],
    "typescript": ["typescript", "ts"],
    "c++": ["c++", "cpp"],
    "c#": ["c#", "c sharp", "csharp"],
    ".net": [".net", "dotnet", "asp.net", "asp.net core", ".net core", ".net framework"],
    "sql": ["sql"],
    "postgresql": ["postgresql", "postgres", "psql"],
    "mongodb": ["mongodb", "mongo"],
    # ML / AI
    "machine learning": ["machine learning", "ml", "ml/ai"],
    "deep learning": ["deep learning"],
    "tensorflow": ["tensorflow"],
    "pytorch": ["pytorch", "torch"],
    # Frameworks
    "flask": ["flask"],
    "fastapi": ["fastapi"],
    "django": ["django"],
    "react": ["react", "reactjs", "react.js"],
    "node.js": ["node.js", "nodejs", "node"],
    # Data / libraries
    "pandas": ["pandas"],
    "numpy": ["numpy"],
    "scikit-learn": ["scikit-learn", "scikit learn", "sklearn"],
    # DevOps / cloud
    "aws": ["aws", "amazon web services"],
    "azure": ["azure", "microsoft azure"],
    "gcp": ["gcp", "google cloud"],
    "docker": ["docker"],
    "kubernetes": ["kubernetes", "k8s"],
    # Productivity
    "git": ["git", "github"],
    # Security / infra
    "rest api": ["rest api", "restful api", "restful"],
}


@dataclass(frozen=True)
class CanonicalSkill:
    name: str
    pattern: Pattern


class SkillExtractor:
    def __init__(self, skill_aliases: Optional[Dict[str, List[str]]] = None):
        aliases = skill_aliases or DEFAULT_SKILL_ALIASES

        compiled: List[CanonicalSkill] = []
        for canonical, alias_list in aliases.items():
            canonical_norm = canonical.strip().lower()
            if not canonical_norm:
                continue

            for alias in alias_list:
                alias_norm = alias.strip().lower()
                if not alias_norm:
                    continue
                compiled.append(
                    CanonicalSkill(name=canonical_norm, pattern=_compile_skill_pattern(alias_norm))
                )

        self._compiled = compiled

    def extract_skills(self, text: Optional[str]) -> List[str]:
        if text is None:
            return []

        # Section-aware extraction: prefer Skills section when it exists.
        skills_section = extract_section(
            str(text),
            headers=[
                "Skills",
                "Technical Skills",
                "Core Skills",
                "TECHNICAL SKILLS",
                "TOOLS",
                "Technologies",
            ],
        )
        source_text = skills_section if skills_section.strip() else str(text)

        norm = normalize_text_preserve_tech(source_text)
        if not norm:
            return []

        found: Set[str] = set()
        for item in self._compiled:
            if item.pattern.search(norm):
                found.add(item.name)

        return sorted(found)

