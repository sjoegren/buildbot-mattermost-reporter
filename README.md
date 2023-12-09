# Mattermost status reporter for Buildbot

Install:

```
pip install buildbot-mattermost-reporter
```

Usage example in Buildbot `master.cfg`:

```python
from buildbot.plugins import reporters

c['services'].append(
    reporters.MattermostStatusPush(
        webhook_url="https://mattermost.example.com/hooks/hookidstring",
    ),
)
```

Parameters to `MattermostStatusPush`:

```
MattermostStatusPush(
    webhook_url, channel=None, icon_url=None, icon_emoji=None,
    timezone=None, username_fn=None, buildstatusgenerator_kwargs=None,
    generators=None,
    **kwargs)
```

* `webhook_url` (*string*): Mattermost Webhook URL given when webhook is
  created
* `channel` (*string*): See [Mattermost incoming webhooks docs][]
* `icon_url` (*string*): See [Mattermost incoming webhooks docs][]
* `icon_emoji` (*string*): See [Mattermost incoming webhooks docs][]
* `timezone` (*datetime.tzinfo*): Convert timestamps in messages to a timezone,
  if set. Otherwise timestamps are UTC. Concrete `tzinfo` objects could be
  created with [dateutil][], which Buildbot has as dependency.
* `username_fn` (*callable*): Callable that takes a string argument, which is
  one of the individuals in the builds *owners* property, and returns a
  Mattermost username. The username is used for failing builds, where the
  message includes a line like `@owner1, @owner2, ...`. By default a function
  is used that assumes that each owner is an e-mail address and returns the
  part before @, i.e. `user@example.com` returns `user`.
  An example where failing builds would notify the whole channel instead would
  be `username_fn=lambda _: "channel"`.
* `buildstatusgenerator_kwargs` (*dict*): Any extra keyword arguments to
  `reporters.BuildStatusGenerator`, e.g.
  `buildstatusgenerator_kwargs={'report_new': True}`.
* `generators` (*list*): To override generator created by
  `MattermostStatusPush` and format Mattermost messages in a custom manner.
* `**kwargs`: Any extra arguments to `reporters.HttpStatusPush`.

[Mattermost incoming webhooks docs]: https://developers.mattermost.com/integrate/webhooks/incoming/
[dateutil]: https://pypi.org/project/python-dateutil/
