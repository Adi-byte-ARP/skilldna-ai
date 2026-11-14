"""Phase gating for the improve plan.

A learning phase opens when the phase before it is complete. A phase is complete when
every one of its tasks is ticked AND its phase test is passed. The first phase is always
open. The final "Prove it" phase opens when every learning phase is passed.

Statuses: locked | in_progress | test_ready | passed
"""


def _tasks_done(phase_items: list[dict]) -> tuple[int, int]:
    total = sum(len(it["tasks"]) for it in phase_items)
    done = sum(1 for it in phase_items for t in it["tasks"] if t["done"])
    return done, total


def apply_phase_gates(plan: dict, passed: dict[int, float], attempts: dict[int, int]) -> dict:
    """passed maps phase index -> best passing score. attempts maps phase index -> count."""
    learning = [i for i, ph in enumerate(plan["phases"]) if ph["items"]]
    previous_passed = True
    for index, phase in enumerate(plan["phases"]):
        items = [it for it in plan["items"] if it["key"] in phase["items"]]
        is_proof = not items
        done, total = _tasks_done(items)
        if is_proof:
            unlocked = all(i in passed for i in learning)
            complete = False
        else:
            unlocked = previous_passed
            complete = total > 0 and done == total
        test_passed = (not is_proof) and index in passed
        if not unlocked:
            status = "locked"
        elif is_proof:
            status = "in_progress" if unlocked else "locked"
        elif test_passed:
            status = "passed"
        elif complete:
            status = "test_ready"
        else:
            status = "in_progress"

        phase["status"] = status
        phase["unlocked"] = unlocked
        phase["tasks_done"] = done
        phase["tasks_total"] = total
        phase["test"] = {
            "available": (not is_proof) and unlocked and complete and not test_passed,
            "passed": test_passed,
            "best_score": passed.get(index),
            "attempts": attempts.get(index, 0),
            "pass_score": 60,
        }
        if not unlocked and not is_proof:
            phase["locked_reason"] = f"Finish Phase {_learning_number(plan, index - 1)} and pass its test to unlock this phase."
        for it in items:
            it["locked"] = not unlocked

        if not is_proof:
            previous_passed = test_passed

    plan["next_phase"] = next(
        (i for i, ph in enumerate(plan["phases"]) if ph.get("status") in ("test_ready", "in_progress", "locked")),
        None,
    )
    return plan


def _learning_number(plan: dict, index: int) -> int:
    """1-based number of a learning phase, as the user sees it in the title."""
    return index + 1


def phase_is_open_for_task(plan: dict, item_key: str) -> tuple[bool, str | None]:
    for item in plan["items"]:
        if item["key"] == item_key:
            if item.get("locked"):
                phase_index = item.get("phase_index", 0)
                return False, f"Phase {phase_index + 1} is locked. Finish the phase before it and pass its test."
            return True, None
    return False, "That skill is not part of this plan."
