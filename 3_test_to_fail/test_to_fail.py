import sys
import os
import pytest
import allure
from datetime import datetime, timedelta

# Add the parent directory to the path so 'SOLUTIONS' can be found
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# DO NOT LOOK INTO THE RECORD_TELEGRAMS FUNCTION AS IT WILL SPOIL THE MYSTERY!
from SOLUTIONS.water_meter import record_telegrams


@allure.title("Verify Mobile telegram timing tolerance")
@allure.description("Checks that Mobile telegrams arrive every 60s ± 10%")
@pytest.mark.parametrize("duration_minutes", [60])
def test_mobile_telegrams_distance(duration_minutes):
    telegrams = record_telegrams(duration_minutes)
    mobile_times = []

    for telegram in telegrams:
        if "Mobile telegram" in telegram:
            timestamp_str = telegram.split(" at ")[1].split(" Volume:")[0]
            mobile_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            mobile_times.append(mobile_time)

    time_diffs = []
    for i in range(1, len(mobile_times)):
        diff = mobile_times[i] - mobile_times[i - 1]
        time_diffs.append(diff.total_seconds())

    # Attach timing differences
    allure.attach(
        "\n".join(str(d) for d in time_diffs),
        name="Time Differences Between Mobile Telegrams",
        attachment_type=allure.attachment_type.TEXT,
    )

    # Check
    for diff in time_diffs:
        assert 54 <= diff <= 66, f"Telegram time diff {diff}s out of bounds"


@allure.feature("Static Telegrams")
@allure.title("Static telegrams sent hourly and always with STATUS: OK")
def test_static_telegrams_status():
    telegrams = record_telegrams(duration_minutes=100000)

    static_telegrams = [tg for tg in telegrams if tg.startswith("Static")]

    # Attach all static telegrams for inspection
    allure.attach(
        "\n".join(static_telegrams),
        name="All Static Telegrams",
        attachment_type=allure.attachment_type.TEXT,
    )

    # Identify bad telegrams (not STATUS: OK)
    bad_telegrams = [tg for tg in static_telegrams if "STATUS: OK" not in tg]

    if bad_telegrams:
        allure.attach(
            "\n".join(bad_telegrams),
            name="Static Telegrams with Incorrect Status",
            attachment_type=allure.attachment_type.TEXT,
        )

    with allure.step("Check that all static telegrams contain STATUS: OK"):
        assert (
            not bad_telegrams
        ), f"{len(bad_telegrams)} static telegram(s) had incorrect status."

    with allure.step("Check static telegrams are sent every hour ±60 seconds"):
        timestamps = [
            datetime.strptime(
                tg.split(" at ")[1].split(" STATUS")[0], "%Y-%m-%d %H:%M:%S"
            )
            for tg in static_telegrams
        ]

        deltas = [
            (timestamps[i] - timestamps[i - 1]).total_seconds()
            for i in range(1, len(timestamps))
        ]

        allure.attach(
            "\n".join(f"{d:.1f} seconds" for d in deltas),
            name="Static Telegram Intervals",
            attachment_type=allure.attachment_type.TEXT,
        )

        for delta in deltas:
            assert (
                3540 <= delta <= 3660
            ), f"Static telegram timing incorrect: interval = {delta:.1f} seconds"


@allure.feature("Volume Measurement")
@allure.title("First mobile telegram volume is zero")
def test_mobile_telegram_volume_starts_zero():
    telegrams = record_telegrams(duration_minutes=60)
    first_volume = float(telegrams[0].split()[-1])
    assert first_volume == 1e-6, f"First volume should be zero, got {first_volume}"


@allure.feature("Volume Consistency")
@allure.title("Mobile telegram volume increases by exactly 10 dm³ per minute")
def test_mobile_telegram_volume_increments():
    telegrams = record_telegrams(duration_minutes=100)

    volumes = [
        float(telegram.split()[-1])
        for telegram in telegrams
        if telegram.startswith("Mobile")
    ]

    errors = []

    for i in range(1, len(volumes)):
        delta = volumes[i] - volumes[i - 1]
        if delta < 0:
            errors.append(f"Volume decreased at #{i}: {volumes[i - 1]} -> {volumes[i]}")
        elif abs(delta - 10) > 0.01:
            errors.append(f"Unexpected increment at #{i}: got {delta}")

    assert not errors, "Volume errors:\n" + "\n".join(errors)
