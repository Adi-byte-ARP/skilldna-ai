"""
Starter skills taxonomy.

This is intentionally a plain dict so it's trivial to extend — add new
skills/categories here, or later load this from the database/a JSON file/
an external taxonomy API (e.g. ESCO, LinkedIn Skills) without touching
the parsing logic. Keys are lowercase canonical skill names; values are
category + aliases (alternate spellings/phrasings that map to the same
canonical skill).
"""

SKILLS_TAXONOMY = {
    # Programming Languages
    "python": {"category": "Programming Language", "aliases": ["python3", "py"]},
    "java": {"category": "Programming Language", "aliases": []},
    "javascript": {"category": "Programming Language", "aliases": ["js", "es6"]},
    "typescript": {"category": "Programming Language", "aliases": ["ts"]},
    "c++": {"category": "Programming Language", "aliases": ["cpp"]},
    "c": {"category": "Programming Language", "aliases": []},
    "c#": {"category": "Programming Language", "aliases": ["csharp"]},
    "go": {"category": "Programming Language", "aliases": ["golang"]},
    "rust": {"category": "Programming Language", "aliases": []},
    "sql": {"category": "Programming Language", "aliases": []},
    "r": {"category": "Programming Language", "aliases": []},
    "kotlin": {"category": "Programming Language", "aliases": []},
    "swift": {"category": "Programming Language", "aliases": []},

    # Frameworks / Libraries
    "react": {"category": "Framework", "aliases": ["react.js", "reactjs"]},
    "node.js": {"category": "Framework", "aliases": ["nodejs", "node"]},
    "fastapi": {"category": "Framework", "aliases": []},
    "django": {"category": "Framework", "aliases": []},
    "flask": {"category": "Framework", "aliases": []},
    "spring boot": {"category": "Framework", "aliases": ["spring"]},
    "express": {"category": "Framework", "aliases": ["express.js"]},
    "angular": {"category": "Framework", "aliases": []},
    "vue": {"category": "Framework", "aliases": ["vue.js"]},
    "tensorflow": {"category": "Framework", "aliases": []},
    "pytorch": {"category": "Framework", "aliases": []},
    "pandas": {"category": "Framework", "aliases": []},
    "numpy": {"category": "Framework", "aliases": []},
    "scikit-learn": {"category": "Framework", "aliases": ["sklearn"]},

    # Databases
    "postgresql": {"category": "Database", "aliases": ["postgres"]},
    "mysql": {"category": "Database", "aliases": []},
    "mongodb": {"category": "Database", "aliases": ["mongo"]},
    "redis": {"category": "Database", "aliases": []},
    "supabase": {"category": "Database", "aliases": []},
    "sqlite": {"category": "Database", "aliases": []},

    # Cloud / DevOps
    "aws": {"category": "Cloud/DevOps", "aliases": ["amazon web services"]},
    "azure": {"category": "Cloud/DevOps", "aliases": []},
    "gcp": {"category": "Cloud/DevOps", "aliases": ["google cloud"]},
    "docker": {"category": "Cloud/DevOps", "aliases": []},
    "kubernetes": {"category": "Cloud/DevOps", "aliases": ["k8s"]},
    "ci/cd": {"category": "Cloud/DevOps", "aliases": ["cicd", "continuous integration"]},
    "git": {"category": "Cloud/DevOps", "aliases": ["github", "version control"]},
    "linux": {"category": "Cloud/DevOps", "aliases": []},

    # Data / ML
    "machine learning": {"category": "Data/ML", "aliases": ["ml"]},
    "deep learning": {"category": "Data/ML", "aliases": []},
    "data analysis": {"category": "Data/ML", "aliases": ["data analytics"]},
    "nlp": {"category": "Data/ML", "aliases": ["natural language processing"]},
    "computer vision": {"category": "Data/ML", "aliases": ["cv"]},

    # Soft skills
    "leadership": {"category": "Soft Skill", "aliases": []},
    "communication": {"category": "Soft Skill", "aliases": []},
    "teamwork": {"category": "Soft Skill", "aliases": ["collaboration"]},
    "problem solving": {"category": "Soft Skill", "aliases": ["problem-solving"]},
    "project management": {"category": "Soft Skill", "aliases": []},
}


def build_alias_lookup() -> dict[str, str]:
    """Map every alias (and the canonical name itself) -> canonical skill name."""
    lookup = {}
    for canonical, info in SKILLS_TAXONOMY.items():
        lookup[canonical] = canonical
        for alias in info["aliases"]:
            lookup[alias] = canonical
    return lookup


ALIAS_LOOKUP = build_alias_lookup()
