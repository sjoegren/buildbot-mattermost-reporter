# Mattermost status reporter for Buildbot

Install:

```
pip install buildbot-mattermost-reporter
```

Use:

```python
c['services'].append(
    MattermostStatusPush(
        webhook_url="https://mattermost.example.com/hooks/hookidstring",
        channel="ci-status",
    ),
)
```

TODO: document optional arguments
