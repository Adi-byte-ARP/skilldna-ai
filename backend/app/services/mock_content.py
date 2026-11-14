"""Question banks for mock tests and mock interviews.

Answer keys live here, on the server. The API never returns `answer` or
`keywords` until a session is finished.

These banks are starter content: a few questions per skill and per role.
Add more entries freely; ids must stay unique because stored answers refer to them.
"""

MCQ_BANK = [
    {"id": "py-1", "skill": "python", "question": "What does `len([1, 2, 3])` return?",
     "options": ["2", "3", "4", "Error"], "answer": 1},
    {"id": "py-2", "skill": "python", "question": "Which keyword starts a generator function's yield-based pause?",
     "options": ["return", "yield", "pause", "await"], "answer": 1},
    {"id": "js-1", "skill": "javascript", "question": "What is the result of `typeof null`?",
     "options": ["'null'", "'object'", "'undefined'", "'number'"], "answer": 1},
    {"id": "js-2", "skill": "javascript", "question": "Which method returns a new array with transformed items?",
     "options": ["forEach", "map", "push", "splice"], "answer": 1},
    {"id": "react-1", "skill": "react", "question": "Which hook stores local state in a function component?",
     "options": ["useEffect", "useRef", "useState", "useMemo"], "answer": 2},
    {"id": "sql-1", "skill": "sql", "question": "Which clause filters rows after GROUP BY?",
     "options": ["WHERE", "HAVING", "ORDER BY", "LIMIT"], "answer": 1},
    {"id": "sql-2", "skill": "sql", "question": "Which JOIN keeps all rows from the left table even without a match?",
     "options": ["INNER JOIN", "LEFT JOIN", "CROSS JOIN", "SELF JOIN"], "answer": 1},
    {"id": "git-1", "skill": "git", "question": "Which command creates a new branch and switches to it?",
     "options": ["git branch -d", "git checkout -b", "git merge", "git fetch"], "answer": 1},
    {"id": "docker-1", "skill": "docker", "question": "What is a Docker image?",
     "options": ["A running container", "A read-only template for containers", "A virtual machine", "A volume"], "answer": 1},
    {"id": "fastapi-1", "skill": "fastapi", "question": "FastAPI uses which library to validate request bodies?",
     "options": ["marshmallow", "pydantic", "cerberus", "attrs"], "answer": 1},
    {"id": "ml-1", "skill": "machine learning", "question": "What does overfitting mean?",
     "options": ["Model performs well on new data", "Model memorizes training data and generalizes poorly",
                 "Model trains too quickly", "Model has too few parameters"], "answer": 1},
    {"id": "ml-2", "skill": "machine learning", "question": "Why split data into train and test sets?",
     "options": ["To make training faster", "To estimate performance on unseen data",
                 "To reduce the number of features", "To remove outliers"], "answer": 1},
]

# Interview questions per target role. `keywords` drive the coverage score;
# `seconds` is the per-question answer time.
INTERVIEW_BANK = {
    "Full-Stack Developer": [
        {"id": "fs-1", "question": "Walk me through what happens when a user submits a form in a web app you built.",
         "keywords": ["request", "api", "server", "database", "response", "validate", "route"], "seconds": 120},
        {"id": "fs-2", "question": "How do you keep frontend state and backend data consistent?",
         "keywords": ["state", "fetch", "cache", "refresh", "api", "error", "loading"], "seconds": 120},
        {"id": "fs-3", "question": "Describe how you would make a slow page load faster.",
         "keywords": ["measure", "bundle", "cache", "lazy", "image", "network", "profile"], "seconds": 120},
    ],
    "Data / ML Engineer": [
        {"id": "ml-q1", "question": "How would you check whether a model is overfitting?",
         "keywords": ["train", "validation", "test", "gap", "regularization", "cross"], "seconds": 120},
        {"id": "ml-q2", "question": "Walk me through cleaning a messy dataset before modelling.",
         "keywords": ["missing", "duplicate", "outlier", "type", "encode", "scale", "explore"], "seconds": 120},
        {"id": "ml-q3", "question": "How would you explain a model's result to a non-technical manager?",
         "keywords": ["simple", "example", "accuracy", "impact", "risk", "decision"], "seconds": 120},
    ],
    "Backend Engineer": [
        {"id": "be-1", "question": "How do you design an API endpoint that other teams will depend on?",
         "keywords": ["versioning", "validation", "error", "documentation", "contract", "status"], "seconds": 120},
        {"id": "be-2", "question": "How would you handle a database query that is slow in production?",
         "keywords": ["index", "explain", "query", "cache", "profile", "slow"], "seconds": 120},
        {"id": "be-3", "question": "What do you do when a deployment breaks production?",
         "keywords": ["rollback", "logs", "monitor", "incident", "root", "fix"], "seconds": 120},
    ],
}

