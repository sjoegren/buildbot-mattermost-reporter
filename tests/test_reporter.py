import datetime
import pytest

import dateutil.tz
from buildbot.plugins import reporters

from buildbot_mattermost import reporter


@pytest.fixture
def context_build():
    started_at = datetime.datetime.fromtimestamp(
        1_700_000_000, tz=datetime.timezone.utc
    )
    ctx = {}
    ctx["build"] = {
        "number": 47,
        "builder": {
            "name": "testbuilder",
        },
        "state_string": "string_from_build",
        "results": 0,
        "properties": {
            "owners": (
                [
                    "foo@example.com",
                    "bar@example.com",
                ],
                "prop source",
            ),
        },
        "complete": False,
        "started_at": started_at,
        "url": "http://buildbot.example.com/#/builders/2/builds/47",
    }
    return ctx


@pytest.fixture
def context_build_complete(context_build):
    complete_at = context_build["build"]["started_at"] + datetime.timedelta(minutes=5)
    context_build["build"]["complete"] = True
    context_build["build"]["complete_at"] = complete_at
    return context_build


def test_import_as_buildbot_plugin():
    assert reporters.MattermostStatusPush is reporter.MattermostStatusPush


def test_no_webhook_url_raises():
    with pytest.raises(
        Exception, match=r"missing 1 required positional argument: 'webhook_url'"
    ):
        reporter.MattermostStatusPush()


@pytest.mark.parametrize("value", [None, ""])
def test_empty_webhook_url_raises(value):
    with pytest.raises(Exception, match=r"webhook_url must be set"):
        reporter.MattermostStatusPush(webhook_url=value)


def test_message_formatter_fn_completed_success(context_build_complete):
    ret = reporter.mattermost_message_formatter_fn(
        context_build_complete,
    )
    assert ret == {
        "attachments": [
            {
                "author_link": "http://buildbot.example.com",
                "author_name": "Buildbot",
                "color": "#66bb6a",
                "fallback": "testbuilder #47 "
                "http://buildbot.example.com/#/builders/2/builds/47: "
                "string_from_build",
                "pretext": "Build finished at 2023-11-14 22:18:20+00:00",
                "text": ":white_check_mark: `string_from_build`",
                "title": "Build: testbuilder #47",
                "title_link": "http://buildbot.example.com/#/builders/2/builds/47",
            }
        ],
        "type": "custom_buildbot_status",
        "username": "Buildbot",
    }


def test_message_formatter_fn_failure(context_build_complete):
    context_build_complete["build"]["results"] = 2
    ret = reporter.mattermost_message_formatter_fn(
        context_build_complete,
    )
    assert ret == {
        "attachments": [
            {
                "author_link": "http://buildbot.example.com",
                "author_name": "Buildbot",
                "color": "#e74c3c",
                "fallback": "testbuilder #47 "
                "http://buildbot.example.com/#/builders/2/builds/47: "
                "string_from_build",
                "pretext": "Build finished at 2023-11-14 22:18:20+00:00",
                "text": ":x: `string_from_build`\n@bar, @foo",
                "title": "Build: testbuilder #47",
                "title_link": "http://buildbot.example.com/#/builders/2/builds/47",
            }
        ],
        "type": "custom_buildbot_status",
        "username": "Buildbot",
    }


@pytest.mark.parametrize(
    "owners, expected_string",
    [
        ([], ""),
        (["foo"], "@foo"),
        (["bravo", "charlie", "alpha"], "@alpha, @bravo, @charlie"),
    ],
)
def test_message_formatter_fn_username_fn(
    context_build_complete, owners, expected_string
):
    """Set username_fn to a function that returns whatever username is given,
    i.e. the build owners."""
    context_build_complete["build"]["results"] = 2
    context_build_complete["build"]["properties"] = {
        "owners": (owners, ""),
    }
    ret = reporter.mattermost_message_formatter_fn(
        context_build_complete, username_fn=lambda u: u
    )
    last_line = ret["attachments"][0]["text"].splitlines()[-1]
    if len(owners) == 0:
        assert not last_line.startswith("@")
    else:
        assert last_line == expected_string


def test_message_formatter_fn_username_fn_static_string(context_build_complete):
    """Set username_fn to a function that always returns the same notify
    string."""
    context_build_complete["build"]["results"] = 2
    context_build_complete["build"]["properties"] = {
        "owners": (["foo@example.com", "bar"], ""),
    }
    ret = reporter.mattermost_message_formatter_fn(
        context_build_complete, username_fn=lambda u: "channel"
    )
    last_line = ret["attachments"][0]["text"].splitlines()[-1]
    assert last_line == "@channel"


def test_message_formatter_fn_started(context_build):
    ret = reporter.mattermost_message_formatter_fn(
        context_build,
    )
    assert ret == {
        "attachments": [
            {
                "author_link": "http://buildbot.example.com",
                "author_name": "Buildbot",
                "color": "#66bb6a",
                "fallback": "testbuilder #47 "
                "http://buildbot.example.com/#/builders/2/builds/47: "
                "string_from_build",
                "pretext": "Build started at 2023-11-14 22:13:20+00:00",
                "text": ":arrow_forward: `string_from_build`",
                "title": "Build: testbuilder #47",
                "title_link": "http://buildbot.example.com/#/builders/2/builds/47",
            }
        ],
        "type": "custom_buildbot_status",
        "username": "Buildbot",
    }


@pytest.mark.parametrize(
    "arg, value",
    [
        ("channel", "mattermost-channel-name"),
        ("icon_url", "http://buildbot.net/img/full_logo.svg"),
        ("icon_emoji", ":emoji:"),
    ],
)
def test_message_formatter_fn_completed_optional_webhook_args(
    context_build_complete, arg, value
):
    ret = reporter.mattermost_message_formatter_fn(
        context_build_complete,
        **{arg: value},
    )
    assert ret[arg] == value


@pytest.mark.parametrize(
    "tz, timestamp",
    [
        ("UTC", "2023-11-14 22:13:20+00:00"),
        ("Europe/London", "2023-11-14 22:13:20+00:00"),
        ("Europe/Helsinki", "2023-11-15 00:13:20+02:00"),
        ("America/New_York", "2023-11-14 17:13:20-05:00"),
        ("Pacific/Tongatapu", "2023-11-15 11:13:20+13:00"),
    ],
)
def test_message_formatter_fn_started_with_timezone(context_build, tz, timestamp):
    ret = reporter.mattermost_message_formatter_fn(
        context_build,
        timezone=dateutil.tz.gettz(tz),
    )
    assert ret["attachments"][0]["pretext"] == "Build started at " + timestamp


@pytest.mark.parametrize(
    "tz, timestamp",
    [
        ("UTC", "2023-11-14 22:18:20+00:00"),
        ("Europe/London", "2023-11-14 22:18:20+00:00"),
        ("Europe/Helsinki", "2023-11-15 00:18:20+02:00"),
        ("America/New_York", "2023-11-14 17:18:20-05:00"),
        ("Pacific/Tongatapu", "2023-11-15 11:18:20+13:00"),
    ],
)
def test_message_formatter_fn_completed_with_timezone(
    context_build_complete, tz, timestamp
):
    ret = reporter.mattermost_message_formatter_fn(
        context_build_complete,
        timezone=dateutil.tz.gettz(tz),
    )
    assert ret["attachments"][0]["pretext"] == "Build finished at " + timestamp
