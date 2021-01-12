from unittest.mock import patch

import pytest
from slack import errors, WebClient

from superset.reports.notifications.slack import SlackNotification
from tests.base_tests import SupersetTestCase
from tests.utils import read_fixture


class SlackTests(SupersetTestCase):
    IMAGE = read_fixture("sample.png")

    @patch("superset.reports.notifications.slack.WebClient.files_upload")
    def test_deliver_message_with_file(self, files_upload_mock):
        SlackNotification.deliver_message(
            "#test_channel", "Your slack subject", "You have a new message", self.IMAGE
        )

        self.assertEqual(
            files_upload_mock.call_args[1],
            {
                "channels": "#test_channel",
                "file": self.IMAGE,
                "initial_comment": "You have a new message",
                "title": "Your slack subject",
            },
        )

    @patch("superset.reports.notifications.slack.WebClient.chat_postMessage")
    def test_deliver_message_without_file(self, chat_post_mock):
        SlackNotification.deliver_message(
            "#test_channel_without",
            "Your slack subject",
            "You have a new message without file",
            None,
        )

        self.assertEqual(
            chat_post_mock.call_args[1],
            {
                "channel": "#test_channel_without",
                "text": "You have a new message without file",
            },
        )


def test_slack_client_compatibility():
    c2 = WebClient()
    # slackclient >2.5.0 raises TypeError: a bytes-like object is required, not 'str
    # and requires to path a filepath instead of the bytes directly
    with pytest.raises(errors.SlackApiError):
        c2.files_upload(channels="#bogdan-test2", file=b"blabla", title="Test upload")
