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
from io import IOBase
from typing import Optional, Union

from retry.api import retry
from slack.errors import SlackApiError

from superset.reports.notifications.slack import SlackNotification


@retry(SlackApiError, delay=10, backoff=2, tries=5)
def deliver_slack_msg(
    slack_channel: str,
    subject: str,
    body: str,
    file: Optional[Union[str, IOBase, bytes]],
) -> None:
    SlackNotification.deliver_message(slack_channel, subject, body, file)
