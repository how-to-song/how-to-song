from pathlib import Path

WORKFLOW = (Path(__file__).resolve().parent.parent / ".github/workflows/blackjack.yml").read_text(encoding="utf-8")


def test_checkout_uses_branch_tip_not_event_sha():
    # 대기했던 실행이 이벤트 당시의 옛 커밋을 받으면 상태가 낡아 push가 충돌한다.
    assert "ref: ${{ github.event.repository.default_branch }}" in WORKFLOW


def test_concurrency_is_job_level_so_skipped_runs_do_not_cancel_game_runs():
    # 워크플로 수준 concurrency면, 게임과 무관한 Issue 실행이 대기 중인 게임 실행을 취소한다.
    head, _, jobs = WORKFLOW.partition("\njobs:")
    assert "concurrency:" not in head
    assert "concurrency:" in jobs
