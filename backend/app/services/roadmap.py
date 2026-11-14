"""Detailed skill-gap roadmap.

For a target role, the plan lists every skill the role expects that the user
has not shown yet (missing) or has shown only weakly (weak). Each gap gets a
playbook entry: why it matters, objectives, weekly tasks, a project, resources
and a time estimate. Items are grouped into phases so the user has a timeline.

Resource links point only to official documentation home or tutorial pages.
Skills without a playbook entry get a generic plan built from the taxonomy resource.
"""
import re

from app.services.mock_content import ROLE_SKILLS
from app.services.learning import notes_for, videos_for_task
from app.utils.skills_taxonomy import SKILLS_TAXONOMY

WEAK_BELOW = 60  # a skill scored under this counts as a weak gap, not a missing one

PLAYBOOK = {
    "python": {
        "why": "Python is the most requested language for backend, data and automation roles.",
        "objectives": ["Write functions, classes and comprehensions without help",
                       "Use the standard library for files, JSON and dates",
                       "Write small tested modules"],
        "tasks": ["Work through the official tutorial, chapters 3 to 7",
                  "Solve 15 small exercises that read and write files",
                  "Write a script that cleans a CSV and prints a summary"],
        "project": "A command-line expense tracker that stores data in a JSON file.",
        "resources": [("Python official tutorial", "https://docs.python.org/3/tutorial/")],
        "hours": 30,
    },
    "sql": {
        "why": "Almost every data and backend role needs to read and change relational data.",
        "objectives": ["Write SELECT with WHERE, GROUP BY, HAVING and ORDER BY",
                       "Join two or three tables correctly",
                       "Explain what an index does and when it helps"],
        "tasks": ["Complete the SQL lessons on SQLBolt, all sections",
                  "Write 10 queries that answer business questions on a sample database",
                  "Use EXPLAIN on one slow query and describe the plan"],
        "project": "A sales report that answers five questions with SQL only.",
        "resources": [("SQLBolt interactive lessons", "https://sqlbolt.org")],
        "hours": 25,
    },
    "javascript": {
        "why": "JavaScript runs every browser and most of the server-side code you will read on a team.",
        "objectives": ["Explain closures, scope and the event loop",
                       "Use async/await and handle errors from fetch",
                       "Transform arrays with map, filter and reduce"],
        "tasks": ["Read the MDN guide sections on functions and promises",
                  "Rewrite one callback-based snippet with async/await",
                  "Build a small page that fetches JSON and renders a list"],
        "project": "A to-do list that saves items to localStorage and reloads them.",
        "resources": [("MDN JavaScript guide", "https://developer.mozilla.org/en-US/docs/Web/JavaScript")],
        "hours": 35,
    },
    "typescript": {
        "why": "TypeScript catches a large class of bugs before they reach users, and most teams use it.",
        "objectives": ["Type functions, objects and arrays",
                       "Use unions and optional fields",
                       "Type API responses from a real endpoint"],
        "tasks": ["Read the handbook chapters on basic types and interfaces",
                  "Convert a small JavaScript file to TypeScript without using any",
                  "Type the response of one API call you already use"],
        "project": "Convert one of your JavaScript projects to TypeScript.",
        "resources": [("TypeScript handbook", "https://www.typescriptlang.org/docs/handbook/intro.html")],
        "hours": 20,
    },
    "react": {
        "why": "React is the most common frontend library in job postings.",
        "objectives": ["Build components that take props and manage state",
                       "Use useEffect correctly, including its cleanup",
                       "Lift state and share it between components"],
        "tasks": ["Finish the official 'Learn React' tutorial",
                  "Build a form with validation and an error message",
                  "Fetch data in an effect and show loading and error states"],
        "project": "A movie search page that calls a public API and paginates results.",
        "resources": [("React learn guide", "https://react.dev/learn")],
        "hours": 40,
    },
    "node.js": {
        "why": "Node.js lets you use JavaScript for APIs, which many full-stack roles require.",
        "objectives": ["Create an HTTP server and routes",
                       "Read environment variables and config safely",
                       "Handle errors in async code"],
        "tasks": ["Work through the Node.js 'Learn' guides on modules and HTTP",
                  "Build a REST API with three endpoints and input checks",
                  "Add structured error responses to every route"],
        "project": "A notes API with create, list, update and delete endpoints.",
        "resources": [("Node.js learn guides", "https://nodejs.org/en/learn")],
        "hours": 30,
    },
    "fastapi": {
        "why": "FastAPI is a fast, well-documented Python framework used for many new APIs.",
        "objectives": ["Define routes with request and response models",
                       "Add authentication with a dependency",
                       "Write tests with the built-in test client"],
        "tasks": ["Complete the FastAPI tutorial through path operations and dependencies",
                  "Add a POST endpoint with validation errors you can explain",
                  "Write three tests for one endpoint"],
        "project": "A book library API with authentication and a search endpoint.",
        "resources": [("FastAPI tutorial", "https://fastapi.tiangolo.com/tutorial/")],
        "hours": 25,
    },
    "html": {
        "why": "Semantic HTML is the base of accessible, searchable pages.",
        "objectives": ["Use semantic elements such as main, nav and section",
                       "Build a form with labels and validation attributes",
                       "Explain the difference between a div and a semantic element"],
        "tasks": ["Work through the MDN 'Learn web development' HTML module",
                  "Rebuild one page using only semantic elements",
                  "Check the page with a keyboard only"],
        "project": "A personal portfolio page with an accessible contact form.",
        "resources": [("MDN learn web development", "https://developer.mozilla.org/en-US/docs/Learn_web_development")],
        "hours": 12,
    },
    "css": {
        "why": "Layout skill decides whether an interface works on phones as well as desktops.",
        "objectives": ["Lay out a page with flexbox and grid",
                       "Make a layout responsive with media queries",
                       "Explain the box model in your own words"],
        "tasks": ["Complete the MDN CSS layout lessons (flexbox and grid)",
                  "Recreate one reference page at phone and desktop widths",
                  "Fix three layout bugs in a deliberately broken page"],
        "project": "A responsive product grid that works from 360 px to 1440 px wide.",
        "resources": [("MDN learn web development", "https://developer.mozilla.org/en-US/docs/Learn_web_development")],
        "hours": 15,
    },
    "git": {
        "why": "Every team uses Git. Clean history and clear branches make you easy to work with.",
        "objectives": ["Create branches, commit and merge without fear",
                       "Resolve a merge conflict",
                       "Write commit messages that explain why"],
        "tasks": ["Read chapters 1 to 3 of the Pro Git book",
                  "Create a repo, make three branches and merge them",
                  "Deliberately cause a conflict and resolve it"],
        "project": "Contribute a small fix to an open-source repository.",
        "resources": [("Pro Git book", "https://git-scm.com/book/en/v2")],
        "hours": 10,
    },
    "github": {
        "why": "Pull requests and issues are how most teams review and track work.",
        "objectives": ["Open a pull request with a clear description",
                       "Review someone else's pull request",
                       "Use issues and labels to track a small project"],
        "tasks": ["Complete the GitHub Skills courses on pull requests",
                  "Open a pull request on one of your repos and review it yourself",
                  "Set up a project board with three columns"],
        "project": "A public repo with a README, issues and a tagged release.",
        "resources": [("GitHub documentation", "https://docs.github.com")],
        "hours": 8,
    },
    "docker": {
        "why": "Containers make an app run the same on your laptop, in tests and in production.",
        "objectives": ["Write a Dockerfile for an app you built",
                       "Run two containers together with compose",
                       "Explain images versus containers"],
        "tasks": ["Complete the Docker 'Get started' guide",
                  "Containerize one of your projects and run it locally",
                  "Add a compose file that starts the app and its database"],
        "project": "Containerize your FastAPI or Node project with a database container.",
        "resources": [("Docker get started", "https://docs.docker.com/get-started/")],
        "hours": 15,
    },
    "ci/cd": {
        "why": "Automated tests and deployments are expected on most engineering teams.",
        "objectives": ["Write a workflow that runs tests on every push",
                       "Add a build step that fails the pipeline on error",
                       "Explain the difference between continuous integration and delivery"],
        "tasks": ["Read the GitHub Actions quickstart",
                  "Add a workflow that installs dependencies and runs your tests",
                  "Break a test on purpose and watch the pipeline fail"],
        "project": "Add a CI workflow with tests and a lint step to one of your repos.",
        "resources": [("GitHub Actions documentation", "https://docs.github.com/en/actions")],
        "hours": 12,
    },
    "aws": {
        "why": "Cloud skills are required for most deployment and data roles.",
        "objectives": ["Explain what EC2, S3 and IAM are for",
                       "Deploy a small app on a virtual server or container service",
                       "Set least-privilege permissions for a role"],
        "tasks": ["Complete the AWS Cloud Practitioner Essentials course (free)",
                  "Store one file in S3 and make it private by default",
                  "Deploy one app and write down each step"],
        "project": "Host a static site on S3 and serve it through CloudFront.",
        "resources": [("AWS training", "https://aws.amazon.com/training/")],
        "hours": 25,
    },
    "postgresql": {
        "why": "PostgreSQL is a reliable default database for production applications.",
        "objectives": ["Create tables with keys and constraints",
                       "Write transactions that commit or roll back together",
                       "Create an index and explain when it is used"],
        "tasks": ["Work through the official PostgreSQL tutorial",
                  "Design a schema for one of your projects with foreign keys",
                  "Run EXPLAIN ANALYZE before and after adding an index"],
        "project": "Move one of your data projects from SQLite to PostgreSQL.",
        "resources": [("PostgreSQL tutorial", "https://www.postgresql.org/docs/current/tutorial.html")],
        "hours": 20,
    },
    "machine learning": {
        "why": "Model building and evaluation are the core of ML engineering roles.",
        "objectives": ["Split data and explain why",
                       "Train and evaluate a baseline model",
                       "Recognise overfitting from train and test scores"],
        "tasks": ["Work through the first three weeks of an introductory ML course",
                  "Train a logistic regression on a public dataset and report metrics",
                  "Write a one-page note on what the model got wrong"],
        "project": "Predict a public dataset outcome and document the error analysis.",
        "resources": [("Kaggle Learn", "https://www.kaggle.com/learn"),
                      ("scikit-learn user guide", "https://scikit-learn.org/stable/user_guide.html")],
        "hours": 45,
    },
    "pandas": {
        "why": "Pandas is the standard tool for cleaning and exploring tabular data.",
        "objectives": ["Load, filter and group a DataFrame",
                       "Handle missing values deliberately",
                       "Merge two tables on a key"],
        "tasks": ["Work through the pandas 10-minute guide",
                  "Clean one messy public CSV and document each change",
                  "Answer three questions about it with groupby"],
        "project": "A cleaning notebook that turns a raw CSV into a summary table.",
        "resources": [("pandas 10 minutes guide", "https://pandas.pydata.org/docs/user_guide/10min.html")],
        "hours": 15,
    },
    "numpy": {
        "why": "NumPy arrays are the foundation of most numerical Python code.",
        "objectives": ["Create arrays and explain their shape",
                       "Use vectorized operations instead of loops",
                       "Index and slice arrays confidently"],
        "tasks": ["Work through the NumPy quickstart",
                  "Rewrite one loop as a vectorized expression",
                  "Compute summary statistics on a 2D array"],
        "project": "Implement a moving average and a normalisation with NumPy only.",
        "resources": [("NumPy quickstart", "https://numpy.org/doc/stable/user/quickstart.html")],
        "hours": 10,
    },
    "data analysis": {
        "why": "Turning data into a clear finding is most of the work in analytics roles.",
        "objectives": ["Frame a question before analysing",
                       "Choose a chart that matches the question",
                       "Write a short written conclusion with numbers"],
        "tasks": ["Complete the Kaggle Learn data analysis course",
                  "Answer one business question on a public dataset",
                  "Present the result in a half-page write-up"],
        "project": "A written analysis of a public dataset with three charts and a conclusion.",
        "resources": [("Kaggle Learn", "https://www.kaggle.com/learn")],
        "hours": 20,
    },
    "redis": {
        "why": "Redis is used for caching and fast counters in many production systems.",
        "objectives": ["Store and expire keys with a TTL",
                       "Explain when caching helps and when it creates stale data",
                       "Use a Redis data structure beyond plain strings"],
        "tasks": ["Read the Redis 'Get started' guide",
                  "Add a cache with an expiry to one slow endpoint",
                  "Write down what happens on a cache miss"],
        "project": "Cache the results of one slow API route and measure the difference.",
        "resources": [("Redis documentation", "https://redis.io/docs/latest/")],
        "hours": 10,
    },
}

