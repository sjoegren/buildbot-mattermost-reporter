import functools
from urllib.parse import urlparse

from twisted.internet import defer

from buildbot import config
from buildbot.plugins import reporters
from buildbot.process import results
import buildbot.reporters.http

COLOR_MAP_RESULT = {
    results.SUCCESS: "#66bb6a",  # green
    results.WARNINGS: "#ffcc80",  # yellow
    results.FAILURE: "#e74c3c",  # red
}
ICON_MAP_RESULT = {
    results.SUCCESS: ":white_check_mark:",
    results.WARNINGS: ":warning:",
    results.FAILURE: ":x:",
}
ICON_BUILD_STARTED = ":arrow_forward:"


class MattermostStatusPush(buildbot.reporters.http.HttpStatusPush):
    """
    Buildbot reporter to report build statuses to a Mattermost webhook.
    """

    name = "MattermostStatusPush"
    secrets = ["auth", "webhook_url", "serverUrl"]

    def checkConfig(
        self,
        webhook_url,
        channel=None,
        icon_url=None,
        icon_emoji=None,
        timezone=None,
        username_fn=None,
        buildstatusgenerator_kwargs=None,
        generators=None,
        **kwargs,
    ):
        if not webhook_url:
            config.error("webhook_url must be set to the Mattermost webhook URL")
        self._channel = channel
        self._icon_url = icon_url
        self._icon_emoji = icon_emoji
        self._timezone = timezone
        self._username_fn = username_fn
        if generators is None:
            generators = self._create_buildstatusgenerators(buildstatusgenerator_kwargs)

        super().checkConfig(serverUrl=webhook_url, generators=generators, **kwargs)

    @defer.inlineCallbacks
    def reconfigService(
        self,
        webhook_url,
        channel=None,
        icon_url=None,
        icon_emoji=None,
        timezone=None,
        username_fn=None,
        buildstatusgenerator_kwargs=None,
        generators=None,
        **kwargs,
    ):
        if generators is None:
            generators = self._create_buildstatusgenerators(buildstatusgenerator_kwargs)
        yield super().reconfigService(
            serverUrl=webhook_url, generators=generators, **kwargs
        )

    def _create_buildstatusgenerators(self, buildstatusgenerator_kwargs):
        """
        Create a BuildStatusGenerator with a custom message_formatter that
        formats json payload of HttpStatusPush according to Mattermost Webhook
        API.
        """
        # MessageFormatterFunction takes a callable that expects one argument;
        #   > A callable that will be called with a dictionary that contains
        #   build key with the value that contains the build dictionary as
        #   received from the data API.
        # Prepare a callable of mattermost_message_formatter_fn with the extra
        # Mattermost options passed to MattermostStatusPush.
        formatter_fn = functools.partial(
            mattermost_message_formatter_fn,
            channel=self._channel,
            icon_url=self._icon_url,
            icon_emoji=self._icon_emoji,
            timezone=self._timezone,
            username_fn=self._username_fn,
        )
        formatter = reporters.MessageFormatterFunction(
            formatter_fn,
            "json",
            want_properties=True,
            want_steps=False,
            want_logs=False,
        )
        kwargs = buildstatusgenerator_kwargs or {}
        kwargs.setdefault("report_new", False)
        return [reporters.BuildStatusGenerator(message_formatter=formatter, **kwargs)]


def mattermost_message_formatter_fn(
    context,
    /,
    username="Buildbot",
    channel=None,
    icon_url=None,
    icon_emoji=None,
    timezone=None,
    username_fn=None,
):
    build = context["build"]

    def getprop(name, default=""):
        try:
            prop = context["build"]["properties"][name]
        except KeyError:
            return default
        value, source = prop
        return value or default

    def mm_user_from_email(email):
        """Return ${USER} of ${USER}@domain email addresses."""
        try:
            at = email.index("@")
        except ValueError:
            return email
        return email[:at]

    # Make a list of Mattermost usernames from the builds list of owners.
    if username_fn is None:
        username_fn = mm_user_from_email
    build_owner_usernames = set(username_fn(o) for o in getprop("owners", []) if o)

    webhook_request = {
        "username": username,
        "type": "custom_buildbot_status",
    }
    if channel is not None:
        webhook_request["channel"] = channel
    if icon_url is not None:
        webhook_request["icon_url"] = icon_url
    if icon_emoji is not None:
        webhook_request["icon_emoji"] = icon_emoji

    buildbot_url = "{0.scheme}://{0.netloc}".format(urlparse(build.get("url", "")))

    if build.get("complete"):
        message = _build_completed(build, build_owner_usernames, timezone)
    else:
        message = _build_started(build, timezone)

    # Set common items in the Mattermost attachment.
    message.update(
        {
            "author_name": "Buildbot",
            "author_link": buildbot_url,
            "title": "Build: {builder[name]} #{number}".format(**build),
            "title_link": build.get("url"),
            "fallback": "{builder[name]} #{number} {url}: {state_string}".format(
                **build
            ),
        }
    )
    webhook_request["attachments"] = [message]
    return webhook_request


def _build_started(build, timezone):
    rv = {}
    rv["pretext"] = "Build started at {}".format(
        _format_dt(build["started_at"], timezone)
    )
    rv["text"] = "{} `{}`".format(ICON_BUILD_STARTED, build["state_string"])
    try:
        rv["color"] = COLOR_MAP_RESULT[build["results"]]
    except KeyError:
        pass
    return rv


def _build_completed(build, owners, timezone):
    rv = {}
    rv["pretext"] = "Build finished at {}".format(
        _format_dt(build["complete_at"], timezone)
    )

    rv["text"] = "{status_icon} `{state_string}`".format(
        status_icon=ICON_MAP_RESULT.get(
            build["results"], ICON_MAP_RESULT[results.FAILURE]
        ),
        state_string=build["state_string"],
    )

    # If the build failed, include as list of build owners to ping
    if build["results"] == results.FAILURE and owners:
        owners = ", ".join(f"@{u}" for u in sorted(owners))
        rv["text"] += f"\n{owners}"

    try:
        rv["color"] = COLOR_MAP_RESULT[build["results"]]
    except KeyError:
        pass
    return rv


def _format_dt(dt, timezone=None):
    if not dt:
        return dt
    if timezone is not None:
        dt = dt.astimezone(timezone)
    return dt.isoformat(sep=" ", timespec="seconds")
