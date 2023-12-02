from buildbot_mattermost import reporter

from buildbot.plugins import reporters


def test_import_as_buildbot_plugin():
    assert reporters.MattermostStatusPush is reporter.MattermostStatusPush
