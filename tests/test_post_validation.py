"""The LinkedIn post, checked against new decisions and new physical scenes."""

import math

from validation.check_post import NEW_SCENES, POST_SCENES, run


def test_post_claims_hold_and_new_scenes_change_the_move():
    report = run()
    for scene in report["scenes"]:
        assert scene["ok"], scene
        assert scene["best"] == scene["expected"], scene
        if scene["expected_ev"] is not None:
            assert math.isclose(scene["ev"], scene["expected_ev"], abs_tol=1e-9)

    named = {scene["label"]: scene["best"] for scene in report["scenes"]}
    assert [named[label] for label, *_rest in POST_SCENES] == [
        "accelerate",
        "drain",
        "lookup",
        "run",
        "trust_trend",
    ]
    assert [named[label] for label, *_rest in NEW_SCENES] == [
        "steer",
        "share",
        "cool",
        "repeat_last",
        "finish",
    ]

    clinic = report["clinic"]
    assert clinic["recommended"] == "start_with_book"
    assert clinic["confidence"] == "high"
    assert clinic["epistemic_spread"]["agree_on_best"] is True
    assert clinic["flip_parameters"] == []
    assert clinic["models_used"] == 3
    by_action = {row["action"]: row for row in clinic["options"]}
    assert math.isclose(by_action["start_with_book"]["ev"], -22.0)
    assert math.isclose(by_action["rewrite_everything"]["ev"], -35.0)
    assert math.isclose(by_action["keep_old_desk"]["ev"], -36.5)
    assert math.isclose(by_action["start_with_book"]["p_events"]["missed_behavior"], 0.10)
    assert math.isclose(by_action["start_with_book"]["p_events"]["privacy_incident"], 0.05)

    warehouse = report["warehouse"]
    assert warehouse["recommended"] == "phased_move"
    assert warehouse["confidence"] == "low"
    assert warehouse["epistemic_spread"]["agree_on_best"] is True
    assert {item["param"] for item in warehouse["flip_parameters"]} == {"stockout_p"}
    assert {item["flips_at"] for item in warehouse["flip_parameters"]} == {"low"}
    assert {item["new_best"] for item in warehouse["flip_parameters"]} == {"weekend_move"}
    phased = next(row for row in warehouse["options"] if row["action"] == "phased_move")
    assert math.isclose(phased["ev"], -12.0)

    split = report["split"]
    assert split["recommended"] == "buy"
    assert split["confidence"] == "low"
    assert split["epistemic_spread"]["agree_on_best"] is False
    ranking = {row["action"]: row["models_ranking_first"] for row in split["options"]}
    assert ranking == {"buy": 1, "rent": 1}
