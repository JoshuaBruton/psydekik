from frontend_console.state.chappie_state import (
    ChappieMode,
    ChappieVoiceController,
)


class FakeScheduler:
    def after(self, _delay: int, _callback: object) -> None:
        pass


def make_controller() -> ChappieVoiceController:
    return ChappieVoiceController(
        FakeScheduler(),
        lambda _snapshot: None,
    )


def test_manual_turn_interrupts_sleeping_listener() -> None:
    controller = make_controller()
    controller._ready.set()

    controller.request_turn()

    assert controller._busy.is_set()
    assert controller._manual_request.is_set()
    assert controller._wake_interrupt.is_set()


def test_busy_controller_ignores_another_turn() -> None:
    controller = make_controller()
    controller._ready.set()
    controller._busy.set()

    controller.request_turn()

    assert not controller._manual_request.is_set()
    assert not controller._wake_interrupt.is_set()


def test_turn_before_ready_publishes_starting_state() -> None:
    controller = make_controller()

    controller.request_turn()

    snapshot = controller._events.get_nowait()

    assert snapshot.mode is ChappieMode.STARTING
    assert "warming up" in snapshot.headline


def test_sleeping_snapshot_advertises_wake_phrase() -> None:
    controller = make_controller()

    controller._publish_sleeping(
        "Voice and wake word are online."
    )

    snapshot = controller._events.get_nowait()

    assert snapshot.mode is ChappieMode.SLEEPING
    assert "Hey Chappie" in snapshot.headline
    assert snapshot.detail == "Voice and wake word are online."


def test_stop_interrupts_wake_listener() -> None:
    controller = make_controller()
    controller._ready.set()

    controller.stop()

    assert not controller._ready.is_set()
    assert controller._stop_requested.is_set()
    assert controller._wake_interrupt.is_set()
