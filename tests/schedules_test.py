# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
# isort:skip_file
# TODO Test me new reporting slice URL
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from flask_babel import gettext as __
import pytest

from tests.test_app import app
from superset import db
from superset.models.dashboard import Dashboard
from superset.models.schedules import (
    DashboardEmailSchedule,
    EmailDeliveryType,
    SliceEmailReportFormat,
    SliceEmailSchedule,
)
from superset.tasks.schedules import deliver_dashboard, deliver_slice, next_schedules
from superset.models.slice import Slice
from tests.base_tests import SupersetTestCase
from tests.utils import read_fixture
from tests.fixtures.birth_names_dashboard import (
    load_birth_names_dashboard_with_slices_module_scope,
)


class TestSchedules(SupersetTestCase):

    RECIPIENTS = "recipient1@superset.com, recipient2@superset.com"
    BCC = "bcc@superset.com"
    CSV = read_fixture("trends.csv")

    @classmethod
    def setUpClass(cls):
        with app.app_context():
            cls.common_data = dict(
                active=True,
                crontab="* * * * *",
                recipients=cls.RECIPIENTS,
                deliver_as_group=True,
                delivery_type=EmailDeliveryType.inline,
            )

            # Pick up a sample slice and dashboard
            slce = db.session.query(Slice).filter_by(slice_name="Participants").one()
            dashboard = (
                db.session.query(Dashboard)
                .filter_by(dashboard_title="World Bank's Data")
                .one()
            )

            dashboard_schedule = DashboardEmailSchedule(**cls.common_data)
            dashboard_schedule.dashboard_id = dashboard.id
            dashboard_schedule.user_id = 1
            db.session.add(dashboard_schedule)

            slice_schedule = SliceEmailSchedule(**cls.common_data)
            slice_schedule.slice_id = slce.id
            slice_schedule.user_id = 1
            slice_schedule.email_format = SliceEmailReportFormat.data
            slice_schedule.slack_channel = "#test_channel"

            db.session.add(slice_schedule)
            db.session.commit()

            cls.slice_schedule = slice_schedule.id
            cls.dashboard_schedule = dashboard_schedule.id

    @classmethod
    def tearDownClass(cls):
        with app.app_context():
            db.session.query(SliceEmailSchedule).filter_by(
                id=cls.slice_schedule
            ).delete()
            db.session.query(DashboardEmailSchedule).filter_by(
                id=cls.dashboard_schedule
            ).delete()
            db.session.commit()

    def test_crontab_scheduler(self):
        crontab = "* * * * *"

        start_at = datetime.now().replace(microsecond=0, second=0, minute=0)
        stop_at = start_at + timedelta(seconds=3600)

        # Fire off the task every minute
        schedules = list(next_schedules(crontab, start_at, stop_at, resolution=0))

        self.assertEqual(schedules[0], start_at)
        self.assertEqual(schedules[-1], stop_at - timedelta(seconds=60))
        self.assertEqual(len(schedules), 60)

        # Fire off the task every 10 minutes, controlled via resolution
        schedules = list(next_schedules(crontab, start_at, stop_at, resolution=10 * 60))

        self.assertEqual(schedules[0], start_at)
        self.assertEqual(schedules[-1], stop_at - timedelta(seconds=10 * 60))
        self.assertEqual(len(schedules), 6)

        # Fire off the task every 12 minutes, controlled via resolution
        schedules = list(next_schedules(crontab, start_at, stop_at, resolution=12 * 60))

        self.assertEqual(schedules[0], start_at)
        self.assertEqual(schedules[-1], stop_at - timedelta(seconds=12 * 60))
        self.assertEqual(len(schedules), 5)

    def test_wider_schedules(self):
        crontab = "*/15 2,10 * * *"

        for hour in range(0, 24):
            start_at = datetime.now().replace(
                microsecond=0, second=0, minute=0, hour=hour
            )
            stop_at = start_at + timedelta(seconds=3600)
            schedules = list(next_schedules(crontab, start_at, stop_at, resolution=0))

            if hour in (2, 10):
                self.assertEqual(len(schedules), 4)
            else:
                self.assertEqual(len(schedules), 0)

    @pytest.mark.usefixtures("load_birth_names_dashboard_with_slices_module_scope")
    def test_complex_schedule(self):
        # Run the job on every Friday of March and May
        # On these days, run the job at
        # 5:10 pm
        # 5:11 pm
        # 5:12 pm
        # 5:13 pm
        # 5:14 pm
        # 5:15 pm
        # 5:25 pm
        # 5:28 pm
        # 5:31 pm
        # 5:34 pm
        # 5:37 pm
        # 5:40 pm
        crontab = "10-15,25-40/3 17 * 3,5 5"
        start_at = datetime.strptime("2018/01/01", "%Y/%m/%d")
        stop_at = datetime.strptime("2018/12/31", "%Y/%m/%d")

        schedules = list(next_schedules(crontab, start_at, stop_at, resolution=60))
        self.assertEqual(len(schedules), 108)
        fmt = "%Y-%m-%d %H:%M:%S"
        self.assertEqual(schedules[0], datetime.strptime("2018-03-02 17:10:00", fmt))
        self.assertEqual(schedules[-1], datetime.strptime("2018-05-25 17:40:00", fmt))
        self.assertEqual(schedules[59], datetime.strptime("2018-03-30 17:40:00", fmt))
        self.assertEqual(schedules[60], datetime.strptime("2018-05-04 17:10:00", fmt))

    @patch("superset.tasks.schedules.send_email_smtp")
    @patch("superset.utils.screenshots.DashboardScreenshot.compute_and_cache")
    def test_deliver_dashboard_inline(self, screenshot_mock, send_email_smtp):
        screenshot = read_fixture("sample.png")
        screenshot_mock.return_value = screenshot

        schedule = (
            db.session.query(DashboardEmailSchedule)
            .filter_by(id=self.dashboard_schedule)
            .one()
        )

        deliver_dashboard(
            schedule.dashboard_id,
            schedule.recipients,
            schedule.slack_channel,
            schedule.delivery_type,
            schedule.deliver_as_group,
        )

        send_email_smtp.assert_called_once()

        self.assertEqual(send_email_smtp.call_args[0][0], self.RECIPIENTS)

        self.assertIsNone(send_email_smtp.call_args[1]["data"])
        self.assertIsNotNone(send_email_smtp.call_args[1]["images"])

        email_body = send_email_smtp.call_args[0][2]
        assert '<img src="cid' in email_body
        assert "Explore in Superset" in email_body

    @patch("superset.tasks.schedules.send_email_smtp")
    @patch("superset.utils.screenshots.DashboardScreenshot.compute_and_cache")
    def test_deliver_dashboard_as_attachment(self, screenshot_mock, send_email_smtp):
        screenshot = read_fixture("sample.png")
        screenshot_mock.return_value = screenshot

        schedule = (
            db.session.query(DashboardEmailSchedule)
            .filter_by(id=self.dashboard_schedule)
            .one()
        )

        schedule.delivery_type = EmailDeliveryType.attachment

        deliver_dashboard(
            schedule.dashboard_id,
            schedule.recipients,
            schedule.slack_channel,
            schedule.delivery_type,
            schedule.deliver_as_group,
        )

        send_email_smtp.assert_called_once()

        email_body = send_email_smtp.call_args[0][2]
        assert '<img src="cid' not in email_body

        self.assertIsNone(send_email_smtp.call_args[1]["images"])
        self.assertEqual(
            send_email_smtp.call_args[1]["data"]["screenshot.png"], screenshot
        )

    @patch("superset.tasks.schedules.send_email_smtp")
    @patch("superset.utils.screenshots.DashboardScreenshot.compute_and_cache")
    def test_deliver_email_options(self, screenshot_mock, send_email_smtp):
        screenshot = read_fixture("sample.png")
        screenshot_mock.return_value = screenshot

        schedule = (
            db.session.query(DashboardEmailSchedule)
            .filter_by(id=self.dashboard_schedule)
            .one()
        )

        # Send individual mails to the group
        schedule.deliver_as_group = False

        # Set a bcc email address
        app.config["EMAIL_REPORT_BCC_ADDRESS"] = self.BCC

        deliver_dashboard(
            schedule.dashboard_id,
            schedule.recipients,
            schedule.slack_channel,
            schedule.delivery_type,
            schedule.deliver_as_group,
        )

        self.assertEqual(send_email_smtp.call_count, 2)
        self.assertEqual(send_email_smtp.call_args[1]["bcc"], self.BCC)

    @patch("superset.reports.notifications.slack.SlackNotification.deliver_message")
    @patch("superset.tasks.schedules.send_email_smtp")
    @patch("superset.utils.screenshots.DashboardScreenshot.compute_and_cache")
    def test_deliver_dashboard_slack(
        self, screenshot_mock, send_email_smtp, deliver_message_mock
    ):
        screenshot = read_fixture("sample.png")
        screenshot_mock.return_value = screenshot

        schedule = (
            db.session.query(DashboardEmailSchedule)
            .filter_by(id=self.dashboard_schedule)
            .one()
        )
        schedule.recipients = None
        schedule.slack_channel = "#test_channel"

        deliver_dashboard(
            schedule.dashboard_id,
            schedule.recipients,
            schedule.slack_channel,
            schedule.delivery_type,
            schedule.deliver_as_group,
        )

        send_email_smtp.assert_not_called()

        self.assertEqual(
            deliver_message_mock.call_args[0],
            (
                "#test_channel",
                "[Report]  World Bank's Data",
                f"\n        *World Bank's Data*\n\n        <http://0.0.0.0:8080/superset/dashboard/{schedule.dashboard_id}/|Explore in Superset>\n        ",
                screenshot,
            ),
        )

    @patch("superset.reports.notifications.slack.SlackNotification.deliver_message")
    @patch("superset.tasks.schedules.send_email_smtp")
    @patch("superset.utils.screenshots.ChartScreenshot.compute_and_cache")
    def test_deliver_slice_inline_image(
        self, screenshot_mock, send_email_smtp, deliver_message_mock
    ):
        screenshot = read_fixture("sample.png")
        screenshot_mock.return_value = screenshot

        schedule = (
            db.session.query(SliceEmailSchedule).filter_by(id=self.slice_schedule).one()
        )

        schedule.email_format = SliceEmailReportFormat.visualization
        schedule.delivery_type = EmailDeliveryType.inline

        deliver_slice(
            schedule.slice_id,
            schedule.recipients,
            schedule.slack_channel,
            schedule.delivery_type,
            schedule.email_format,
            schedule.deliver_as_group,
            db.session,
        )
        send_email_smtp.assert_called_once()

        print(send_email_smtp.call_args)

        self.assertEqual(
            list(send_email_smtp.call_args[1]["images"].values())[0], screenshot
        )

        self.assertEqual(
            deliver_message_mock.call_args[0],
            (
                "#test_channel",
                "[Report]  Participants",
                f"\n        *Participants*\n\n        <http://0.0.0.0:8080/superset/slice/{schedule.slice_id}/|Explore in Superset>\n        ",
                screenshot,
            ),
        )

    @patch("superset.reports.notifications.slack.SlackNotification.deliver_message")
    @patch("superset.tasks.schedules.send_email_smtp")
    @patch("superset.utils.screenshots.ChartScreenshot.compute_and_cache")
    def test_deliver_slice_attachment(
        self, screenshot_mock, send_email_smtp, deliver_message_mock
    ):
        screenshot = read_fixture("sample.png")
        screenshot_mock.return_value = screenshot

        schedule = (
            db.session.query(SliceEmailSchedule).filter_by(id=self.slice_schedule).one()
        )

        schedule.email_format = SliceEmailReportFormat.visualization
        schedule.delivery_type = EmailDeliveryType.attachment

        deliver_slice(
            schedule.slice_id,
            schedule.recipients,
            schedule.slack_channel,
            schedule.delivery_type,
            schedule.email_format,
            schedule.deliver_as_group,
            db.session,
        )

        send_email_smtp.assert_called_once()

        self.assertEqual(
            send_email_smtp.call_args[1]["data"]["screenshot.png"], screenshot
        )

        self.assertEqual(
            deliver_message_mock.call_args[0],
            (
                "#test_channel",
                "[Report]  Participants",
                f"\n        *Participants*\n\n        <http://0.0.0.0:8080/superset/slice/{schedule.slice_id}/|Explore in Superset>\n        ",
                screenshot,
            ),
        )

    @patch("superset.reports.notifications.slack.SlackNotification.deliver_message")
    @patch("superset.tasks.schedules.urllib.request.urlopen")
    @patch("superset.tasks.schedules.urllib.request.OpenerDirector.open")
    @patch("superset.tasks.schedules.send_email_smtp")
    def test_deliver_slice_csv_attachment(
        self, send_email_smtp, mock_open, mock_urlopen, deliver_message_mock
    ):
        response = Mock()
        mock_open.return_value = response
        mock_urlopen.return_value = response
        mock_urlopen.return_value.getcode.return_value = 200
        response.read.return_value = self.CSV

        schedule = (
            db.session.query(SliceEmailSchedule).filter_by(id=self.slice_schedule).one()
        )

        schedule.email_format = SliceEmailReportFormat.data
        schedule.delivery_type = EmailDeliveryType.attachment

        deliver_slice(
            schedule.slice_id,
            schedule.recipients,
            schedule.slack_channel,
            schedule.delivery_type,
            schedule.email_format,
            schedule.deliver_as_group,
            db.session,
        )

        send_email_smtp.assert_called_once()

        file_name = __("%(name)s.csv", name=schedule.slice.slice_name)

        self.assertEqual(send_email_smtp.call_args[1]["data"][file_name], self.CSV)

        self.assertEqual(
            deliver_message_mock.call_args[0],
            (
                "#test_channel",
                "[Report]  Participants",
                f"\n        *Participants*\n\n        <http://0.0.0.0:8080/superset/slice/{schedule.slice_id}/|Explore in Superset>\n        ",
                self.CSV,
            ),
        )

    @patch("superset.reports.notifications.slack.SlackNotification.deliver_message")
    @patch("superset.tasks.schedules.urllib.request.urlopen")
    @patch("superset.tasks.schedules.urllib.request.OpenerDirector.open")
    @patch("superset.tasks.schedules.send_email_smtp")
    def test_deliver_slice_csv_inline(
        self, send_email_smtp, mock_open, mock_urlopen, deliver_message_mock
    ):
        response = Mock()
        mock_open.return_value = response
        mock_urlopen.return_value = response
        mock_urlopen.return_value.getcode.return_value = 200
        response.read.return_value = self.CSV
        schedule = (
            db.session.query(SliceEmailSchedule).filter_by(id=self.slice_schedule).one()
        )

        schedule.email_format = SliceEmailReportFormat.data
        schedule.delivery_type = EmailDeliveryType.inline

        deliver_slice(
            schedule.slice_id,
            schedule.recipients,
            schedule.slack_channel,
            schedule.delivery_type,
            schedule.email_format,
            schedule.deliver_as_group,
            db.session,
        )

        send_email_smtp.assert_called_once()

        self.assertIsNone(send_email_smtp.call_args[1]["data"])
        self.assertTrue("<table " in send_email_smtp.call_args[0][2])

        self.assertEqual(
            deliver_message_mock.call_args[0],
            (
                "#test_channel",
                "[Report]  Participants",
                f"\n        *Participants*\n\n        <http://0.0.0.0:8080/superset/slice/{schedule.slice_id}/|Explore in Superset>\n        ",
                self.CSV,
            ),
        )
