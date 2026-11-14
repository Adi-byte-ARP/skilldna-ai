"""More skills, added so certificates, resumes and new roles can be matched.

Same shape as SKILLS_TAXONOMY. Aliases are only added when they are unambiguous in
prose (no two-letter words), because a false match here inflates someone's score.
"""

EXTRA_SKILLS = {
    # AI and data
    "generative ai": {"category": "Data/ML", "aliases": ["gen ai", "genai", "generative artificial intelligence"]},
    "prompt engineering": {"category": "Data/ML", "aliases": ["prompt design", "prompting"]},
    "large language models": {"category": "Data/ML", "aliases": ["llm", "llms", "large language model"]},
    "langchain": {"category": "Data/ML", "aliases": []},
    "hugging face": {"category": "Data/ML", "aliases": ["huggingface", "transformers library"]},
    "artificial intelligence": {"category": "Data/ML", "aliases": ["ai fundamentals", "introduction to ai"]},
    "keras": {"category": "Data/ML", "aliases": []},
    "opencv": {"category": "Data/ML", "aliases": ["open cv"]},
    "statistics": {"category": "Data/ML", "aliases": ["statistical analysis", "probability and statistics"]},
    "data visualization": {"category": "Data/ML", "aliases": ["data visualisation", "visualization"]},
    "power bi": {"category": "Data/ML", "aliases": ["powerbi"]},
    "tableau": {"category": "Data/ML", "aliases": []},
    "excel": {"category": "Data/ML", "aliases": ["microsoft excel", "ms excel"]},
    "apache spark": {"category": "Data/ML", "aliases": ["spark", "pyspark"]},
    "hadoop": {"category": "Data/ML", "aliases": []},
    "kafka": {"category": "Data/ML", "aliases": ["apache kafka"]},
    "snowflake": {"category": "Data/ML", "aliases": []},
    "bigquery": {"category": "Data/ML", "aliases": ["big query"]},
    "google analytics": {"category": "Data/ML", "aliases": []},
    # security
    "cybersecurity": {"category": "Security", "aliases": ["cyber security", "information security", "infosec"]},
    "ethical hacking": {"category": "Security", "aliases": ["penetration testing", "pentesting"]},
    "network security": {"category": "Security", "aliases": ["network security fundamentals"]},
    "cryptography": {"category": "Security", "aliases": []},
    # cloud and devops
    "terraform": {"category": "Cloud/DevOps", "aliases": []},
    "ansible": {"category": "Cloud/DevOps", "aliases": []},
    "jenkins": {"category": "Cloud/DevOps", "aliases": []},
    "cloud computing": {"category": "Cloud/DevOps", "aliases": ["cloud fundamentals", "cloud architecture"]},
    "microservices": {"category": "Cloud/DevOps", "aliases": ["microservice architecture"]},
    "networking": {"category": "Cloud/DevOps", "aliases": ["computer networks", "tcp/ip"]},
    # web and apis
    "html": {"category": "Framework", "aliases": ["html5"]},
    "css": {"category": "Framework", "aliases": ["css3"]},
    "tailwind css": {"category": "Framework", "aliases": ["tailwind", "tailwindcss"]},
    "bootstrap": {"category": "Framework", "aliases": []},
    "next.js": {"category": "Framework", "aliases": ["nextjs", "next js"]},
    "graphql": {"category": "Framework", "aliases": []},
    "rest api": {"category": "Framework", "aliases": ["rest apis", "restful api", "restful apis", "rest"]},
    "flutter": {"category": "Framework", "aliases": []},
    "react native": {"category": "Framework", "aliases": ["reactnative"]},
    "android": {"category": "Framework", "aliases": ["android development", "android studio"]},
    "dart": {"category": "Programming Language", "aliases": []},
    "php": {"category": "Programming Language", "aliases": []},
    # testing and product
    "selenium": {"category": "Testing", "aliases": []},
    "postman": {"category": "Testing", "aliases": []},
    "test automation": {"category": "Testing", "aliases": ["automation testing", "automated testing"]},
    "unit testing": {"category": "Testing", "aliases": ["unit tests"]},
    "jira": {"category": "Project & Product", "aliases": []},
    "agile": {"category": "Project & Product", "aliases": ["agile methodology"]},
    "scrum": {"category": "Project & Product", "aliases": ["scrum master"]},
    "product management": {"category": "Project & Product", "aliases": ["product manager"]},
    "business analysis": {"category": "Project & Product", "aliases": ["business analyst", "requirements analysis"]},
    "technical writing": {"category": "Soft Skill", "aliases": ["documentation writing"]},
    "time management": {"category": "Soft Skill", "aliases": []},
    "critical thinking": {"category": "Soft Skill", "aliases": []},
    # design
    "figma": {"category": "Design", "aliases": []},
    "ui/ux design": {"category": "Design", "aliases": ["ui design", "ux design", "user experience design", "ui/ux"]},
    "user research": {"category": "Design", "aliases": []},
    # other
    "blockchain": {"category": "Emerging", "aliases": []},
    "iot": {"category": "Emerging", "aliases": ["internet of things"]},
    "data structures": {"category": "Computer Science", "aliases": ["data structures and algorithms", "dsa"]},
    "algorithms": {"category": "Computer Science", "aliases": ["algorithm design"]},
    "operating systems": {"category": "Computer Science", "aliases": []},
    "digital marketing": {"category": "Marketing", "aliases": []},
    "seo": {"category": "Marketing", "aliases": ["search engine optimization"]},
}
