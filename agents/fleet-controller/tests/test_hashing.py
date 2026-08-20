from models import Constraints, PlanRequest, RequestedAction, canonical_hash


def test_hash_stable_regardless_of_field_construction_order():
    # Two PlanRequest instances built from differently-ordered kwargs/dicts —
    # the claim is about pydantic-model equality producing equal hashes, not
    # about json.dumps(sort_keys=True) alone.
    a = PlanRequest(
        schema_version=1,
        mission_id="m1",
        requested_actions=[
            RequestedAction(action_id="a1", kind="compose_profile.preview", profile="agents")
        ],
        constraints=Constraints(allow_profiles=["agents"], deny_profiles=[]),
    )
    b = PlanRequest(
        constraints=Constraints(deny_profiles=[], allow_profiles=["agents"]),
        requested_actions=[
            RequestedAction(profile="agents", action_id="a1", kind="compose_profile.preview")
        ],
        mission_id="m1",
        schema_version=1,
    )
    assert canonical_hash(a) == canonical_hash(b)


def test_hash_changes_when_a_field_changes():
    plan = PlanRequest(
        schema_version=1,
        mission_id="m1",
        requested_actions=[
            RequestedAction(action_id="a1", kind="compose_profile.preview", profile="agents")
        ],
        constraints=Constraints(allow_profiles=["agents"]),
    )
    original = canonical_hash(plan)

    changed = plan.model_copy(deep=True)
    changed.requested_actions[0].profile = "hyper"
    assert canonical_hash(changed) != original


def test_hash_is_a_sha256_prefixed_string():
    plan = PlanRequest(
        schema_version=1,
        mission_id="m1",
        requested_actions=[RequestedAction(action_id="a1", kind="crew.workflow.preview")],
    )
    h = canonical_hash(plan)
    assert h.startswith("sha256:")
    assert len(h) == len("sha256:") + 64
