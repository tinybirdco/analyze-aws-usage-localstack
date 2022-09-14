import json
import logging
import uuid
from datetime import datetime

import requests
from localstack.extensions.api import Extension, http, aws

from localstack_tinybird_logger.config import TINYBIRD_API_TOKEN

LOG = logging.getLogger(__name__)


class TinybirdLoggerExtension(Extension):
    name = "localstack-tinybird-logger"

    session_id: str

    def on_extension_load(self):
        # create a unique session id when the extension is loaded (which only happens once at startup)
        self.session_id = str(uuid.uuid4())

    def update_response_handlers(self, handlers: aws.CompositeResponseHandler):
        # add the
        handlers.append(self._log_aws_api_call)

    def _log_aws_api_call(self, chain, context: aws.RequestContext, response: http.Response):
        # only invoke the handler if the operation is set, indicating a correct AWS request
        if not context.operation:
            return
        # ignore API calls that are made from within localstack
        if is_internal(context):
            return

        payload = {
            "timestamp": datetime.utcnow().isoformat(timespec="seconds"),
            "session_id": self.session_id,
            "service": context.service.service_name,
            "operation": context.operation.name,
            "region": context.region,
            "status_code": response.status_code,
            "user_agent": context.request.headers.get("user-agent"),
            "request": None,
            "response": None,
            "err_type": context.service_exception.code if context.service_exception else None,
            "err_msg": context.service_exception.message if context.service_exception else None,
        }

        # sometimes the service request and response documents may contain objects that are not json serializable
        try:
            payload["request"] = json.dumps(context.service_request)
        except Exception:
            pass
        try:
            payload["response"] = json.dumps(context.service_response)
        except Exception:
            pass

        response = requests.post(
            url="https://api.tinybird.co/v0/events",
            data=json.dumps(payload),
            params={
                "name": "aws_api_calls",
                "token": TINYBIRD_API_TOKEN,
            }
        )
        print("loaded into tinybird: %s" % response.json())


def is_internal(context: aws.RequestContext) -> bool:
    """
    Method to determine whether the given request was made from inside localstack.
    """
    from localstack.utils.aws.aws_stack import is_internal_call_context
    return is_internal_call_context(context.request.headers)