WEEKLY_HOURS = 20  # a realistic study pace alongside a degree or a job
PHASE_LABELS = ["Foundations", "Build", "Apply", "Deepen", "Specialise", "Consolidate"]
HOURS_PER_PHASE = 2 * WEEKLY_HOURS  # each learning phase is about two weeks of study
PROVE_WEEKS = 2


def _display_names() -> dict[str, str]:
    """lowercase skill -> the name a person expects to see (e.g. 'node.js' -> 'Node.js')."""
    names = {}
    for role_skills in ROLE_SKILLS.values():
        for skill in role_skills:
            names.setdefault(skill.lower(), skill)
    return names


def _pretty(skill: str) -> str:
    return _display_names().get(skill.lower(), skill)


def _slug(skill: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", skill.lower()).strip("-")


def _as_pair(item) -> tuple[str, float]:
    """Accept either a dict or an ORM SkillScore row (build_report returns rows)."""
    if isinstance(item, dict):
        return item["skill_name"], float(item["score"])
    return item.skill_name, float(item.score)


def _gaps_for_role(role: str, all_scores: list) -> list[dict]:
    """Role skills the user lacks (missing) or scores weakly on (weak), in role order."""
    by_name = {}
    for item in all_scores:
        name, score = _as_pair(item)
        by_name[name.lower()] = score
    gaps = []
    for skill in ROLE_SKILLS.get(role, []):
        key = skill.lower()
        if key not in by_name:
            gaps.append({"skill": skill, "status": "missing", "current_score": None})
        elif by_name[key] < WEAK_BELOW:
            gaps.append({"skill": skill, "status": "weak", "current_score": round(by_name[key], 1)})
    # missing skills first, then weak ones; stable within each group
    gaps.sort(key=lambda g: 0 if g["status"] == "missing" else 1)
    return gaps


def _generic_playbook(skill: str, taxonomy_resource: str | None) -> dict:
    return {
        "why": f"{skill} appears in the requirements for this role.",
        "objectives": [f"Explain the core ideas of {skill} in your own words",
                       f"Complete one small exercise in {skill}",
                       f"Apply {skill} in a small project"],
        "tasks": [f"Study the official documentation for {skill}",
                  f"Do a short course or tutorial on {skill}",
                  f"Build one small thing that uses {skill}"],
        "project": f"A small project that uses {skill} and a README explaining your decisions.",
        "resources": [("Starting point", taxonomy_resource or "https://developer.mozilla.org/en-US/docs/Learn_web_development")],
        "hours": 15,
    }


def build_plan(role: str, all_scores: list, overall_score: float, tier: str,
               done_keys: set[str], taxonomy_resources: dict[str, str] | None = None,
               baselines: dict[str, float] | None = None,
               daily_stats: dict[str, dict] | None = None) -> dict:
    taxonomy_resources = taxonomy_resources or {}
    baselines = baselines or {}
    daily_stats = daily_stats or {}
    current_by_name = {_as_pair(item)[0].lower(): _as_pair(item)[1] for item in all_scores}
    gaps = _gaps_for_role(role, all_scores)
    pairs = [_as_pair(item) for item in all_scores]
    strengths = [_pretty(name) for name, _ in sorted(pairs, key=lambda p: -p[1])[:5]]

    items = []
    phase_index = 0          # phases are numbered 0, 1, 2... with no gaps
    hours_in_phase = 0
    items_in_phase = 0
    for gap in gaps:
        book = PLAYBOOK.get(gap["skill"].lower()) or _generic_playbook(
            gap["skill"], taxonomy_resources.get(gap["skill"].lower()))
        slug = _slug(gap["skill"])
        category = SKILLS_TAXONOMY.get(gap["skill"].lower(), {}).get("category")
        tasks = [
            {
                "key": f"{slug}:task{i}",
                "text": text,
                "done": f"{slug}:task{i}" in done_keys,
                "videos": videos_for_task(_pretty(gap["skill"]), text),
            }
            for i, text in enumerate(book["tasks"])
        ]
        # A phase is about two weeks of study. Move to the next phase once this one is full,
        # but never leave a phase empty (one long skill fills one phase, not two).
        if items_in_phase and hours_in_phase >= HOURS_PER_PHASE:
            phase_index += 1
            hours_in_phase = 0
            items_in_phase = 0
        hours_in_phase += book["hours"]
        items_in_phase += 1
        items.append({
            "key": slug,
            "skill": _pretty(gap["skill"]),
            "status": gap["status"],
            "current_score": gap["current_score"],
            "why": book["why"],
            "objectives": book["objectives"],
            "tasks": tasks,
            "notes": notes_for(_pretty(gap["skill"]), category),
            "project": book["project"],
            "resources": [{"name": n, "url": u} for n, u in book["resources"]],
            "hours_estimate": book["hours"],
            "check": f"Pass at least 4 of 5 daily challenges that cover {_pretty(gap['skill'])}.",
            "progress": _skill_progress(gap["skill"], tasks, baselines, current_by_name, daily_stats),
            "phase_index": phase_index,
        })

    phases = _build_phases(items)

    # The ranked list the user sees first: which skills need work, why, and the next thing to do.
    improve = []
    for item in items:
        open_tasks = [t for t in item["tasks"] if not t["done"]]
        if item["status"] == "missing":
            priority, reason = "High", f"Not shown yet. {item['why']}"
        elif item["current_score"] is not None and item["current_score"] < 40:
            priority, reason = "High", f"Shown at {item['current_score']:.0f}/100, below 40. {item['why']}"
        else:
            priority, reason = "Medium", f"Shown at {item['current_score']:.0f}/100, so it needs more evidence. {item['why']}"
        improve.append({
            "key": item["key"],
            "skill": item["skill"],
            "status": item["status"],
            "score": item["current_score"],
            "priority": priority,
            "reason": reason,
            "next_task": open_tasks[0]["text"] if open_tasks else None,
            "next_task_key": open_tasks[0]["key"] if open_tasks else None,
            "phase_index": item["phase_index"],
            "hours": item["hours_estimate"],
        })
    improve.sort(key=lambda x: (0 if x["priority"] == "High" else 1, x["score"] if x["score"] is not None else -1))

    total_tasks = sum(len(it["tasks"]) for it in items)
    done_count = sum(1 for it in items for t in it["tasks"] if t["done"])
    total_hours = sum(it["hours_estimate"] for it in items)

    return {
        "role": role,
        "overall_score": overall_score,
        "tier": tier,
        "summary": _summary(role, gaps, strengths, total_hours),
        "strengths_to_leverage": strengths,
        "gap_count": len(gaps),
        "total_hours_estimate": total_hours,
        "progress": {
            "done": done_count,
            "total": total_tasks,
            "percent": round(100 * done_count / total_tasks, 1) if total_tasks else 0.0,
        },
        "phases": phases,
        "items": items,
        "improve": improve,
        "no_gaps": not gaps,
    }


SCORE_HELP = ("Your score changes when new evidence is added: a certificate, a GitHub update, "
              "a LinkedIn skills screenshot, or a new resume. Finishing tasks builds the skill; "
              "the score follows once the new work is shown.")


def _skill_progress(skill: str, tasks: list[dict], baselines: dict, current_by_name: dict,
                    daily_stats: dict) -> dict:
    key = skill.lower()
    baseline = baselines.get(key)
    current = current_by_name.get(key)
    delta = None
    if baseline is not None:
        delta = round((current or 0.0) - baseline, 1)
    done = sum(1 for t in tasks if t["done"])
    daily = daily_stats.get(key, {"attempts": 0, "correct": 0})
    if delta is None:
        message = "Progress starts from your next plan view."
    elif delta > 0:
        message = f"Up {delta:g} points since you started this plan."
    elif done:
        message = "Tasks ticked, but the score has not moved yet. " + SCORE_HELP
    else:
        message = "No change yet. Tick tasks as you complete them."
    return {
        "baseline_score": baseline,
        "current_score": current,
        "score_change": delta,
        "tasks_done": done,
        "tasks_total": len(tasks),
        "daily_correct": daily["correct"],
        "daily_attempts": daily["attempts"],
        "message": message,
    }


def _build_phases(items: list[dict]) -> list[dict]:
    """Learning phases sized by hours, each with a week range, then a proof phase."""
    phases = []
    week = 1
    last_index = max((it["phase_index"] for it in items), default=-1)
    for index in range(last_index + 1):
        label = PHASE_LABELS[index] if index < len(PHASE_LABELS) else f"Stage {index + 1}"
        phase_items = [it for it in items if it["phase_index"] == index]
        hours = sum(it["hours_estimate"] for it in phase_items)
        weeks = max(1, -(-hours // WEEKLY_HOURS))
        span = f"weeks {week}-{week + weeks - 1}" if weeks > 1 else f"week {week}"
        phases.append({
            "name": f"Phase {index + 1} · {label} ({span}, about {hours} hours)",
            "items": [it["key"] for it in phase_items],
            "goal": _phase_goal(index, phase_items),
        })
        week += weeks
    proof_index = last_index + 2
    proof_span = f"weeks {week}-{week + PROVE_WEEKS - 1}"
    phases.append({
        "name": f"Phase {proof_index} · Prove it ({proof_span})",
        "items": [],
        "goal": ("Take one mock test and one mock interview for this role, "
                 "and keep a daily challenge streak of at least 5 days."),
    })
    return phases


def _phase_goal(index: int, items: list[dict]) -> str:
    if not items:
        return "No skills to build in this phase."
    names = ", ".join(it["skill"] for it in items)
    return f"Work through {names}. Finish each task list before moving on."


def _summary(role: str, gaps: list[dict], strengths: list[str], hours: int) -> str:
    if not gaps:
        return f"Your profile already covers every skill listed for {role}. Focus on proof: projects and mock interviews."
    missing = [g["skill"] for g in gaps if g["status"] == "missing"]
    weak = [g["skill"] for g in gaps if g["status"] == "weak"]
    parts = [f"For {role}, you have {len(gaps)} gaps (about {hours} hours of study)."]
    if missing:
        parts.append("Not shown yet: " + ", ".join(missing) + ".")
    if weak:
        parts.append("Shown but weak: " + ", ".join(weak) + ".")
    if strengths:
        parts.append("Lean on your strongest areas: " + ", ".join(strengths[:3]) + ".")
    return " ".join(parts)