GENERAL_INTERVIEW = [
    {"id": "gen-1", "question": "Tell me about a time you disagreed with a teammate. What happened?",
     "keywords": ["team", "disagree", "listen", "resolve", "outcome", "result"], "seconds": 120},
    {"id": "gen-2", "question": "Describe a project you are proud of and your exact contribution.",
     "keywords": ["built", "my", "role", "result", "problem", "impact"], "seconds": 120},
]

# Skills each target role is expected to show. Plans, mock tests and the AI interview all use this.
ROLE_SKILLS = {
    "Full-Stack Developer": ["JavaScript", "TypeScript", "React", "Node.js", "SQL", "Git",
                             "HTML", "CSS", "Docker", "PostgreSQL"],
    "Frontend Developer": ["JavaScript", "TypeScript", "React", "HTML", "CSS", "Tailwind CSS", "Git",
                           "UI/UX Design", "REST API"],
    "Backend Engineer": ["Python", "FastAPI", "Node.js", "SQL", "PostgreSQL", "Docker", "AWS",
                         "CI/CD", "Git", "Redis"],
    "Data / ML Engineer": ["Python", "Pandas", "NumPy", "Machine Learning", "Scikit-learn", "SQL",
                           "Data Analysis", "Deep Learning", "Docker", "AWS"],
    "Data Analyst": ["Python", "SQL", "Excel", "Power BI", "Tableau", "Statistics",
                     "Data Visualization", "Pandas", "Data Analysis", "Communication"],
    "DevOps Engineer": ["Linux", "Docker", "Kubernetes", "CI/CD", "Terraform", "AWS", "Git",
                        "Jenkins", "Ansible", "Networking"],
    "Cloud Engineer": ["AWS", "Azure", "GCP", "Cloud Computing", "Kubernetes", "Terraform", "Linux",
                       "Networking", "Docker", "Python"],
    "Mobile App Developer": ["Flutter", "Dart", "Android", "React Native", "Kotlin", "REST API", "Git",
                             "UI/UX Design", "Problem Solving"],
    "QA / Test Engineer": ["Selenium", "Test Automation", "Unit Testing", "Postman", "Python", "SQL",
                           "Jira", "Agile", "Git", "Problem Solving"],
    "Cybersecurity Analyst": ["Cybersecurity", "Network Security", "Ethical Hacking", "Linux", "Python",
                              "Networking", "Cryptography", "Problem Solving", "Critical Thinking"],
    "AI / Prompt Engineer": ["Python", "Generative AI", "Prompt Engineering", "Large Language Models",
                             "NLP", "Machine Learning", "LangChain", "Hugging Face", "Problem Solving",
                             "Communication"],
    "Product Manager": ["Product Management", "Agile", "Scrum", "Jira", "Data Analysis", "Communication",
                        "Leadership", "Problem Solving", "Business Analysis", "Project Management"],
    "Business Analyst": ["Business Analysis", "Excel", "SQL", "Power BI", "Communication", "Problem Solving",
                         "Agile", "Jira", "Statistics", "Technical Writing"],
    "UI/UX Designer": ["Figma", "UI/UX Design", "User Research", "HTML", "CSS", "Communication",
                       "Problem Solving", "Teamwork"],
}
